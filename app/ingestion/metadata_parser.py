from pathlib import Path
# Task of this function is to extract the metadata from the file path

def parser(path:str) -> dict:

    path_object = Path(path)
    path_list = path_object.parts

    # Channel selection
    channel_path = path_object.name

    channel = channel_path.split(".")[0][-3:]

    run_metadata = {"measurement_type":path_list[0],
                    "device":path_list[1],
                    "speed":int(path_list[2]),
                    "condition":path_list[3],
                    "channel":channel}

    return run_metadata
