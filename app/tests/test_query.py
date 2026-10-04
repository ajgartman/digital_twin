import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy import select
from app.models.db_models.orm_models import ProcessMeasurement

# File to test db connection and query some data
from app.database.connection import SessionLocal


HEALTHY_RUNS = [
    "M2_50_healthy_1_0",
    "M2_50_healthy_2_0",
    "M2_50_healthy_3_0",
    "M2_50_new_motor_0",

    "M2_75_healthy_1_0",
    "M2_75_healthy_2_0",
    "M2_75_healthy_3_0",
    "M2_75_new_motor_0",

    "M2_100_healthy_1_0",
    "M2_100_healthy_2_0",
    "M2_100_healthy_3_0",
    "M2_100_new_motor_0",
]


def get_healthy_process_data():

    with SessionLocal() as session:

        query = select(ProcessMeasurement).where(
            ProcessMeasurement.run_id.in_(HEALTHY_RUNS))

        measurements = session.scalars(query).all()

    data = [
        {
            "run_id": row.run_id,
            "speed_sp": row.speed_sp,
            "speed_rpm": row.speed_rpm,
            "flow": row.flow,
            "pressure": row.pressure,
        }
        for row in measurements
    ]

    return pd.DataFrame(data)

df = get_healthy_process_data()

print(df)

plt.scatter(df["speed_rpm"], df["flow"])

plt.xlabel("Speed RPM")
plt.ylabel("Flow")
plt.title("Healthy Pump: RPM vs Flow")

plt.show()


plt.scatter(df["speed_rpm"], df["pressure"])

plt.xlabel("Speed RPM")
plt.ylabel("Pressure")
plt.title("Healthy Pump: RPM vs Pressure")

plt.show()

print(
    df.groupby("speed_rpm")["flow"]
      .agg(["count", "min", "max"])
)


print(
    df[["run_id", "speed_rpm", "flow", "pressure"]]
    .sort_values("speed_rpm")
    .to_string(index=False)
)