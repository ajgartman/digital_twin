from typing import Any
import pandas as pd
from pandas import DataFrame
from app.data.commmon.common import HEALTHY_RUNS_DICT
from app.database.connection import SessionLocal
from sqlalchemy import select

from app.models.database.orm_models import ProcessMeasurement, HealthyElectricFeatures, HealthyVibrationFeatures, \
    ElectricMeasurement, VibrationMeasurement
from app.models.validation.exceptions import MeasurementNotFoundError
# Separating the responsibilities - DB access

# Getting the observed measurement data first.
def get_observed_data(run_id: str,speed_sp:int) -> tuple[pd.DataFrame, pd.DataFrame]:

    with SessionLocal() as session:
        # Find the process measurement
        query = select(ProcessMeasurement).where(ProcessMeasurement.run_id == run_id)

        process_measurement = session.scalars(query).one_or_none()

        if process_measurement is None:
            raise MeasurementNotFoundError(f"No process measurement found for {run_id}")

        process_measurement_id = process_measurement.id

        # Checking if passed data belongs to healthy runs:
        if run_id in HEALTHY_RUNS_DICT[speed_sp]:
            # Get electrical data
            electric_query = select(HealthyElectricFeatures).where(HealthyElectricFeatures.process_measurement_id== process_measurement_id)
            electric_data = session.scalars(electric_query).all()

            # Get vibration data
            vibration_query = select(HealthyVibrationFeatures).where(HealthyVibrationFeatures.process_measurement_id== process_measurement_id)
            vibration_data = session.scalars(vibration_query).all()

        # If data is not from healthy set, we need to process it first...
        else:
            measurement_types = ["electric", "vibration"]
            dataframe_dict = {}

            for measurement_type in measurement_types:

                if measurement_type == "electric":
                    measurement_entity = ElectricMeasurement
                else:
                    measurement_entity = VibrationMeasurement

                query = select(measurement_entity).join(measurement_entity.process_measurement).where(ProcessMeasurement.run_id == run_id)
                query_result = session.scalars(query).all()
                # Process run id will be the same for the whole file.
                # process_id_int = result[0].process_measurement_id
                data = [{"process_run_id": row.process_measurement.run_id,
                        "channel": row.channel,
                        "mean": row.mean,
                        "rms": row.rms,
                        "std": row.std,
                        "peak": row.peak} for row in query_result]

                # Creating dataframe
                dataframe = pd.DataFrame(data)

                # A run may have no rows for one sensor modality. Preserve a
                # clear unavailable result instead of failing on groupby.
                if dataframe.empty:
                    dataframe_dict[measurement_type] = pd.DataFrame(
                        columns=["channel", "feature", "mean", "std", "min", "max"])
                    continue

                # Grouping dataframe by channel - selecting 4 channels - applying aggregate functions to each one of them
                dataframe = dataframe.groupby("channel")[["mean", "rms", "std", "peak"]].agg(
                    ["mean", "std", "min", "max"])

                # Stacking the dataframe... level = 0
                dataframe = dataframe.stack(level=0)
                # Resetting index...
                dataframe = dataframe.reset_index()
                dataframe = dataframe.rename(columns={"level_1": "feature"})
                dataframe_dict[measurement_type] = dataframe


            electric_faulty_df = dataframe_dict["electric"]
            vibration_faulty_df = dataframe_dict["vibration"]

            return electric_faulty_df, vibration_faulty_df

    # Convert vibration data to DataFrame
    vibration_df = pd.DataFrame([
        {
            "channel": row.channel,
            "feature": row.feature,
            "mean": row.mean,
            "std": row.std,
            "min": row.feature_min,
            "max": row.feature_max,
        } for row in vibration_data])

    # Convert electrical data to DataFrame
    electric_df = pd.DataFrame([
        {
            "channel": row.channel,
            "feature": row.feature,
            "mean": row.mean,
            "std": row.std,
            "min": row.feature_min,
            "max": row.feature_max,
        } for row in electric_data])

    return electric_df, vibration_df


# Getting the healthy data
def get_healthy_data(speed_sp: int, excluded_run: str | None = None, excluded_run_id: str | None = None) -> tuple[DataFrame, DataFrame, list[Any]]:

    # Exclude known fault-labelled runs that have severity 0. New motor remains
    # in the healthy pool because HEALTHY_RUNS_DICT labels it as healthy.
    condition_description_filter = ["Bearing contaminated",
                                    "Bearing BSF",
                                    "Loose foot motor",
                                    "Loose foot pump",
                                    "Broken rotor bar"]

    if excluded_run:
        condition_description_filter.append(excluded_run)

    with SessionLocal() as session:

        # Find all healthy runs for this setpoint
        query = select(ProcessMeasurement).where(ProcessMeasurement.speed_sp == speed_sp, ProcessMeasurement.severity == 0,
                                                 ProcessMeasurement.condition_desc.not_in(condition_description_filter))
        if excluded_run:
            query = query.where(ProcessMeasurement.condition_desc != excluded_run)
        # Load all healthy runs for tolerance calibration. The centre baseline below still excludes an explicitly held-out healthy run.
        calibration_runs = session.scalars(query).all()
        healthy_runs = [run for run in calibration_runs
                        if run.run_id != excluded_run_id]
        print("Runs used to set healthy baseline: ")
        for run in healthy_runs:
            print(run.run_id)

        if not healthy_runs:
            raise ValueError(f"No healthy runs available for validation at this setpoint!")

        process_measurement_ids = [h_run.id for h_run in healthy_runs]
        calibration_ids = [h_run.id for h_run in calibration_runs]

        # Get per-run electrical baseline data
        electric_query = select(HealthyElectricFeatures).where(HealthyElectricFeatures.process_measurement_id.in_(calibration_ids))
        electric_data = session.scalars(electric_query).all()

        # Get per-run vibration baseline data
        vibration_query = select(HealthyVibrationFeatures).where(HealthyVibrationFeatures.process_measurement_id.in_(calibration_ids))
        vibration_data = session.scalars(vibration_query).all()

    # Convert ORM objects to DataFrames
    electric_df = pd.DataFrame([{
            "process_measurement_id": row.process_measurement_id,
            "channel": row.channel,
            "feature": row.feature,
            "mean": row.mean,
            "std": row.std,
            "min": row.feature_min,
            "max": row.feature_max}
        for row in electric_data])

    vibration_df = pd.DataFrame([
        {
            "process_measurement_id": row.process_measurement_id,
            "channel": row.channel,
            "feature": row.feature,
            "mean": row.mean,
            "std": row.std,
            "min": row.feature_min,
            "max": row.feature_max,
        } for row in vibration_data])

    return electric_df, vibration_df,process_measurement_ids