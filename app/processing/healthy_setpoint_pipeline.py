import pandas as pd
from sqlalchemy import select
from app.database.connection import SessionLocal
from sqlalchemy.exc import SQLAlchemyError

from app.models.db_models.orm_models import ProcessMeasurement, HealthyVibrationBaseline, \
    HealthyElectricBaseline, HealthySetpointBaseline


def get_baseline_data(run_id:str):

    with SessionLocal() as session:
        # Getting the measurement id INT
        measurement_id = select(ProcessMeasurement.id).where(ProcessMeasurement.run_id == run_id)
        measurement_id = session.scalar(measurement_id)

        # Getting the baseline data for both Electric and Vibration...
        vibration_data = select(HealthyVibrationBaseline).where(HealthyVibrationBaseline.process_measurement_id == measurement_id)
        vibration_data = session.scalars(vibration_data).all()

        electric_data = select(HealthyElectricBaseline).where(HealthyElectricBaseline.process_measurement_id == measurement_id)
        electric_data = session.scalars(electric_data).all()

        return vibration_data,electric_data



def get_setpoint_data(speed_sp: int,healthy_run_data:dict):

    runs = healthy_run_data[speed_sp]
    vibration_frames = []
    electric_frames = []

    for run_id in runs:

        vibration_data, electric_data = get_baseline_data(run_id)
        vibration_df = pd.DataFrame([
            {
                "run_id": run_id,
                "channel": row.channel,
                "feature": row.feature,
                "mean": row.mean,
                "std": row.std,
                "feature_min": row.feature_min,
                "feature_max": row.feature_max,
            }
            for row in vibration_data
        ])

        electric_df = pd.DataFrame([
            {
                "run_id": run_id,
                "channel": row.channel,
                "feature": row.feature,
                "mean": row.mean,
                "std": row.std,
                "feature_min": row.feature_min,
                "feature_max": row.feature_max,
            }
            for row in electric_data
        ])

        vibration_frames.append(vibration_df)
        electric_frames.append(electric_df)

    # Outputting two dataframes
    vibration_df = pd.concat(vibration_frames, ignore_index=True)
    electric_df = pd.concat(electric_frames, ignore_index=True)

    # Grouping by and applying aggregate functions - mean/std - mean, min/max - min/max across all the runs
    vibration_setpoint_baseline = (
        vibration_df
        .groupby(["channel", "feature"])
        .agg(
            mean=("mean", "mean"),
            std=("std", "mean"),
            feature_min=("feature_min", "min"),
            feature_max=("feature_max", "max"),
        )
        .reset_index()
    )
    # Adding columns to match the DB schema - vibration
    vibration_setpoint_baseline["speed_sp"] = speed_sp
    vibration_setpoint_baseline["measurement_type"] = "vibration"
    # Reordering columns
    vibration_setpoint_baseline = vibration_setpoint_baseline[["speed_sp","measurement_type","channel","feature","mean","std","feature_min","feature_max"]]

    electric_setpoint_baseline = (
        electric_df
        .groupby(["channel", "feature"])
        .agg(
            mean=("mean", "mean"),
            std=("std", "mean"),
            feature_min=("feature_min", "min"),
            feature_max=("feature_max", "max"),
        )
        .reset_index()
    )
    # Adding columns to match the DB schema - electric
    electric_setpoint_baseline["speed_sp"] = speed_sp
    electric_setpoint_baseline["measurement_type"] = "electric"
    # Reordering columns
    electric_setpoint_baseline = electric_setpoint_baseline[
        ["speed_sp", "measurement_type", "channel", "feature", "mean", "std", "feature_min", "feature_max"]]

    return vibration_setpoint_baseline,electric_setpoint_baseline


def save_setpoint_baseline(speed_sp: int,healthy_run_data:dict):

    # Duplicate check
    if healthy_setpoint_duplicate_check(speed_sp):
        print(f"Baseline for SP{speed_sp} already exists. Skipping.")
        return

    vibration_df, electric_df = get_setpoint_data(speed_sp,healthy_run_data)

    setpoint_baseline = pd.concat(
        [vibration_df, electric_df],
        ignore_index=True
    )

    with SessionLocal() as session:
        try:
            for row in setpoint_baseline.itertuples(index=False):
                baseline = HealthySetpointBaseline(
                    speed_sp=row.speed_sp,
                    measurement_type=row.measurement_type,
                    channel=row.channel,
                    feature=row.feature,
                    mean=row.mean,
                    std=row.std,
                    feature_min=row.feature_min,
                    feature_max=row.feature_max,
                )

                session.add(baseline)
            print("Data saved successfully!")
            session.commit()

        except SQLAlchemyError as error:
            print(error)
            session.rollback()

def healthy_setpoint_duplicate_check(speed_sp:int):

    with SessionLocal() as session:
        query = select(HealthySetpointBaseline).where(
            HealthySetpointBaseline.speed_sp == speed_sp
        )

        existing_baseline = session.scalars(query).first()

        return existing_baseline is not None

