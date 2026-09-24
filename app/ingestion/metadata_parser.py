from pathlib import Path
# Task of this function is to extract the metadata from the file path
def parser(path:str) -> dict:

    try:
        path_object = Path(path)
        path_list = path_object.parts
    except ValueError:
        print("Something went wrong!")

    sequence_of_numbers = "0123456789"
    # Data splitting
    file_name = path_object.name
    measurement_type = path_list[0]
    device = path_list[1]
    speed = int(path_list[2])
    condition = path_list[3]
    condition_no_severity = path_list[3][:-2]
    if "healthy" in condition:
        severity = "0"
        condition_no_severity = path_list[3]
    elif condition[-1] not in sequence_of_numbers:
        severity = "0"
        condition_no_severity = path_list[3]
    else:
        severity = condition[-1]

    channel = int(file_name.split(".")[0][-3:].strip("ch"))
    capital_letter = path_list[1][0]
    motor_number = device[-1]
    speed_setpoint = path_list[2]

    run_id = capital_letter + motor_number + "_" + speed_setpoint + "_" + condition_no_severity.replace(" ","_") + "_" + severity

    run_metadata = {"run_id":run_id,
                    "measurement_type":measurement_type,
                    "device":device,
                    "speed":speed,
                    "condition":condition_no_severity,
                    "severity":severity,
                    "channel":channel}

    return run_metadata

