MSc January Intake Final Project - "Digital Twin of Drumfos centrifugal pump for performance monitoring and fault detection"

## Overview

The project uses experimentally collected centrifugal pump data to build a software-based representation of healthy pump behaviour and support performance monitoring and anomaly detection.

The system processes electrical and vibration measurements, extracts signal features, builds healthy operating baselines, and exposes the processed data through a software architecture suitable for future digital-twin visualisation.

## Project Pipeline

1. Raw Experimental Data
2. Data Ingestion & Validation     
3. Feature Extraction     
4. Processed Measurements     
5. Per-Run Healthy Baselines     
6. Setpoint Healthy Baseline
7. Anomaly Detection / Digital Twin


## Project Log
## Project Log

| Date | Description | Time Spent |
|---|---|---:|
| 16-Sep | Created Gantt Chart, registered the project, created fault candidate list, feature and classes, created project log, literature review started, dataset mapping | 4h |
| 17-Sep | Investigated faults, counted runs, expanded Excel sheet | 3h |
| 18-Sep | Categorized faults, created fault families, counted each fault windows and runs | 3h |
| 19-Sep | Set up FastAPI project, loader/validation functions, testing one healthy dataset window | 2h 15m |
| 20-Sep | Worked further on loader/parser/validate pipeline, testing edge cases | 2h 30m |
| 21-Sep | Worked on feature extraction, validation, and DataFrame library. Created dataset of all features for Healthy 50% | 4h 15m |
| 22-Sep | Extracted healthy data for all runs, created new function to search through all the files, set up PostgreSQL connection, validated data | 4h |
| 23-Sep | Built ORM models, modified process measurement data, created uniform IDs | 4h |
| 24-Sep | Worked on data pipeline, ID processing, added validation steps | 4h |
| 25-Sep | Data pipeline, loading data into DB, edge cases, handling already processed data | 3h |
| 26-Sep | — | 0h |
| 27-Sep | — | 0h |
| 28-Sep | Populated all tables, finished ETL pipeline, started healthy baseline pipeline | 4h |
| 29-Sep | — | 0h |
| 30-Sep | Worked on healthy baseline, added Alembic migrations | 2h 30m |
| 01-Oct | Finished healthy baseline, populated tables, started creating healthy setpoint entities | 2h |