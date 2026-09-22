from app.processing.pipeline import process_csv
import os
from app.core.config import Config
from app.processing.pipeline import process_folder

# Algorithm.
# 1. Parse, 2.Load, 3. Extract features

# TESTING ENVIRONMENT!
folder_path = "Electric/Motor-2/50/healthy 1"

features = process_folder(folder_path)

print(features.groupby("channel")[["mean", "rms", "std", "peak"]].mean())