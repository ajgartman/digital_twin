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
    condition_no_severity = path_list[3][:-1]
    if "healthy" in condition:
        severity = "0"
    elif condition[-1] not in sequence_of_numbers:
        severity = "0"
    else:
        severity = condition[-1]

    channel = file_name.split(".")[0][-3:]
    run_id = path_list[1][0]+ device[-1]+ "_" + path_list[2] + "_" + path_list[3].replace(" ","_") + "_" + severity

    run_metadata = {"run_id":run_id,
                    "measurement_type":measurement_type,
                    "device":device,
                    "speed":speed,
                    "condition":condition_no_severity,
                    "severity":severity,
                    "channel":channel}

    return run_metadata

