from sqlalchemy.exc import SQLAlchemyError
from app.database.connection import SessionLocal
from sqlalchemy import select
from app.models.db_models.orm_models import ProcessMeasurement, ElectricMeasurement,VibrationMeasurement
import pandas as pd

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
        search_result = session.scalar(search)

    return search_result

# Adding processed dataframe file to the database
def save_processed_data(dataframe:pd.DataFrame):

    # This function will process the dataframe file, folder by folder
    # Taking first row, data here does not change during the run
    with SessionLocal() as session:

        run_id = dataframe["run_id"][0]
        measurement_type = dataframe["measurement_type"][0]
        # We need process_measurement_id which can be obtained from dataframe.run_id.
        process_measurement_id = select(ProcessMeasurement.id).where(ProcessMeasurement.run_id == run_id)
        result:int = session.scalars(process_measurement_id).one_or_none()
        if result is None:
            raise ValueError(f"No process measurement found for {run_id}")

        if measurement_type == "Vibration":
            # Need to load data row by row.
            for row in dataframe.itertuples(index=False):
                channel = row.channel
                measurement_id = row.measurement_id
                mean = row.mean
                rms = row.rms
                std = row.std
                peak = row.peak

                vibration_data_object = VibrationMeasurement(
                    process_measurement_id=result,
                    channel= channel,
                    measurement_id=measurement_id,
                    mean= mean,
                    rms= rms,
                    std= std,
                    peak= peak
                )
                session.add(vibration_data_object)
            try:
                session.commit()
                print("Data commited successfully!")
            except SQLAlchemyError as error:
                print(error)
                session.rollback()

        else:
            # Measurement type is Electric
            for row in dataframe.itertuples(index=False):
                channel = row.channel
                measurement_id = row.measurement_id
                window_id = row.window_id
                mean = row.mean
                rms = row.rms
                std = row.std
                peak = row.peak

                electric_data_object = ElectricMeasurement(
                    process_measurement_id=result,
                    channel=channel,
                    window_id= window_id,
                    measurement_id=measurement_id,
                    mean=mean,
                    rms=rms,
                    std=std,
                    peak=peak
                )

                session.add(electric_data_object)
            try:
                session.commit()
                print("Data commited successfully!")
            except SQLAlchemyError as error:
                print(error)
                session.rollback()

