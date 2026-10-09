from sqlalchemy import select
from app.database.connection import SessionLocal
from app.models.database.orm_models import ProcessMeasurement

def get_healthy_performance_model(speed_sp: int) -> dict:
    # Hardcoding the run data...
    healthy_runs = {
        50: [
            "M2_50_healthy_1_0",
            "M2_50_healthy_2_0",
            "M2_50_healthy_3_0",
            "M2_50_new_motor_0",
        ],
        75: [
            "M2_75_healthy_1_0",
            "M2_75_healthy_2_0",
            "M2_75_healthy_3_0",
            "M2_75_new_motor_0",
        ],
        100: [
            "M2_100_healthy_1_0",
            "M2_100_healthy_2_0",
            "M2_100_healthy_3_0",
            "M2_100_new_motor_0",
        ],
    }

    with SessionLocal() as session:
        query = select(ProcessMeasurement).where(ProcessMeasurement.run_id.in_(healthy_runs[speed_sp]))
        healthy_runs = session.scalars(query).all()

    if not healthy_runs:
        raise ValueError(
            f"No healthy process data found for SP{speed_sp}")

    flow_values = [run.flow for run in healthy_runs]
    pressure_values = [run.pressure for run in healthy_runs]

    flow_mean = sum(flow_values) / len(flow_values) # average
    flow_std =  (sum((value - flow_mean) ** 2 for value in flow_values) / len(flow_values)) ** 0.5

    pressure_mean = sum(pressure_values) / len(pressure_values)
    pressure_std = (sum((value - pressure_mean) ** 2 for value in pressure_values) / len(pressure_values)) ** 0.5

    model = {
        "flow": {
            "mean": flow_mean,
            "std": flow_std,
            "min": min(flow_values),
            "max": max(flow_values),
        },
        "pressure": {
            "mean": pressure_mean,
            "std": pressure_std,
            "min": min(pressure_values),
            "max": max(pressure_values),
        }
    }

    return model