import pandas as pd
from sqlalchemy import select
from app.database.connection import SessionLocal
from app.models.database.orm_models import (ProcessMeasurement,
                                            HealthyElectricFeatures,
                                            HealthyVibrationFeatures,
                                            ElectricMeasurement, VibrationMeasurement)

from app.data.commmon.common import HEALTHY_RUNS_DICT

# Task of the script
# Q: Does the unseen healthy run behave consistently with our healthy model?
def get_healthy_baseline(speed_sp: int, excluded_run: str | None = None,
                         excluded_run_id: str | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:

    # Used to filter out other conditions with severity 0, and speed_sp = x...
    # Add 'Healthy 1', 'Healthy 2', 'Healthy 3' or 'New motor' to exclude given run and perform healthy validation...
    condition_description_filter = ["Bearing contaminated",
                                    "Bearing BSF",
                                    "Loose foot motor",
                                    "Loose foot pump",
                                    "Broken rotor bar",
                                    "New motor"] # Temporary excluding the motor

    if excluded_run:
        condition_description_filter.append(excluded_run)

    with SessionLocal() as session:

        # Find all healthy runs for this setpoint
        query = select(ProcessMeasurement).where(ProcessMeasurement.speed_sp == speed_sp,
                                                 ProcessMeasurement.severity == 0,
                                                 ProcessMeasurement.condition_desc.not_in(condition_description_filter))
        if excluded_run:
            query = query.where(ProcessMeasurement.condition_desc != excluded_run)
        if excluded_run_id:
            query = query.where(ProcessMeasurement.run_id != excluded_run_id)

        healthy_runs = session.scalars(query).all()
        print("Runs used to set healthy baseline: ")
        for run in healthy_runs:
            print(run.run_id)

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

    # Build temporary healthy baseline
    def aggregate_baseline(df: pd.DataFrame) -> pd.DataFrame:

        if df.empty:
            return pd.DataFrame(columns=["channel", "feature", "mean", "std", "min", "max",
                                         "median", "mad", "btw_run_std", "btw_run_std_spread"])

        df_result = df.groupby(["channel", "feature"]).agg(
            mean=("mean", "mean"),  # first is column, second is the operation applied to it
            std=("std", "mean"),
            min=("min", "min"),
            max=("max", "max"),
            median=("mean", "median"),  # Adding new line 1 here too
            mad=("mean", lambda x: (x - x.median()).abs().median()),  # Adding new line 2. Mean absolute deviation
            btw_run_std=("mean", "std"),  # Between-session spread of the feature center.
            btw_run_std_spread=("std", "std"),  # Between-session spread of the per-run variability.
        ).reset_index()

        return df_result


    electric_baseline = aggregate_baseline(electric_df)
    vibration_baseline = aggregate_baseline(vibration_df)

    return electric_baseline, vibration_baseline


def get_observed_data(run_id: str,speed_sp:int) -> tuple[pd.DataFrame, pd.DataFrame]:

    with SessionLocal() as session:
        # Find the process measurement
        query = select(ProcessMeasurement).where(ProcessMeasurement.run_id == run_id)

        process_measurement = session.scalars(query).one_or_none()

        if process_measurement is None:
            raise ValueError(
                f"No process measurement found for {run_id}")

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
                result = session.scalars(query).all()
                # Process run id will be the same for the whole file.
                # process_id_int = result[0].process_measurement_id
                data = [{"process_run_id": row.process_measurement.run_id,
                        "channel": row.channel,
                        "mean": row.mean,
                        "rms": row.rms,
                        "std": row.std,
                        "peak": row.peak} for row in result]

                # Creating dataframe
                dataframe = pd.DataFrame(data)

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


def compare_feature(observed: pd.DataFrame, baseline: pd.DataFrame,
                    z_threshold: float = 3.0) -> dict:
    """Compare one observed channel-feature row with its healthy reference. """
    result = {
        "observed_mean": None, "observed_std": None,
        "z_score": None, "std_score": None,
        "mean_check": None, "min_check": None,
        "max_check": None, "std_check": None,
        "baseline_median": None, "mad": None,
        "btw_run_std": None, "btw_run_std_spread": None,
        "reason": None,
    }
    if len(observed) != 1:
        result["reason"] = f"expected_one_observed_row_got_{len(observed)}"
        return result
    if len(baseline) != 1:
        result["reason"] = f"expected_one_baseline_row_got_{len(baseline)}"
        return result

    obs = observed.iloc[0]
    ref = baseline.iloc[0]
    required_obs = ["mean", "std", "min", "max"]
    required_ref = ["min", "max", "std", "median", "mad"]
    if any(pd.isna(obs.get(column)) for column in required_obs):
        result["reason"] = "non_finite_observed_value"
        return result
    if any(pd.isna(ref.get(column)) for column in required_ref):
        result["reason"] = "non_finite_baseline_value"
        return result

    observed_mean = float(obs["mean"])
    observed_std = float(obs["std"])
    baseline_median = float(ref["median"])
    mad = float(ref["mad"])
    result.update({
        "observed_mean": observed_mean,
        "observed_std": observed_std,
        "baseline_median": baseline_median,
        "mad": mad,
        "btw_run_std": ref.get("btw_run_std"),
        "btw_run_std_spread": ref.get("btw_run_std_spread"),})

    if mad > 1e-12:
        robust_z_score = 0.6745 * (observed_mean - baseline_median) / mad
        result["z_score"] = robust_z_score
        result["mean_check"] = abs(robust_z_score) <= z_threshold
    else:
        result["reason"] = "mean_scale_zero_or_too_small"

    result["min_check"] = float(obs["min"]) >= float(ref["min"])
    result["max_check"] = float(obs["max"]) <= float(ref["max"])

    # Compare like quantities: observed between-window std against the healthy
    # sessions' between-run spread of that same per-run std statistic.
    std_spread = ref.get("btw_run_std_spread")
    if pd.notna(std_spread) and float(std_spread) > 1e-12:
        std_score = (observed_std - float(ref["std"])) / float(std_spread)
        result["std_score"] = std_score
        result["std_check"] = abs(std_score) <= z_threshold
    else:
        result["reason"] = result["reason"] or "std_reference_spread_unavailable"
    return result


def summarise_validation(results: list[dict]) -> dict:
    """Summarize check failures and unique affected features separately."""
    if not results:
        return {
            "feature_count": 0,
            "check_failures": {},
            "check_unknowns": {},
            "features_with_any_violation": 0,
            "features_with_any_violation_rate": None}

    check_names = ("mean_check", "min_check", "max_check", "std_check")
    check_failures = {}
    check_unknowns = {}
    for name in check_names:
        check_failures[name] = sum(row.get(name) is False for row in results)
        check_unknowns[name] = sum(row.get(name) is None for row in results)

    failed_features = sum(any(row.get(name) is False for name in check_names)
                          for row in results)
    return {
        "feature_count": len(results),
        "check_failures": check_failures,
        "check_unknowns": check_unknowns,
        "features_with_any_violation": failed_features,
        "features_with_any_violation_rate": failed_features / len(results),
        "max_abs_z_score": max((abs(row["z_score"]) for row in results if row.get("z_score") is not None), default=None),
    }

def validate_measurement(run_id:str,excluded_condition :str|None = None):

    print("Run being validated: ", run_id)

    # Getting relevant setpoint
    speed_sp = int(run_id.split("_")[1])

    # Getting observed dataframe
    observed_electric, observed_vibration = get_observed_data(run_id,speed_sp)
    # Getting baseline dataframe. Insert extra parameter to exclude a run!
    # A healthy run must not be included in its own validation baseline.
    is_healthy_holdout = run_id in HEALTHY_RUNS_DICT.get(speed_sp, [])
    baseline_electric, baseline_vibration = get_healthy_baseline(
        speed_sp,
        excluded_run=excluded_condition,
        excluded_run_id=run_id if is_healthy_holdout else None,)

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
            electric_output.append(electric_result)

    # Vibration comparison
    for channel in range(1, vibration_channels + 1):
        for feature in features:
            observed = observed_vibration[(observed_vibration["channel"] == channel) & (observed_vibration["feature"] == feature)]
            baseline = baseline_vibration[(baseline_vibration["channel"] == channel) & (baseline_vibration["feature"] == feature)]
            vibration_result = compare_feature(observed, baseline)
            # Adding metadata
            vibration_result['channel'] = channel
            vibration_result['feature'] = feature
            # Appending records
            vibration_output.append(vibration_result)

    # None means a check could not be evaluated; do not count it as a violation.
    electric_mean_violations = [r for r in electric_output if r["mean_check"] is False]
    vibration_mean_violations = [r for r in vibration_output if r["mean_check"] is False]

    print()
    print(f"Electric mean-check violations: {len(electric_mean_violations)}/{len(electric_output)}")
    print(f"Vibration mean-check violations: {len(vibration_mean_violations)}/{len(vibration_output)}")

    summary_electric = summarise_validation(electric_output)
    summary_vibration = summarise_validation(vibration_output)

    print("Electric summary:", summary_electric)
    print("Vibration summary:", summary_vibration)
    return summary_electric, summary_vibration


if __name__ == "__main__":
    result = validate_measurement("M2_100_bearing_bpfi_1")