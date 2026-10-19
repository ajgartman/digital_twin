import pandas as pd
import numpy as np
from sqlalchemy import select
from app.database.connection import SessionLocal
from app.models.database.orm_models import (ProcessMeasurement,
                                            HealthyElectricFeatures,
                                            HealthyVibrationFeatures,
                                            ElectricMeasurement, VibrationMeasurement)

from app.data.commmon.common import HEALTHY_RUNS_DICT

# Task of the script
# Q: Does the unseen healthy run behave consistently with our healthy model?
def get_healthy_baseline(speed_sp: int, excluded_run: str | None = None, excluded_run_id: str | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:

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

    # Build temporary healthy baseline
    def max_loo_deviation(values: pd.Series) -> float:
        values = pd.to_numeric(values, errors="coerce").dropna().to_numpy(dtype=float)
        if len(values) < 2:
            return np.nan
        deviations = [abs(value - float(np.median(np.delete(values, index))))
                      for index, value in enumerate(values)]
        return float(max(deviations))

    def aggregate_baseline(df: pd.DataFrame, feature_table: pd.DataFrame) -> pd.DataFrame:

        if df.empty:
            return pd.DataFrame(columns=["channel", "feature", "mean", "std", "min", "max",
                                         "median", "mad", "btw_run_std", "btw_run_std_spread",
                                         "std_median", "loo_mean_tolerance", "loo_std_tolerance"])

        # The centre and min/max envelope use only the reference runs. The tolerances are the largest leave-one-healthy-run-out deviations from
        # the other healthy runs, calibrated feature by feature.
        baseline_rows = df[df["process_measurement_id"].isin(process_measurement_ids)]

        df_result = baseline_rows.groupby(["channel", "feature"]).agg(
            mean=("mean", "mean"),  # first is column, second is the operation applied to it
            std=("std", "mean"),
            min=("min", "min"),
            max=("max", "max"),
            median=("mean", "median"),  # Adding new line 1 here too
            mad=("mean", lambda x: (x - x.median()).abs().median()),  # Adding new line 2. Mean absolute deviation
            btw_run_std=("mean", "std"),  # Between-session spread of the feature centre.
            btw_run_std_spread=("std", "std"),  # Between-session spread of the per-run variability.
            std_median=("std", "median")).reset_index()

        tolerances = feature_table.groupby(["channel", "feature"]).agg(
            loo_mean_tolerance=("mean", max_loo_deviation),
            loo_std_tolerance=("std", max_loo_deviation),).reset_index()

        df_result = df_result.merge(tolerances, on=["channel", "feature"], how="left")

        return df_result


    electric_baseline = aggregate_baseline(electric_df, electric_df.drop(columns=["process_measurement_id"]))

    vibration_baseline = aggregate_baseline(vibration_df, vibration_df.drop(columns=["process_measurement_id"]))

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


def compare_feature(observed: pd.DataFrame, baseline: pd.DataFrame) -> dict:

    result = {
        "observed_mean": None, "observed_std": None,
        "z_score": None, "std_score": None,
        "mean_check": None, "min_check": None,
        "max_check": None, "std_check": None,
        "baseline_median": None, "mad": None,
        "btw_run_std": None, "btw_run_std_spread": None,
        "mean_deviation": None, "std_deviation": None,
        "mean_tolerance": None, "std_tolerance": None,
        "mean_envelope_ratio": None, "std_envelope_ratio": None,
        "reason": None}

    # Length checks
    if len(observed) != 1:
        result["reason"] = f"expected_one_observed_row_got_{len(observed)}"
        return result
    if len(baseline) != 1:
        result["reason"] = f"expected_one_baseline_row_got_{len(baseline)}"
        return result

    obs = observed.iloc[0]
    ref = baseline.iloc[0]

    required_obs = ["mean", "std"]
    required_ref = ["median", "std_median", "loo_mean_tolerance", "loo_std_tolerance"]
    if any(pd.isna(obs.get(column)) for column in required_obs):
        result["reason"] = "non_finite_observed_value"
        return result
    if any(pd.isna(ref.get(column)) for column in required_ref):
        result["reason"] = "non_finite_baseline_value"
        return result

    observed_mean = float(obs["mean"])
    observed_std = float(obs["std"])
    baseline_median = float(ref["median"])
    baseline_std_median = float(ref["std_median"])
    mean_tolerance = max(0.0, float(ref["loo_mean_tolerance"]))
    std_tolerance = max(0.0, float(ref["loo_std_tolerance"]))
    mean_deviation = abs(observed_mean - baseline_median)
    std_deviation = abs(observed_std - baseline_std_median)
    result.update({
        "observed_mean": observed_mean,
        "observed_std": observed_std,
        "baseline_median": baseline_median,
        "mad": float(ref["mad"]) if pd.notna(ref.get("mad")) else None,
        "btw_run_std": ref.get("btw_run_std"),
        "btw_run_std_spread": ref.get("btw_run_std_spread"),
        "mean_deviation": mean_deviation,
        "std_deviation": std_deviation,
        "mean_tolerance": mean_tolerance,
        "std_tolerance": std_tolerance,})

    mean_epsilon = 1e-9 * max(1.0, abs(observed_mean), abs(baseline_median), mean_tolerance)
    std_epsilon = 1e-9 * max(1.0, abs(observed_std), abs(baseline_std_median), std_tolerance)
    result["mean_envelope_ratio"] = mean_deviation / mean_tolerance if mean_tolerance > 1e-12 else (0.0 if mean_deviation <= mean_epsilon else None)
    result["std_envelope_ratio"] = std_deviation / std_tolerance if std_tolerance > 1e-12 else (0.0 if std_deviation <= std_epsilon else None)
    # Keep the former keys available to any existing report code. These values
    # are envelope ratios, not statistical z-scores.
    result["z_score"] = result["mean_envelope_ratio"]
    result["std_score"] = result["std_envelope_ratio"]
    result["mean_check"] = mean_deviation <= mean_tolerance + mean_epsilon
    result["std_check"] = std_deviation <= std_tolerance + std_epsilon
    # Per-run min/max are intrinsically unstable with only three healthy runs;
    # retain the fields for report compatibility but do not let them veto a run.
    result["min_check"] = None
    result["max_check"] = None
    result["reason"] = "leave_one_healthy_run_out_deviation_envelope"
    return result


def summarise_validation(results: list[dict]) -> dict:
    if not results:
        return {
            "feature_count": 0,
            "evaluated_features": 0,
            "check_failures": {},
            "check_unknowns": {},
            "features_with_any_violation": 0,
            "features_with_any_violation_rate": None,
            "run_status": "INSUFFICIENT_DATA"}

    # Min/max are retained in per-feature output for compatibility, but are
    # deliberately excluded from the decision because run extrema are unstable.
    check_names = ("mean_check", "std_check")
    check_failures = {}
    check_unknowns = {}
    for name in check_names:
        check_failures[name] = sum(row.get(name) is False for row in results)
        check_unknowns[name] = sum(row.get(name) is None for row in results)

    failed_features = sum(any(row.get(name) is False for name in check_names)
                          for row in results)
    evaluated_features = sum(any(row.get(name) is not None for name in check_names)
                             for row in results)
    run_status = ("FLAG_FOR_REVIEW" if failed_features else
                  "WITHIN_HEALTHY_ENVELOPE" if evaluated_features else
                  "INSUFFICIENT_DATA")
    return {
        "feature_count": len(results),
        "evaluated_features": evaluated_features,
        "check_failures": check_failures,
        "check_unknowns": check_unknowns,
        "features_with_any_violation": failed_features,
        "features_with_any_violation_rate": failed_features / len(results),
        "run_status": run_status,
        "max_envelope_ratio": max((row[key] for row in results
                                    for key in ("mean_envelope_ratio", "std_envelope_ratio")
                                    if row.get(key) is not None), default=None)}


def validate_measurement(run_id:str,excluded_condition :str|None = None):

    print("Run being validated: ", run_id)

    # Getting relevant speed setpoint
    speed_sp = int(run_id.split("_")[1])
    # Getting observed dataframe
    observed_electric, observed_vibration = get_observed_data(run_id,speed_sp)
    # Getting baseline dataframe. Insert extra parameter to exclude a run!
    # A healthy run must not be included in its own validation baseline.
    is_healthy_holdout = run_id in HEALTHY_RUNS_DICT.get(speed_sp, [])
    baseline_electric, baseline_vibration = get_healthy_baseline(speed_sp, excluded_run=excluded_condition, excluded_run_id=run_id if is_healthy_holdout else None)

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

    # print()
    # print(f"Electric mean-check violations: {len(electric_mean_violations)}/{len(electric_output)}")
    # print(f"Vibration mean-check violations: {len(vibration_mean_violations)}/{len(vibration_output)}")

    summary_electric = summarise_validation(electric_output)
    summary_vibration = summarise_validation(vibration_output)

    # print("Electric summary:", summary_electric)
    # print("Vibration summary:", summary_vibration)

    return summary_electric, summary_vibration

if __name__ == "__main__":
    result = validate_measurement("M2_50_healthy_1_0")

    print("Electric check: ",result[0])
    print("--- --- ---")
    print("Vibration check: ",result[1])
