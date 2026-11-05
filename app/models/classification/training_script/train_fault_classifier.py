"""Train and evaluate sensor-specific pump fault classifiers.

This prototype consumes the supplied, already-extracted feature CSVs. It first
averages windows within each experimental run and sensor channel, then evaluates
one sample per run with leave-one-run-out cross-validation. Run and condition
metadata are used only for grouping and labels, never as model features.

Examples:
    python train_fault_classifier.py --data-dir . --output-dir models
    python train_fault_classifier.py --sensor electric --data-dir .
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.model_selection import LeaveOneGroupOut, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

DATASETS = {
    "electric": "electric_measurements_202611051141.csv",
    "vibration": "vibration_measurements_202611051142.csv",
}
FEATURES = ("mean", "rms", "std", "peak")
MODEL_VERSION = "0.1.0-prototype"


class DatasetError(ValueError):
    """Raised when supplied data cannot be used safely for training."""


def load_run_features(
    data_dir: Path,
    sensor: str,
    process: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.Series, pd.Series, dict[str, Any]]:
    """Return one feature row per run, with channel-specific aggregated inputs."""
    if sensor not in DATASETS:
        raise DatasetError(f"Unsupported sensor {sensor!r}; choose {', '.join(DATASETS)}")
    process_path = data_dir / "process_measurements_202611051142.csv"
    sensor_path = data_dir / DATASETS[sensor]
    if process is None:
        process = pd.read_csv(process_path)
    measurements = pd.read_csv(sensor_path)
    required_process = {"id", "run_id", "condition_desc"}
    required_measurements = {"process_measurement_id", "channel", *FEATURES}
    if absent := required_process - set(process.columns):
        raise DatasetError(f"Process dataset missing columns: {sorted(absent)}")
    if absent := required_measurements - set(measurements.columns):
        raise DatasetError(f"{sensor} dataset missing columns: {sorted(absent)}")
    if process["id"].duplicated().any() or process["run_id"].duplicated().any():
        raise DatasetError("Process IDs and run IDs must be unique")
    if measurements[list(FEATURES)].isna().any().any():
        raise DatasetError(f"{sensor} features contain missing values")

    metadata = process[["id", "run_id", "condition_desc"]].copy()
    metadata["id"] = pd.to_numeric(metadata["id"], errors="raise")
    measurements["process_measurement_id"] = pd.to_numeric(
        measurements["process_measurement_id"], errors="raise")
    orphan_ids = set(measurements["process_measurement_id"]) - set(metadata["id"])
    if orphan_ids:
        raise DatasetError(f"{sensor} rows reference unknown process IDs: {sorted(orphan_ids)}")

    # Each run/channel contributes exactly one vector, regardless of window count.
    means = measurements.groupby(["process_measurement_id", "channel"], sort=True)[
        list(FEATURES)
    ].mean()
    wide = means.unstack("channel")
    wide.columns = [f"{feature}_channel_{channel}" for feature, channel in wide.columns]
    wide.index.name = "id"
    joined = metadata.set_index("id").join(wide, how="inner")
    feature_columns = list(wide.columns)
    if joined[feature_columns].isna().any().any():
        raise DatasetError("Aggregated feature table contains missing values")
    if joined["run_id"].duplicated().any():
        raise DatasetError("Expected one aggregated sample per experimental run")

    labels = joined["condition_desc"].replace(
        {"Healthy 1": "Healthy", "Healthy 2": "Healthy", "Healthy 3": "Healthy"}
    )
    X = joined[feature_columns].astype(float)
    groups = joined["run_id"].astype(str)
    summary = {
        "sensor": sensor,
        "source_file": sensor_path.name,
        "source_measurement_rows": int(len(measurements)),
        "aggregated_run_samples": int(len(joined)),
        "feature_count": int(len(feature_columns)),
        "feature_columns": feature_columns,
        "class_run_counts": labels.value_counts().sort_index().to_dict(),
        "missing_sensor_runs": sorted(set(metadata["run_id"]) - set(groups)),
        "aggregation": "mean per process measurement and sensor channel",
    }
    return X, labels.reset_index(drop=True), groups.reset_index(drop=True), summary


def candidate_models() -> dict[str, Any]:
    """Small, interpretable model set; scaling is confined to linear regression."""
    return {
        "decision_tree": DecisionTreeClassifier(
            class_weight="balanced", min_samples_leaf=2, random_state=42
        ),
        "logistic_regression": make_pipeline(
            StandardScaler(),
            LogisticRegression(
                class_weight="balanced", max_iter=3000, random_state=42
            ),
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=150,
            class_weight="balanced",
            min_samples_leaf=2,
            random_state=42,
            # The datasets are small; serial trees avoid worker startup overhead
            # repeated across the leave-one-run-out folds.
            n_jobs=1,
        ),
    }


def evaluate_model(model: Any, X: pd.DataFrame, y: pd.Series, groups: pd.Series) -> dict[str, Any]:
    """Generate one out-of-fold prediction for each run, holding each run out."""
    splitter = LeaveOneGroupOut()
    predictions = cross_val_predict(
        clone(model), X, y, groups=groups, cv=splitter, method="predict", n_jobs=1
    )
    class_names = sorted(y.unique())
    report = classification_report(
        y,
        predictions,
        labels=class_names,
        output_dict=True,
        zero_division=0,
    )
    return {
        "macro_f1": float(f1_score(y, predictions, average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(y, predictions, average="weighted", zero_division=0)),
        "class_labels": class_names,
        "confusion_matrix": confusion_matrix(y, predictions, labels=class_names).tolist(),
        "classification_report": report,
        "predictions": predictions,
    }


def train_sensor(data_dir: Path, sensor: str, output_dir: Path | None) -> dict[str, Any]:
    X, y, groups, data_summary = load_run_features(data_dir, sensor)
    if y.nunique() < 2:
        raise DatasetError(f"{sensor} has fewer than two classes")
    if y.groupby(groups).nunique().gt(1).any():
        raise DatasetError("A run contains inconsistent target labels")

    evaluations = {
        name: evaluate_model(model, X, y, groups)
        for name, model in candidate_models().items()
    }
    # Select by run-held-out macro-F1, then fit once on the complete training data.
    selected_name = max(evaluations, key=lambda name: evaluations[name]["macro_f1"])
    selected_model = clone(candidate_models()[selected_name]).fit(X, y)
    result: dict[str, Any] = {
        "model_version": MODEL_VERSION,
        "data": data_summary,
        "validation": "LeaveOneGroupOut by run_id; one out-of-fold prediction per run",
        "selection_metric": "macro_f1",
        "selected_model": selected_name,
        "evaluations": {},
    }
    for name, evaluation in evaluations.items():
        result["evaluations"][name] = {
            key: value for key, value in evaluation.items() if key != "predictions"
        }
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        model_path = output_dir / f"{sensor}_fault_classifier.joblib"
        joblib.dump(
            {
                "pipeline": selected_model,
                "feature_columns": list(X.columns),
                "classes": list(selected_model.classes_),
                "model_version": MODEL_VERSION,
                "sensor": sensor,
                "target": "condition_desc with healthy variants combined",
                "group_column": "run_id",
            },
            model_path,
        )
        result["model_path"] = str(model_path)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, default=Path("models"))
    parser.add_argument("--sensor", choices=[*DATASETS, "both"], default="both")
    args = parser.parse_args()
    sensors = list(DATASETS) if args.sensor == "both" else [args.sensor]
    outputs = {}
    for sensor in sensors:
        outputs[sensor] = train_sensor(args.data_dir, sensor, args.output_dir)
    report_path = args.output_dir / "evaluation_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(outputs, indent=2), encoding="utf-8")
    print(json.dumps(outputs, indent=2))
    print(f"\nSaved evaluation report: {report_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DatasetError as exc:
        raise SystemExit(f"Dataset error: {exc}") from exc
