from app.database.connection import SessionLocal
from sqlalchemy import select
from app.models.measurement_entities.orm_models import ElectricMeasurement,ProcessMeasurement,VibrationMeasurement

# Processing pipeline for healthy baseline calculation
# Selecting healthy data for specific setpoint, group by channel and feature, calculate mean/std/min/max

session = SessionLocal()

# Selecting setpoint and measurement type
SETPOINT = 50
MEASUREMENT_TYPE = "Electric"

MEASUREMENT_IDS = [ "M2_50_Healthy_1_0",
                    "M2_50_Healthy_2_0",
                    "M2_50_Healthy_3_0"]


test = "M2_50_Healthy_1_0"


# query = select(ElectricMeasurement).where(ElectricMeasurement.process_measurement)
# search_result = session.scalars(query).all()

# print(search_result)