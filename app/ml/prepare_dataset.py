import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.database.orm_models import (
    ProcessMeasurement,
    ElectricMeasurement,
    VibrationMeasurement,
)
from app.database.connection import SessionLocal

def build_dataset(session: Session) -> pd.DataFrame:
    """Build one feature row per process measurement/run."""

    measurements = session.scalars(
        select(ProcessMeasurement)
    ).all()

    rows = []
    skipped_runs = []

    for run in measurements:
        # Retrieve sensor records for this run
        electric_records = session.scalars(
            select(ElectricMeasurement).where(
                ElectricMeasurement.process_measurement_id == run.id
            )
        ).all()

        vibration_records = session.scalars(
            select(VibrationMeasurement).where(
                VibrationMeasurement.process_measurement_id == run.id
            )
        ).all()

        # Skip only when both modalities are empty
        if not electric_records and not vibration_records:
            skipped_runs.append(run.run_id)
            continue

        condition = run.condition_desc or ""

        condition_normalized = condition.strip().lower()

        healthy_conditions = {
            "healthy 1",
            "healthy 2",
            "healthy 3",
            "new motor"}

        target = int(condition_normalized not in healthy_conditions)

        # Build metadata and target
        row = {
            "run_id": run.run_id,
            "speed_sp": run.speed_sp,
            "speed_rpm": run.speed_rpm,
            "flow": run.flow,
            "pressure": run.pressure,
            "condition": condition,
            "severity": run.severity,
            "target": target,
        }

        # Aggregate each modality by channel
        modalities = [
            ("electric", electric_records),
            ("vibration", vibration_records),
        ]

        for prefix, records in modalities:
            channels = sorted({record.channel for record in records})

            for channel in channels:
                channel_records = [
                    record
                    for record in records
                    if record.channel == channel
                ]

                for feature in ("mean", "rms", "std", "peak"):
                    values = [
                        getattr(record, feature)
                        for record in channel_records
                        if getattr(record, feature) is not None
                    ]

                    feature_name = (
                        f"{prefix}_ch{channel}_{feature}"
                    )

                    # Average feature values across records
                    row[f"{feature_name}_mean"] = (
                        sum(values) / len(values)
                        if values else None
                    )

                    # Variation across records
                    row[f"{feature_name}_std"] = (
                        pd.Series(values).std()
                        if len(values) > 1 else None
                    )

        rows.append(row)

    dataset = pd.DataFrame(rows)

    print(f"Total runs: {len(measurements)}")
    print(f"Runs included: {len(dataset)}")
    print(f"Empty runs skipped: {len(skipped_runs)}")

    if skipped_runs:
        print("Skipped run IDs:")
        for run_id in skipped_runs:
            print(f"  - {run_id}")

    if not dataset.empty:
        print("\nClass counts:")
        print(dataset["target"].value_counts().sort_index())

        print(f"\nMissing feature values: {dataset.isna().sum().sum()}")

    return dataset


with SessionLocal() as session:
    dataset = build_dataset(session)

print(dataset.shape)


missing = dataset.isna().sum()
missing = missing[missing > 0].sort_values(ascending=False)

print("Features with missing values:")
print(missing)

print("\nRuns with most missing features:")
print(
    dataset.assign(
        missing_count=dataset.isna().sum(axis=1)
    )
    .sort_values("missing_count", ascending=False)[
        ["run_id", "condition", "speed_sp", "missing_count"]
    ]
    .head(10)
)

print("-----")

problem_runs = dataset.nlargest(
    4, dataset.isna().sum(axis=1).name
) if False else dataset.assign(
    missing_count=dataset.isna().sum(axis=1)
).nlargest(4, "missing_count")

for _, row in problem_runs.iterrows():
    run_id = row["run_id"]

    print(f"\n{run_id} — {row['missing_count']} missing values")

    missing_features = dataset.loc[
        dataset["run_id"] == run_id
    ].isna().iloc[0]

    print(missing_features[missing_features].index.tolist())


print(dataset.groupby(["condition", "target"]).size())
print(dataset["target"].value_counts())