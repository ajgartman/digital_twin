from app.processing.healthy_setpoint_pipeline import save_setpoint_baseline
# Description:
# Stage 3 Pipeline. It processes healthy data to create baseline for each setpoint
# Calculating healthy baseline.

HEALTHY_RUNS = {
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

for speed_sp in [50,75,100]:
    save_setpoint_baseline(speed_sp,HEALTHY_RUNS)