import pandas as pd
# Validation function
# Checks loaded dataset against expected healthy baseline and returns structured dictionary as the response.
def validate_dataframe(df:pd.DataFrame,run_metadata:dict) -> dict:

    valid = True
    status = "OK"
    expected_samples = 0
    actual_samples = len(df)
    issues = []
    run_id = run_metadata["run_id"]
    channel = run_metadata["channel"]

    # No. of samples expected:
    measurement_type = run_metadata["measurement_type"]
    if measurement_type == "Electric":
        expected_samples = 300000
    elif measurement_type == "Vibration":
        expected_samples = 240000
    else:
        status = "ERROR"
        message = "Can't read the measurement type!"
        issues.append(message)

    # Condition 1. Dataset sample count differs from expected
    if 0.95 * expected_samples < actual_samples < expected_samples or expected_samples < actual_samples < 1.05 * expected_samples:
        status = "WARNING" if status != "ERROR" else "ERROR"
        message = "There is a mismatch in number of samples!"
        issues.append(message)
    # Condition 2. Dataset is missing more than 5% of its samples
    if len(df)<0.95*expected_samples:
        status = "ERROR"
        message = "Dataset is missing 5% or more of its samples!"
        issues.append(message)
    # Condition 3. Empty dataset
    if df.empty:
        status = "ERROR"
        message = "DataFrame is empty!"
        issues.append(message)
    # Condition 4. Dataset contains NULL cells
    if df.isnull().values.any():
        status = "ERROR"
        message = "DataFrame contains empty cells!"
        issues.append(message)

    if status == "ERROR":
        valid = False
    else:
        valid = True

    # Response dictionary
    response = {"run_id":run_id,
                "channel":channel,
                "valid":valid,
                "status":status,
                "expected_samples":expected_samples,
                "actual_samples":actual_samples,
                "issues":issues}

    return response