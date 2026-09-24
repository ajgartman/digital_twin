from app.processing.pipeline import process_csv
import os
from app.core.config import Config
from app.processing.pipeline import process_folder
import pandas as pd

# Algorithm.
# 1. Parse, 2.Load, 3. Extract features

# TESTING ENVIRONMENT!
target_folders = ["healthy 1","healthy 2", "healthy 3"]
target_folder = ["healthy 1"]


healthy_path = "Vibration/Motor-2/50/"

healthy_data_combined = []

for folder in target_folder:

    path = healthy_path+folder
    healthy_folder_data = process_folder(path)
    healthy_data_combined.append(healthy_folder_data)

healthy_50 = pd.concat(healthy_data_combined, ignore_index=True)

print(healthy_50.shape)
print(healthy_50.head(30))
print(healthy_50.columns)



