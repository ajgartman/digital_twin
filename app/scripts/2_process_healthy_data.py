from app.processing.healthy_feature_pipeline import healthy_feature_pipeline
from app.data.commmon.common import HEALTHY_RUNS_DICT

# Description:
# Stage 2 Pipeline. Its task is to fetch processed data, calculate parameters per each channel feature and store it
# in the db for further processing.
# Calculating per-run baseline statistics.

# 1. Select, 2.Validate, 3.Process, 4. Store

# Select the measurement IDs you want to process... - dict[list]


# Run the pipeline
healthy_feature_pipeline(HEALTHY_RUNS_DICT[50])