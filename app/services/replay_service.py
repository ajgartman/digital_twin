from app.models.validation.validation_logic import summarize_by_row
from app.services.validation_service import validate_run_func


#. Replay service will fetch the healthy baseline and then compare window/measurement by measurement with observed run,
# constantly updating the metrics for vibration and electric readings.
# Step by step...

# 1. Reusing function...
def replay(run_id:str):
    # Getting the healthy and observed data for given run!
    # Reusing the existing functions, toggling the bit
    electric_output, vibration_output = validate_run_func(run_id,replay_mode=True)

    # What we are getting is, list of dictionaries per row
    # Do we send the whole list into the function, or we do it one by one?
    for record in electric_output:
        
        result = summarize_by_row(record)
        yield result


    return electric_output, vibration_output


if __name__ == "__main__":
    results = replay("M2_50_healthy_1_0")

