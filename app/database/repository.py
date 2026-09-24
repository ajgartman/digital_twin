from app.database.connection import SessionLocal
from sqlalchemy import select
from app.models.measurement_entities.orm_models import ProcessMeasurement, ElectricMeasurement,VibrationMeasurement
# Operations performed on the stored data.

# Checking if process measurement exists for given .csv file
def get_process_measurement(run_id):
    with SessionLocal() as session:
        search = select(ProcessMeasurement).where(ProcessMeasurement.run_id == run_id)
        search_result = session.scalars(search).one_or_none()

        return search_result

# Checking if given .csv file already has processed data stored in the database.
def check_existing_data(process_measurement,metadata):

    measurement_type = metadata["measurement_type"]
    channel = metadata["channel"]

    if measurement_type == "Electric":
        entity = ElectricMeasurement
    else:
        entity = VibrationMeasurement

    with SessionLocal() as session:
        search = select(entity.id).where(entity.process_measurement_id == process_measurement.id).where(entity.channel == channel)
        search_result = session.scalars(search).one_or_none()

    return search_result