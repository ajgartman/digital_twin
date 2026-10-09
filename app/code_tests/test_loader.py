from app.processing.raw_data_pipeline import pipeline

# Algorithm.
# 1. Parse, 2.Load, 3. Extract features, 4. Load the data into database

# TESTING ENVIRONMENT!

target_folders = ["impeller 1","impeller 2", "impeller 3","loose foot motor", "loose foot pump","new motor","soft foot 1","soft foot 2","stator short 1","stator short 2",
                  "bearing bpfi 1","bearing bpfi 2","bearing bpfi 3","bearing bpfo 1","bearing bpfo 2","bearing bpfo 3","bearing bsf","bearing contaminated",
          "bearing pump 1", "bearing pump 2", "bearing pump 3","broken rotor bar","healthy 1","healthy 2","healthy 3"]

file_path = "Vibration/Motor-2/100/"

# pipeline(file_path,target_folders)
