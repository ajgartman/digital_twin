#
# speed_sp = [50,75,100]
#
# summary_df = []
# for speed in speed_sp:
#     excluded_runs = [f"M2_{speed}_healthy_1_0",
#                      f"M2_{speed}_healthy_2_0",
#                      f"M2_{speed}_healthy_3_0",
#                      f"M2_{speed}_new_motor_0"]
#     for run in excluded_runs:
#         electric_summary, vibration_summary = validate_measurement(run)
#         # Adding more labels to the dictionary
#         electric_summary["type"] = "electric"
#         electric_summary["speed_sp"] = int(run.split("_")[1])
#         electric_summary["excluded_run"] = run
#         vibration_summary["type"] = "vibration"
#         vibration_summary["speed_sp"] = int(run.split("_")[1])
#         vibration_summary["excluded_run"] = run
#         summary_df.append(electric_summary)
#         summary_df.append(vibration_summary)
#
# df_output = pd.DataFrame(summary_df)
# print(df_output)
# print(df_output.groupby(["speed_sp", "type"])[["range_violation_rate", "variability_violation_rate"]].mean().round(3))



