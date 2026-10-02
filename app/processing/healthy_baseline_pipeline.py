import pandas as pd
from sqlalchemy import select
from app.database.connection import SessionLocal
from app.models.measurement_entities.orm_models import (ProcessMeasurement,
                                                        ElectricMeasurement,
                                                        VibrationMeasurement,
                                                        HealthyElectricBaseline,
                                                        HealthyVibrationBaseline)
from sqlalchemy.exc import SQLAlchemyError


# Healthy baseline pipeline
def process_single_run(measurement_type,process_run_id:str):

    if measurement_type == "electric":
        measurement_entity = ElectricMeasurement
    else:
        measurement_entity = VibrationMeasurement

    with SessionLocal() as session:

        query = select(measurement_entity).join(measurement_entity.process_measurement).where(ProcessMeasurement.run_id == process_run_id)
        result = session.scalars(query).all()

        # Process run id will be the same for the whole file.
        process_id_int = result[0].process_measurement_id

        data = [{"process_run_id": row.process_measurement.run_id,
                 "channel": row.channel,
                 "mean": row.mean,
                 "rms": row.rms,
                 "std": row.std,
                 "peak": row.peak} for row in result]

        # Creating dataframe
        dataframe = pd.DataFrame(data)

        # Grouping dataframe by channel - selecting 4 channels - applying aggregate functions to each one of them
        dataframe = dataframe.groupby("channel")[["mean", "rms", "std", "peak"]].agg(
            ["mean", "std", "min", "max"])

        # Stacking the dataframe... level = 0
        dataframe = dataframe.stack(level=0)
        # Resetting index...
        dataframe = dataframe.reset_index()
        dataframe = dataframe.rename(columns={"level_1": "feature"})

        if measurement_type == "electric":
            for row in dataframe.itertuples(index=False):
                baseline = HealthyElectricBaseline(
                    process_measurement_id=process_id_int,
                    channel = row.channel,
                    feature = row.feature,
                    mean = row.mean,
                    std = row.std,
                    feature_max = row.max,
                    feature_min = row.min
                )

                session.add(baseline)
            try:
                session.commit()
                print("Data commited successfully!")
            except SQLAlchemyError as error:
                print(error)
                session.rollback()

        elif measurement_type == "vibration":
            for row in dataframe.itertuples(index=False):
                baseline = HealthyVibrationBaseline(
                    process_measurement_id=process_id_int,
                    channel=row.channel,
                    feature=row.feature,
                    mean=row.mean,
                    std=row.std,
                    feature_max=row.max,
                    feature_min=row.min
                )

                session.add(baseline)
            try:
                session.commit()
                print("Data commited successfully!")

            except SQLAlchemyError as error:
                print(error)
                session.rollback()


def process_validation(measurement_type,measurement_id) -> bool:

    if measurement_type == "electric":
        measurement_entity = HealthyElectricBaseline
    else:
        measurement_entity = HealthyVibrationBaseline


    with SessionLocal() as session:
        # Obtaining process measurement id
        process_id = select(ProcessMeasurement.id).where(ProcessMeasurement.run_id == measurement_id)
        process_id = session.scalar(process_id)

        existing_data = select(measurement_entity).where(measurement_entity.process_measurement_id == process_id)
        existing_data = session.scalars(existing_data).first()

    if existing_data:
        return False

    return True

def healthy_baseline_pipeline(measurement_ids:list[str]):

    measurement_types = ["electric","vibration"]

    # Loading the data to the db...
    for measurement_type in measurement_types:
        for measurement_run_id in measurement_ids:
            if not process_validation(measurement_type,measurement_run_id):
                print("Healthy baseline for this ID already exists!")
                continue
            else:
                print("Validation successful!")
            process_single_run(measurement_type,measurement_run_id)
            print("Measurement run processed!")

def healthy_runs(speed_sp:int):
    pass