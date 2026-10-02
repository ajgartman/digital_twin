from app.database.connection import SessionLocal
import pandas as pd

# Opening worker session to the DB
with SessionLocal() as session:
    # Using "..." to move up one level in the directory!
    path = "../data/raw/measurement_raw_overview.csv"

    df = pd.read_csv(path)

    # for row in df.itertuples(index=False):
    #     print("Row inserted!")
    #     measurement = ProcessMeasurement(
    #         run_id=row.run_id,
    #         setup=row.setup,
    #         failure_desc=row.failure_desc,
    #         severity=row.severity,
    #         speed_sp=row.speed_sp,
    #         speed_rpm=row.speed_rpm,
    #         pressure=row.pressure,
    #         flow=row.flow)
    #     session.add(measurement)
    #
    #
    # session.commit()