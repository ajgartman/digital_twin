import pandas as pd
import numpy as np
from app.repositories.database_access import get_healthy_data

# Task of the script
# Q: Does the unseen healthy run behave consistently with our healthy model?
def build_healthy_baseline(speed_sp: int, excluded_run: str | None = None, excluded_run_id: str | None = None):

    # Calling the db access function now
    electric_df, vibration_df, process_measurement_ids = get_healthy_data(speed_sp, excluded_run, excluded_run_id)

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


def compare_feature(observed: pd.DataFrame, baseline: pd.DataFrame) -> dict:

    result_f = {
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
        result_f["reason"] = f"expected_one_observed_row_got_{len(observed)}"
        return result_f
    if len(baseline) != 1:
        result_f["reason"] = f"expected_one_baseline_row_got_{len(baseline)}"
        return result_f

    obs = observed.iloc[0]
    ref = baseline.iloc[0]

    required_obs = ["mean", "std"]
    required_ref = ["median", "std_median", "loo_mean_tolerance", "loo_std_tolerance"]
    if any(pd.isna(obs.get(column)) for column in required_obs):
        result_f["reason"] = "non_finite_observed_value"
        return result_f
    if any(pd.isna(ref.get(column)) for column in required_ref):
        result_f["reason"] = "non_finite_baseline_value"
        return result_f

    observed_mean = float(obs["mean"])
    observed_std = float(obs["std"])
    baseline_median = float(ref["median"])
    baseline_std_median = float(ref["std_median"])
    mean_tolerance = max(0.0, float(ref["loo_mean_tolerance"]))
    std_tolerance = max(0.0, float(ref["loo_std_tolerance"]))
    mean_deviation = abs(observed_mean - baseline_median)
    std_deviation = abs(observed_std - baseline_std_median)
    result_f.update({
        "observed_mean": observed_mean,
        "observed_std": observed_std,
        "baseline_median": baseline_median,
        "mad": float(ref["mad"]) if pd.notna(ref.get("mad")) else None,
        "btw_run_std": float(ref.get("btw_run_std")),
        "btw_run_std_spread": float(ref.get("btw_run_std_spread")),
        "mean_deviation": mean_deviation,
        "std_deviation": std_deviation,
        "mean_tolerance": mean_tolerance,
        "std_tolerance": std_tolerance,})

    mean_epsilon = 1e-9 * max(1.0, abs(observed_mean), abs(baseline_median), mean_tolerance)
    std_epsilon = 1e-9 * max(1.0, abs(observed_std), abs(baseline_std_median), std_tolerance)
    result_f["mean_envelope_ratio"] = mean_deviation / mean_tolerance if mean_tolerance > 1e-12 else (0.0 if mean_deviation <= mean_epsilon else None)
    result_f["std_envelope_ratio"] = std_deviation / std_tolerance if std_tolerance > 1e-12 else (0.0 if std_deviation <= std_epsilon else None)
    # Keep the former keys available to any existing report code. These values
    # are envelope ratios, not statistical z-scores.
    result_f["z_score"] = result_f["mean_envelope_ratio"]
    result_f["std_score"] = result_f["std_envelope_ratio"]
    result_f["mean_check"] = mean_deviation <= mean_tolerance + mean_epsilon
    result_f["std_check"] = std_deviation <= std_tolerance + std_epsilon
    # Per-run min/max are intrinsically unstable with only three healthy runs; # retain the fields for report compatibility but do not let them veto a run.
    result_f["min_check"] = None
    result_f["max_check"] = None
    result_f["reason"] = "leave_one_healthy_run_out_deviation_envelope"
    return result_f


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

    # Min/max are retained in per-feature output for compatibility, but are deliberately excluded from the decision because run extrema are unstable.
    check_names = ("mean_check", "std_check")
    check_failures = {}
    check_unknowns = {}
    for name in check_names:
        check_failures[name] = sum(row.get(name) is False for row in results)
        check_unknowns[name] = sum(row.get(name) is None for row in results)

    failed_features = sum(any(row.get(name) is False for name in check_names) for row in results)
    evaluated_features = sum(any(row.get(name) is not None for name in check_names) for row in results)
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


def summarize_by_row(data_dict:dict):

    mean_check = data_dict["mean_check"]
    std_check = data_dict["std_check"]
    min_check = data_dict["min_check"]
    max_check = data_dict["max_check"]
    channel = data_dict["channel"]
    feature = data_dict["feature"]
    run_status = "FLAG FOR REVIEW" if not mean_check or not std_check else "WITHIN HEALTHY ENVELOPE"

    result = {
        "mean_check":mean_check,
        "std_check":std_check,
        "min_check":min_check,
        "max_check":max_check,
        "channel":channel,
        "feature":feature,
        "run_status":run_status
    }

    return result


def compare_dataframe(observed_electric:pd.DataFrame,
                       baseline_electric:pd.DataFrame,
                       observed_vibration:pd.DataFrame,
                       baseline_vibration:pd.DataFrame,):

    features = ["mean", "rms", "std", "peak"]
    electric_channels = 6
    vibration_channels = 5
    electric_output = []
    vibration_output = []

    # So we are going through every channel... one by one. And then by the feature.
    # Electric comparison
    for channel in range(1, electric_channels + 1):
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

    return electric_output, vibration_output


if __name__ == "__main__":
    pass