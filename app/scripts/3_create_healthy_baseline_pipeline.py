import pandas as pd
from sqlalchemy import select
from app.database.connection import SessionLocal
from sqlalchemy.exc import SQLAlchemyError

from app.models.measurement_entities.orm_models import ProcessMeasurement, HealthyVibrationBaseline, \
    HealthyElectricBaseline

# Description:
# Stage 3 Pipeline. It processes healthy data to create baseline for each setpoint
# Calculating healthy baseline.
HEALTHY_RUNS = {
    50: [
        "M2_50_healthy_1_0",
        "M2_50_healthy_2_0",
        "M2_50_healthy_3_0",
        "M2_50_new_motor_0",
    ],
    75: [
        "M2_75_healthy_1_0",
        "M2_75_healthy_2_0",
        "M2_75_healthy_3_0",
        "M2_75_new_motor_0",
    ],
    100: [
        "M2_100_healthy_1_0",
        "M2_100_healthy_2_0",
        "M2_100_healthy_3_0",
        "M2_100_new_motor_0",
    ],
}

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


import pandas as pd


def get_setpoint_data(speed_sp: int):

    runs = HEALTHY_RUNS[speed_sp]
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

    return vibration_df, electric_df


vibration_dataframe, electric_dataframe = get_setpoint_data(50)

grouped_vibration = vibration_dataframe.groupby(["channel", "feature"])


group = vibration_dataframe[
    (vibration_dataframe["channel"] == 1) &
    (vibration_dataframe["feature"] == "mean")
]

result = {
    "mean": float(group["mean"].mean()),
    "std": float(group["std"].mean()),
    "feature_min": float(group["feature_min"].min()),
    "feature_max": float(group["feature_max"].max()),
}

print(result)
