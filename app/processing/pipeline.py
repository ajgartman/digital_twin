import pandas as pd
import os
from app.ingestion.loader import load_csv
from app.ingestion.validation import validate_dataframe
from app.ingestion.metadata_parser import parser
from app.processing.features import extract_features_dataframe
from app.core.config import Config
from app.database.repository import get_process_measurement, check_existing_data

# Processing pipeline v1.

def process_csv(path:str) -> pd.DataFrame:

    #. Parse the data
    metadata = parser(path)

    #. Check for assigned Process Measurement data
    process_measurement_object = get_process_measurement(metadata["run_id"])
    if not process_measurement_object:
        raise ValueError("Given CSV does not have process measurement file assigned!")

    #. Check for existing processed sensor data
    existing_data = check_existing_data(process_measurement_object,metadata)
    if existing_data:
        raise ValueError("Processed data already exists for this file!")

    #. Load CSV
    df = load_csv(path)

    #. Validate DataFrame
    validation = validate_dataframe(df,metadata)
    print(validation)

    if not validation["valid"]:
        raise ValueError("Invalid dataframe!")

    #. Extracting features
    features = extract_features_dataframe(df,metadata)

    return features

# Processing the folder
def process_folder(folder_path:str) -> pd.DataFrame:
    list_dir = os.listdir(Config.DATASET_ROOT/folder_path)

    feature_folder = []

    for file in list_dir:
        file_name = folder_path+"/"+file
        feature = process_csv(file_name)
        feature_folder.append(feature)

    combined = pd.concat(feature_folder,ignore_index=True)

    return combined
