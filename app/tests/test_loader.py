from app.processing.pipeline import process_csv
import os
from app.processing.pipeline import process_folder
from sqlalchemy import select
import pandas as pd
from app.models.measurement_entities.orm_models import ProcessMeasurement,ElectricMeasurement
from app.database.connection import SessionLocal

session = SessionLocal()
# Algorithm.
# 1. Parse, 2.Load, 3. Extract features

# TESTING ENVIRONMENT!
target_folders = ["healthy 1","healthy 2", "healthy 3"]
target_folder = ["healthy 1"]


healthy_path = "Electric/Motor-2/50/"

healthy_data_combined = []

for folder in target_folder:

    path = healthy_path+folder
    healthy_folder_data = process_folder(path)
    healthy_data_combined.append(healthy_folder_data)

processed_dataframe = pd.concat(healthy_data_combined, ignore_index=True)
print(processed_dataframe.head(20))
print(processed_dataframe.columns)

# Step number 4. Loading the processed data to Postgres
# For now as a separate script...

# dataframe_run_id = processed_dataframe["run_id"][0] # taking the first row value...
# measurement_type = processed_dataframe["measurement_type"][0]
# channel: str = processed_dataframe["channel"][0]
# window_id = processed_dataframe["window_id"][0]
# measurement_id = processed_dataframe["measurement_id"][0]
# mean = processed_dataframe["mean"][0]
# rms = processed_dataframe["rms"][0]
# std = processed_dataframe["std"][0]
# peak = processed_dataframe["peak"][0]
# process_measurement_id = select(ProcessMeasurement.id).where(ProcessMeasurement.run_id == dataframe_run_id)
# result = session.scalars(process_measurement_id).one_or_none()
#
#
# print("Process measurement ID",result)

# Inserting the data to the db


# electric_measurement = ElectricMeasurement(
#     process_measurement_id= result,
#     measurement_type= measurement_type,
#     channel= int(channel.strip("ch")),
#     window_id= window_id,
#     measurement_id= measurement_id,
#     mean= float(mean),
#     rms = float(rms),
#     std= float(std),
#     peak= float(peak)
# )
#
# session.add(electric_measurement)
#
# session.commit()
# print("Data added!")