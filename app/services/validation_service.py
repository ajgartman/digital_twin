from typing import Any

from pandas import DataFrame

from app.data.commmon.common import HEALTHY_RUNS_DICT
from app.models.validation.exceptions import InvalidRunIdError
from app.models.validation.validation_logic import build_healthy_baseline, summarise_validation,compare_dataframe
from app.repositories.database_access import get_observed_data


def validate_run_func(run_id:str,excluded_condition :str|None = None, replay_mode:bool = False) -> tuple[DataFrame, DataFrame, Any, Any] | tuple[dict[Any, Any],dict[Any, Any]]:

    print("Run being validated: ", run_id)
    # Getting relevant speed setpoint
    try:
        speed_sp = int(run_id.split("_")[1])
    except ValueError as e:
        raise InvalidRunIdError ("Run ID is incorrect!") from e
    except IndexError as i:
        raise InvalidRunIdError ("Run ID is incorrect!") from i

    # Getting observed dataframe
    observed_electric, observed_vibration = get_observed_data(run_id,speed_sp)
    # Getting baseline dataframe. Insert extra parameter to exclude a run! Healthy run must not be included in its own validation baseline.
    is_healthy_holdout = run_id in HEALTHY_RUNS_DICT.get(speed_sp, [])
    baseline_electric, baseline_vibration = build_healthy_baseline(speed_sp, excluded_run=excluded_condition, excluded_run_id=run_id if is_healthy_holdout else None)

    electric_output, vibration_output = compare_dataframe(observed_electric,baseline_electric,observed_vibration,baseline_vibration)
    if replay_mode:
        return electric_output, vibration_output

    summary_electric = summarise_validation(electric_output)
    summary_vibration = summarise_validation(vibration_output)

    return summary_electric, summary_vibration

if __name__ == "__main__":
    result = validate_run_func("M2_50_healthy_1_0")
    print(result[0])
    print(result[1])
