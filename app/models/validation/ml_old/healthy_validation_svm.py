import pandas as pd
from sqlalchemy import select

from app.database.connection import SessionLocal
from app.models.database.orm_models import (ProcessMeasurement,HealthyElectricFeatures,HealthyVibrationFeatures)

from sklearn.preprocessing import StandardScaler
from sklearn.svm import OneClassSVM

HEALTHY_RUNS_BY_SETPOINT = {
    50: (
        "M2_50_healthy_1_0",
        "M2_50_healthy_2_0",
        "M2_50_healthy_3_0",
        "M2_50_new_motor_0",
    ),
    75: (
        "M2_75_healthy_1_0",
        "M2_75_healthy_2_0",
        "M2_75_healthy_3_0",
        "M2_75_new_motor_0",
    ),
    100: (
        "M2_100_healthy_1_0",
        "M2_100_healthy_2_0",
        "M2_100_healthy_3_0",
        "M2_100_new_motor_0",),}

def fetch_healthy_features() -> pd.DataFrame:
    """Fetch run-level healthy features from the database."""

    records = []

    with SessionLocal() as session:
        for speed, run_ids in HEALTHY_RUNS_BY_SETPOINT.items():
            for run_id in run_ids:

                process = session.scalars(
                    select(ProcessMeasurement).where(
                        ProcessMeasurement.run_id == run_id)).one_or_none()

                if process is None:
                    raise ValueError(f"Run not found: {run_id}")

                record = {
                    "run_id": run_id,
                    "speed_sp": speed}

                sensor_tables = [
                    ("electric", HealthyElectricFeatures),
                    ("vibration", HealthyVibrationFeatures),]

                for sensor_name, model in sensor_tables:
                    rows = session.scalars(
                        select(model).where(
                            model.process_measurement_id == process.id)).all()

                    for row in rows:
                        column = (f"{sensor_name}_ch{row.channel}_{row.feature}")

                        record[column] = float(row.mean)

                records.append(record)

    df = pd.DataFrame(records)

    if df.empty:
        raise ValueError("No healthy feature data found.")
    return df


def prepare_features(df: pd.DataFrame, speed_sp: int):
    """Select one speed and standardise its feature columns."""

    speed_df = df[df["speed_sp"] == speed_sp].copy()

    feature_columns = [col for col in speed_df.columns if col not in ("run_id", "speed_sp")]

    X = speed_df[feature_columns]

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    return speed_df["run_id"].tolist(), X_scaled, feature_columns


def validate_one_class_svm(df: pd.DataFrame,speed_sp: int,nu: float = 0.1,gamma: str = "scale",) -> pd.DataFrame:
    """Evaluate healthy runs using leave-one-run-out validation."""

    speed_df = df[df["speed_sp"] == speed_sp].copy()

    feature_columns = [
        col for col in speed_df.columns
        if col not in ("run_id", "speed_sp")]

    results = []

    for index in speed_df.index:
        training_df = speed_df.drop(index)
        test_df = speed_df.loc[[index]]

        scaler = StandardScaler()

        X_train = scaler.fit_transform(training_df[feature_columns])
        X_test = scaler.transform(test_df[feature_columns])

        model = OneClassSVM(
            kernel="rbf",
            nu=0.01,
            gamma="scale",)

        model.fit(X_train)

        print("Training predictions:", model.predict(X_train))
        print("Training scores:", model.decision_function(X_train))

        prediction = model.predict(X_test)[0]
        score = model.decision_function(X_test)[0]

        results.append({
            "run_id": test_df.iloc[0]["run_id"],
            "speed_sp": speed_sp,
            "prediction": int(prediction),
            "decision_score": float(score)})

    return pd.DataFrame(results)


if __name__ == "__main__":
    df = fetch_healthy_features()

    print(df.shape)
    print(df.head())
    print(df.isnull().sum().sum())

    run_ids, X_scaled, features = prepare_features(df, 50)

    print("Runs:", run_ids)
    print("Matrix shape:", X_scaled.shape)
    print("Feature count:", len(features))

    results = validate_one_class_svm(df, speed_sp=50)
    print("Result type:", type(results))
    print("Result:")
    print(results)