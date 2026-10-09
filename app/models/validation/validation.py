import pandas as pd
from sqlalchemy import select
from app.database.connection import SessionLocal
from app.models.database.orm_models import (ProcessMeasurement,HealthyElectricFeatures,HealthyVibrationFeatures)

# Task of the script
# Q: Does the unseen healthy run behave consistently with our healthy model?
def get_validation_baseline(excluded_run_id: str) -> tuple[pd.DataFrame, pd.DataFrame]:

    # Used to filter out other conditions with severity 0, and speed_sp = x...
    condition_description_filter = ["Bearing contaminated",
                                    "Bearing BSF",
                                    "Loose foot motor",
                                    "Loose foot pump",
                                    "Broken rotor bar"]

    # Build temporary healthy baseline
    def aggregate_baseline(df: pd.DataFrame) -> pd.DataFrame:


        if df.empty:
            return pd.DataFrame(columns=["channel", "feature", "mean", "std","min", "max", "btw_run_std"])

        return (df.groupby(["channel", "feature"]).agg(
                mean=("mean", "mean"),
                std=("std", "mean"),
                min=("min", "min"),
                max=("max", "max"),
                btw_run_std=("mean", "std"),).reset_index())

    with SessionLocal() as session:

        # Getting the object of the excluded run
        excluded_run = session.scalars(select(ProcessMeasurement).where(ProcessMeasurement.run_id == excluded_run_id)).one_or_none()

        if excluded_run is None:
            raise ValueError(f"Run not found: {excluded_run_id}")



        # Find all healthy runs for this setpoint
        query = select(ProcessMeasurement).where(ProcessMeasurement.speed_sp == excluded_run.speed_sp,
                                                 ProcessMeasurement.severity == 0,
                                                 ProcessMeasurement.run_id != excluded_run_id,
                                                 ProcessMeasurement.condition_desc.not_in(condition_description_filter))

        healthy_runs = session.scalars(query).all()

        if not healthy_runs:
            raise ValueError(f"No healthy runs available for validation at this setpoint!")

        process_measurement_ids = [h_run.id for h_run in healthy_runs]

        # Get per-run electrical baseline data
        electric_query = select(HealthyElectricFeatures).where(HealthyElectricFeatures.process_measurement_id.in_(process_measurement_ids))
        electric_data = session.scalars(electric_query).all()

        # Get per-run vibration baseline data
        vibration_query = select(HealthyVibrationFeatures).where(HealthyVibrationFeatures.process_measurement_id.in_(process_measurement_ids))
        vibration_data = session.scalars(vibration_query).all()

    # Convert ORM objects to DataFrames
    electric_df = pd.DataFrame([{
            "channel": row.channel,
            "feature": row.feature,
            "mean": row.mean,
            "std": row.std,
            "min": row.feature_min,
            "max": row.feature_max}
        for row in electric_data])

    vibration_df = pd.DataFrame([
        {
            "channel": row.channel,
            "feature": row.feature,
            "mean": row.mean,
            "std": row.std,
            "min": row.feature_min,
            "max": row.feature_max,
        } for row in vibration_data])

    electric_baseline = aggregate_baseline(electric_df)
    vibration_baseline = aggregate_baseline(vibration_df)

    return electric_baseline, vibration_baseline


def get_observed_data(run_id: str) -> tuple[pd.DataFrame, pd.DataFrame]:

    with SessionLocal() as session:
        # Find the process measurement
        query = select(ProcessMeasurement).where(
            ProcessMeasurement.run_id == run_id)

        process_measurement = session.scalars(query).one_or_none()

        if process_measurement is None:
            raise ValueError(
                f"No process measurement found for {run_id}")

        process_measurement_id = process_measurement.id

        # Get electrical data
        electric_query = select(HealthyElectricFeatures).where(HealthyElectricFeatures.process_measurement_id== process_measurement_id)
        electric_data = session.scalars(electric_query).all()

        # Get vibration data
        vibration_query = select(HealthyVibrationFeatures).where(HealthyVibrationFeatures.process_measurement_id== process_measurement_id)
        vibration_data = session.scalars(vibration_query).all()

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

    return electric_df, vibration_df


def compare_feature(observed: pd.DataFrame, baseline: pd.DataFrame) -> dict:

    observed_std = observed["std"].item()
    observed_mean = observed["mean"].item()
    observed_min = observed["min"].item()
    observed_max = observed["max"].item()

    baseline_std = baseline["std"].item()
    baseline_mean = baseline["mean"].item()
    baseline_min = baseline["min"].item()
    baseline_max = baseline["max"].item()
    btw_run_std = baseline["btw_run_std"].item()

    # Mean deviation
    if btw_run_std <= 1e-12:
        z_score = None
    else:
        z_score = (observed_mean - baseline_mean) / btw_run_std

    # Range checks
    min_check = observed_min >= baseline_min
    max_check = observed_max <= baseline_max

    # Secondary variability check - to be CHANGED - 09/10
    std_check = observed_std <= baseline_std

    return {
        "z_score": z_score,
        "min_check": min_check,
        "max_check": max_check,
        "std_check": std_check}


def summarise_validation(results: list[dict]) -> dict:
    total = len(results)

    if total == 0:
        return {
            "max_abs_z_score": None,
            "range_violation_rate": None,
            "variability_violation_rate": None}

    z_scores = [abs(result["z_score"]) for result in results if result["z_score"] is not None]

    range_violations = sum(not result["min_check"] or not result["max_check"] for result in results)

    variability_violations = sum(not result["std_check"] for result in results)

    return {
        "max_abs_z_score": max(z_scores) if z_scores else None,
        "range_violation_rate": range_violations / total,
        "variability_violation_rate": variability_violations / total}


def validate_measurement(excluded_run_id:str):

    # Getting observed data
    observed_electric, observed_vibration = get_observed_data(excluded_run_id)
    # Getting baseline data
    baseline_electric, baseline_vibration = get_validation_baseline(excluded_run_id)

    features = ["mean","rms","std","peak"]

    electric_channels = 6
    vibration_channels = 5

    electric_output = []
    vibration_output = []

    # Electric comparison
    for channel in range(1,electric_channels+1):
        for feature in features:
            observed = observed_electric[(observed_electric["channel"] == channel) & (observed_electric["feature"] == feature)]
            baseline = baseline_electric[(baseline_electric["channel"] == channel) & (baseline_electric["feature"] == feature)]
            electric_result = compare_feature(observed, baseline)
            # Adding metadata
            electric_result['channel'] = channel
            electric_result['feature'] = feature
            # print(electric_result)
            electric_output.append(electric_result)

    # Vibration comparison
    for channel in range(1, vibration_channels + 1):
        for feature in features:
            observed = observed_vibration[
                (observed_vibration["channel"] == channel) & (observed_vibration["feature"] == feature)]
            baseline = baseline_vibration[
                (baseline_vibration["channel"] == channel) & (baseline_vibration["feature"] == feature)]
            vibration_result = compare_feature(observed, baseline)
            # Adding metadata
            vibration_result['channel'] = channel
            vibration_result['feature'] = feature
            # Appending records
            vibration_output.append(vibration_result)

    summary_electric = summarise_validation(electric_output)
    summary_vibration = summarise_validation(vibration_output)

    return summary_electric, summary_vibration

# --- --- --- ---
speed_sp = 50
excluded_runs = [f"M2_{speed_sp}_healthy_1_0",
                 f"M2_{speed_sp}_healthy_2_0",
                 f"M2_{speed_sp}_healthy_3_0",
                 f"M2_{speed_sp}_new_motor_0"]

summary_df = []
for run in excluded_runs:
    electric_summary, vibration_summary = validate_measurement(run)
    # Adding more labels to the dictionary
    electric_summary["type"] = "electric"
    electric_summary["excluded_run"] = run
    vibration_summary["type"] = "vibration"
    vibration_summary["excluded_run"] = run
    summary_df.append(electric_summary)
    summary_df.append(vibration_summary)

df_output = pd.DataFrame(summary_df)
print(df_output)
