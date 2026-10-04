import pandas as pd
import os
from app.ingestion.loader import load_csv
from app.ingestion.validation import validate_dataframe
from app.ingestion.metadata_parser import parser
from app.processing.feature_extraction_pipeline import extract_features_dataframe
from app.core.config import Config
from app.database.repository import get_process_measurement, check_existing_data, save_processed_data

# Processing pipeline v1.
def process_csv(path:str) -> pd.DataFrame | None:

    #. Parse the data
    metadata = parser(path)

    #. Check for assigned Process Measurement data
    process_measurement_object = get_process_measurement(metadata["run_id"])
    if not process_measurement_object:
        raise ValueError("Given CSV does not have process measurement file assigned!")

    #. Check for existing processed sensor data
    existing_data = check_existing_data(process_measurement_object,metadata)
    if existing_data:
        print(metadata)
        print("Data already exists, skipping the iteration!")
        return None

    #. Load CSV
    df = load_csv(path)

    #. Validate DataFrame
    validation = validate_dataframe(df,metadata)
    print(validation)

    if not validation["valid"]:
        print(validation["issues"])
        raise ValueError("Invalid dataframe!")

    #. Extracting features
    features = extract_features_dataframe(df,metadata)

    return features

# Processing the folder
def process_folder(folder_path:str) -> pd.DataFrame:
    list_dir = os.listdir(Config.DATASET_ROOT/folder_path)

    # Check against empty folder
    if not list_dir:
        print("Folder is empty!")
        return pd.DataFrame()

    feature_folder = []

    for file in list_dir:
        file_name = folder_path+"/"+file
        process_csv_function = process_csv(file_name)
        if process_csv_function is None:
            continue
        feature_folder.append(process_csv_function)

    if not feature_folder:
        return pd.DataFrame()
    else:
        combined = pd.concat(feature_folder,ignore_index=True)
        return combined

def pipeline(file_path:str,target_folders:list[str]) -> pd.DataFrame:

    data_combined = []
    for folder in target_folders:
        path = file_path+folder
        # Processing the folder
        processed_folder = process_folder(path)
        # Saving data to the database
        if not processed_folder.empty:
            save_processed_data(processed_folder)
            # Appending each folder into master dataframe
            data_combined.append(processed_folder)
        else:
            print("No data to process!")

    if data_combined:
        processed_master_dataframe = pd.concat(data_combined,ignore_index=True)
        return processed_master_dataframe
    else:
        print("No values were processed in this run! Returning empty dataframe...")
        return pd.DataFrame()