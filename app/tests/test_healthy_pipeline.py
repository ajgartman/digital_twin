import pandas as pd

from app.database.connection import SessionLocal
from sqlalchemy import select
from app.models.measurement_entities.orm_models import ElectricMeasurement,ProcessMeasurement,VibrationMeasurement
from sqlalchemy.orm import Mapped

# Processing pipeline for healthy baseline calculation
# Selecting healthy data for specific setpoint, group by channel and feature, calculate mean/std/min/max

session = SessionLocal()

# Selecting setpoint and measurement type
SETPOINT = 50
MEASUREMENT_TYPE = "Electric"

MEASUREMENT_IDS = [ 'M2_50_healthy_1_0',
                    'M2_50_healthy_2_0',
                    'M2_50_healthy_3_0']

test = ["M2_50_healthy_1_0"]

query = select(ElectricMeasurement).join(ElectricMeasurement.process_measurement).where(ProcessMeasurement.severity == 0).where(ProcessMeasurement.speed_sp == 50).where(ProcessMeasurement.run_id.in_(test))
result= session.scalars(query).all()

data = [{"process_id":row.process_measurement.run_id,
        "channel":row.channel,
         "mean":row.mean,
         "rms": row.rms,
         "std":row.std,
         "peak":row.peak} for row in result]

df = pd.DataFrame(data)

print(df.groupby("channel")[["mean", "rms", "std", "peak"]].agg(
    ["mean", "std", "min", "max"]))

print(df.columns)
print(df.shape)
print(df.head(20))
