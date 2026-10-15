import numpy as np
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    recall_score,
)
from sklearn.model_selection import (
    GridSearchCV,
    StratifiedKFold,
    cross_val_predict,
)
from sklearn.pipeline import Pipeline

from app.database.connection import SessionLocal
from app.ml.prepare_dataset import build_dataset  # Update this import


RANDOM_STATE = 42
OUTER_FOLDS = 4
INNER_FOLDS = 3

THRESHOLDS = np.arange(0.20, 0.81, 0.05)


def create_pipeline():
    """Preprocessing and model are fitted together inside each fold."""
    return Pipeline([
        (
            "imputer",
            SimpleImputer(
                strategy="median",
                add_indicator=True,
            ),
        ),
        (
            "classifier",
            RandomForestClassifier(
                random_state=RANDOM_STATE,
                n_estimators=100,
                n_jobs=1,
            ),
        ),
    ])


PARAM_GRID = {
    "classifier__max_depth": [None, 8],
    "classifier__min_samples_leaf": [1, 3, 5],
    "classifier__max_features": ["sqrt", 0.7],
    "classifier__class_weight": [
        "balanced",
        "balanced_subsample",
    ],
}


def prepare_modality_dataset(dataset, modality):
    """Select only one sensor modality and the operating setpoint."""

    if modality not in {"electric", "vibration"}:
        raise ValueError(f"Unsupported modality: {modality}")

    prefix = f"{modality}_ch"

    sensor_features = [
        col for col in dataset.columns
        if col.startswith(prefix)
    ]

    if not sensor_features:
        raise ValueError(f"No {modality} features found.")

    # Keep runs that have at least one usable feature
    # from the requested sensor modality.
    available = dataset[sensor_features].notna().any(axis=1)
    subset = dataset.loc[available].copy()

    # Remove features that are completely missing in this modality.
    sensor_features = [
        col for col in sensor_features
        if subset[col].notna().any()
    ]

    feature_columns = sensor_features.copy()

    # The setpoint is a known operating condition.
    if "speed_sp" in subset.columns:
        feature_columns.append("speed_sp")

    X = subset[feature_columns].copy()
    y = subset["target"].astype(int).copy()

    # Explicitly verify that modalities are not mixed.
    wrong_prefix = (
        "vibration_ch" if modality == "electric"
        else "electric_ch"
    )

    assert not any(
        col.startswith(wrong_prefix) for col in X.columns
    ), f"{modality} dataset contains features from the other modality."

    print(f"\n{modality.upper()} feature audit")
    print(f"Electrical features: {sum(c.startswith('electric_ch') for c in X.columns)}")
    print(f"Vibration features: {sum(c.startswith('vibration_ch') for c in X.columns)}")
    print(f"Operating features: {int('speed_sp' in X.columns)}")

    return X, y


def select_threshold(y_true, probabilities):
    """Choose threshold using training-only out-of-fold predictions."""

    best_threshold = 0.5
    best_score = (-1.0, -1.0, float("-inf"))

    for threshold in THRESHOLDS:
        predictions = (probabilities >= threshold).astype(int)

        balanced = balanced_accuracy_score(
            y_true, predictions
        )
        macro_f1 = f1_score(
            y_true,
            predictions,
            average="macro",
            zero_division=0,
        )

        # Prefer balanced accuracy, then macro F1,
        # then a threshold closer to 0.5.
        score = (
            balanced,
            macro_f1,
            -abs(threshold - 0.5),
        )

        if score > best_score:
            best_score = score
            best_threshold = float(threshold)

    return best_threshold


def report_results(y_true, predictions, title):
    print(f"\n{title}")
    print("-" * len(title))

    print(
        "Balanced accuracy:",
        round(balanced_accuracy_score(y_true, predictions), 3),
    )
    print(
        "Macro F1:",
        round(
            f1_score(
                y_true,
                predictions,
                average="macro",
                zero_division=0,
            ),
            3,
        ),
    )

    recalls = recall_score(
        y_true,
        predictions,
        labels=[0, 1],
        average=None,
        zero_division=0,
    )
    print(f"Healthy recall: {recalls[0]:.3f}")
    print(f"Faulty recall:  {recalls[1]:.3f}")

    print("\nConfusion matrix (rows=actual, columns=predicted):")
    print(confusion_matrix(y_true, predictions, labels=[0, 1]))

    print("\nClassification report:")
    print(
        classification_report(
            y_true,
            predictions,
            labels=[0, 1],
            target_names=["Healthy", "Faulty"],
            zero_division=0,
        )
    )


def tune_and_evaluate(dataset, modality):
    X, y = prepare_modality_dataset(dataset, modality)

    print(f"\n{'=' * 60}")
    print(f"{modality.upper()} RANDOM FOREST TUNING")
    print("=" * 60)
    print(f"Runs: {len(X)}")
    print(f"Features: {len(X.columns)}")
    print("Class counts:")
    print(y.value_counts().sort_index().rename(
        index={0: "Healthy", 1: "Faulty"}
    ))

    counts = y.value_counts()

    if len(counts) != 2 or counts.min() < OUTER_FOLDS:
        print("Insufficient examples for the requested outer CV.")
        return None

    outer_cv = StratifiedKFold(
        n_splits=OUTER_FOLDS,
        shuffle=True,
        random_state=RANDOM_STATE,
    )

    # Every run gets predictions from a model that did not train on it.
    actual_all = []
    default_predictions = []
    tuned_predictions = []
    selected_thresholds = []
    selected_parameters = []

    for fold, (train_idx, test_idx) in enumerate(
        outer_cv.split(X, y), start=1
    ):
        X_train = X.iloc[train_idx]
        X_test = X.iloc[test_idx]
        y_train = y.iloc[train_idx]
        y_test = y.iloc[test_idx]

        inner_cv = StratifiedKFold(
            n_splits=INNER_FOLDS,
            shuffle=True,
            random_state=RANDOM_STATE + fold,
        )

        search = GridSearchCV(
            estimator=create_pipeline(),
            param_grid=PARAM_GRID,
            scoring="balanced_accuracy",
            cv=inner_cv,
            n_jobs=-1,
            refit=True,
            error_score="raise",
        )

        # Hyperparameters are selected using the training fold only.
        search.fit(X_train, y_train)

        # Select the threshold using training-fold OOF probabilities.
        train_probabilities = cross_val_predict(
            clone(search.best_estimator_),
            X_train,
            y_train,
            cv=inner_cv,
            method="predict_proba",
            n_jobs=-1,
        )[:, 1]

        threshold = select_threshold(
            y_train.to_numpy(),
            train_probabilities,
        )

        # Evaluate on the untouched outer test fold.
        test_probabilities = search.best_estimator_.predict_proba(
            X_test
        )[:, 1]

        default_pred = (test_probabilities >= 0.5).astype(int)
        tuned_pred = (test_probabilities >= threshold).astype(int)

        actual_all.extend(y_test.tolist())
        default_predictions.extend(default_pred.tolist())
        tuned_predictions.extend(tuned_pred.tolist())
        selected_thresholds.append(threshold)
        selected_parameters.append(search.best_params_)

        print(
            f"\nFold {fold}: "
            f"inner balanced accuracy={search.best_score_:.3f}, "
            f"selected threshold={threshold:.2f}"
        )
        print("Best parameters:", search.best_params_)

    report_results(
        actual_all,
        default_predictions,
        f"{modality.upper()} — outer CV, threshold 0.50",
    )

    report_results(
        actual_all,
        tuned_predictions,
        f"{modality.upper()} — outer CV, tuned threshold",
    )

    print("\nThresholds selected within training folds:")
    print([round(value, 2) for value in selected_thresholds])

    # Fit a deployable experimental model using all available runs.
    # Its performance must be represented by the outer-CV results above.
    final_cv = StratifiedKFold(
        n_splits=INNER_FOLDS,
        shuffle=True,
        random_state=RANDOM_STATE,
    )

    final_search = GridSearchCV(
        estimator=create_pipeline(),
        param_grid=PARAM_GRID,
        scoring="balanced_accuracy",
        cv=final_cv,
        n_jobs=-1,
        refit=True,
        error_score="raise",
    )
    final_search.fit(X, y)

    final_oof_probabilities = cross_val_predict(
        clone(final_search.best_estimator_),
        X,
        y,
        cv=final_cv,
        method="predict_proba",
        n_jobs=-1,
    )[:, 1]

    final_threshold = select_threshold(
        y.to_numpy(),
        final_oof_probabilities,
    )

    print("\nFinal model configuration")
    print("Best parameters:", final_search.best_params_)
    print(f"Training-derived threshold: {final_threshold:.2f}")

    return {
        "model": final_search.best_estimator_,
        "threshold": final_threshold,
        "outer_balanced_accuracy": balanced_accuracy_score(
            actual_all, tuned_predictions
        ),
        "outer_macro_f1": f1_score(
            actual_all,
            tuned_predictions,
            average="macro",
            zero_division=0,
        ),
        "selected_thresholds": selected_thresholds,
    }


def main():
    with SessionLocal() as session:
        dataset = build_dataset(session)

    if dataset.empty:
        raise ValueError("No usable runs found.")

    print("\nLabel audit:")
    print(dataset.groupby(["condition", "target"]).size())

    if dataset["target"].nunique() != 2:
        raise ValueError("Both target classes (0 and 1) are required.")

    electric_results = tune_and_evaluate(dataset, "electric")
    vibration_results = tune_and_evaluate(dataset, "vibration")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for modality, result in [
        ("Electrical", electric_results),
        ("Vibration", vibration_results),
    ]:
        if result is None:
            continue

        print(
            f"{modality}: "
            f"balanced accuracy={result['outer_balanced_accuracy']:.3f}, "
            f"macro F1={result['outer_macro_f1']:.3f}, "
            f"final threshold={result['threshold']:.2f}"
        )


if __name__ == "__main__":
    main()
