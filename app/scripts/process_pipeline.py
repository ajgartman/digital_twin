from app.processing.pipeline import pipeline

# Algorithm. End to end pipeline to process and store features.
# 1. Parse, 2.Validate, 3.Load, 4.Extract features, 5. Load the data into database

# Select target folders
target_folders = ["impeller 1","impeller 2", "impeller 3","loose foot motor",
                  "loose foot pump","new motor","soft foot 1","soft foot 2",
                  "stator short 1","stator short 2","bearing bpfi 1","bearing bpfi 2",
                  "bearing bpfi 3","bearing bpfo 1","bearing bpfo 2","bearing bpfo 3",
                  "bearing bsf","bearing contaminated","bearing pump 1", "bearing pump 2",
                  "bearing pump 3","broken rotor bar","healthy 1","healthy 2","healthy 3"]

# Select target directory
file_path = "Vibration/Motor-2/100/"

# Run the pipeline
pipeline(file_path,target_folders)