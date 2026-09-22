from pathlib import Path
# Task of this function is to extract the metadata from the file path

def parser(path:str) -> dict:

    try:
        path_object = Path(path)
        path_list = path_object.parts
    except ValueError:
        print("Something went wrong!")

    # File name
    file_name = path_object.name
    measurement_type = path_list[0]
    device = path_list[1]
    speed = int(path_list[2])
    condition = path_list[3]
    channel = file_name.split(".")[0][-3:]
    run_id = path_list[0][0] + path_list[1][0] + path_list[2] + "_" + path_list[3].replace(" ","_")


    run_metadata = {"run_id":run_id,
                    "measurement_type":measurement_type,
                    "device":device,
                    "speed":speed,
                    "condition":condition,
                    "channel":channel}

    return run_metadata
