import pandas as pd
# Feature extractor
def extract_features_series(input_series) -> dict:

    sum_square = 0
    total_sum = 0
    max_absolute_value = 0
    nominator = 0
    n = len(input_series)

    # Calculating mean
    for row in input_series:
        total_sum += row
    mean_output = total_sum/n

    for row in input_series:
        sum_square += row ** 2
        nominator += (row - mean_output) ** 2
        if abs(row) > max_absolute_value:
            max_absolute_value = abs(row)


    rms_output = (sum_square / n) ** 0.5
    std_output = (nominator/n)**0.5
    max_abs_output = max_absolute_value

    response = {"mean":mean_output,
                "rms":rms_output,
                "std":std_output,
                "peak":max_abs_output}

    return response

def extract_features_dataframe(input_dataframe:pd.DataFrame,metadata:dict) -> pd.DataFrame:

    features_vector = []

    for column in input_dataframe.columns[1:]:
        series_features : dict = extract_features_series(input_dataframe[column])
        series_features["window_id"] = column
        series_features["measurement_id"] = int(column)//5 if metadata["measurement_type"] == "Vibration" else column
        series_features["measurement_type"] = metadata["measurement_type"]
        series_features["device"] = metadata["device"]
        series_features["speed"] = metadata["speed"]
        series_features["condition"] = metadata["condition"]
        series_features["channel"] = metadata["channel"]
        series_features["run_id"] = metadata["run_id"]
        series_features["severity"] = metadata["severity"]

        features_vector.append(series_features)

    features_vector_df = pd.DataFrame(features_vector)

    # Reordering the file columns
    features_vector_df = features_vector_df[
        ["run_id","window_id","measurement_id","channel", "measurement_type", "device", "speed", "condition", "severity",
         "mean", "rms", "std", "peak"]]

    if metadata["measurement_type"] == "Vibration":
        features_vector_df = features_vector_df.groupby(["channel","measurement_id"]).agg({
                                                        "mean": "mean",
                                                        "rms": "mean",
                                                        "std": "mean",
                                                        "peak": "mean",

                                                        "speed": "first",     # using 'first' to take the first value
                                                        "condition": "first",
                                                        "run_id": "first",
                                                        "device": "first",
                                                        "measurement_type": "first",
                                                        "severity":"first",
                                                        })
        # Resetting the index
        features_vector_df = features_vector_df.reset_index()

    return features_vector_df