# File to test db connection.
from app.database.connection import SessionLocal
from app.models.measurement_entities.orm_models import ProcessMeasurement,ElectricMeasurement

session = SessionLocal()

process_measurement_object = session.get(ProcessMeasurement,3)

print(process_measurement_object.electric_measurements)

