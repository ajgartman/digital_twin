import pandas as pd
from app.database.connection import SessionLocal
from sqlalchemy import select
from app.models.db_models.orm_models import ElectricMeasurement,ProcessMeasurement,VibrationMeasurement

# ---- Processing pipeline for healthy baseline calculation ----
# Selecting healthy data for specific setpoint, group by channel and feature, calculate mean/std/min/max

#session = SessionLocal()

# Selecting setpoint and measurement type
SETPOINT = 50
MEASUREMENT_TYPE = "Electric"

HEALTHY_MEASUREMENT_DATA = ['M2_50_healthy_1_0',
                            'M2_50_healthy_2_0',
                            'M2_50_healthy_3_0',
                            'M2_75_healthy_1_0',
                            'M2_75_healthy_2_0',
                            'M2_75_healthy_3_0',
                            'M2_100_healthy_1_0',
                            'M2_100_healthy_2_0',
                            'M2_100_healthy_3_0',
                            'M2_50_new_motor_0',
                            'M2_75_new_motor_0',
                            'M2_100_new_motor_0']
