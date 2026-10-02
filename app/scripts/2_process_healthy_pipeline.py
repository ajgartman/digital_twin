from app.processing.healthy_baseline_pipeline import healthy_baseline_pipeline

# Description:
# Stage 2 Pipeline. Its task is to fetch processed data, calculate parameters per each channel feature and store it
# in the db for further processing.
# Calculating per-run baseline statistics.


# 1. Select, 2.Validate, 3.Process, 4. Store

# Select the measurement IDs you want to process... - dict[list]
HEALTHY_RUNS_DICT = {
    50: [
        "M2_50_healthy_1_0",
        "M2_50_healthy_2_0",
        "M2_50_healthy_3_0",
        "M2_50_new_motor_0",
    ],
    75: [
        "M2_75_healthy_1_0",
        "M2_75_healthy_2_0",
        "M2_75_healthy_3_0",
        "M2_75_new_motor_0",
    ],
    100: [
        "M2_100_healthy_1_0",
        "M2_100_healthy_2_0",
        "M2_100_healthy_3_0",
        "M2_100_new_motor_0",
    ],
}

# Run the pipeline
healthy_baseline_pipeline(HEALTHY_RUNS_DICT[50])