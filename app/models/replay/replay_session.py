# Replay session class

class ReplaySession:
    def __init__(self,run_id:str,
                 speed:float,
                 electric_data:list[dict],
                 vibration_data:list[dict],
                 process_data:dict):

        self.run_id = run_id
        self.status = "idle"

        self.electric_index = 0
        self.vibration_index = 0
        # We know that measurement has specified no. of output rows.
        self.electric_measurements = electric_data
        self.vibration_measurements = vibration_data
        self.electric_total = len(self.electric_measurements)
        self.vibration_total = len(self.vibration_measurements)
        self.process_data = process_data
        self.speed = speed
        self.latest_results = None
        self.electric_violation_qty = 0
        self.vibration_violation_qty = 0
        self.electric_violation_rate = 0
        self.vibration_violation_rate = 0

    # Property getter
    @property
    def get_status(self):
        return self.status

    # Nice advice, when you use in-line assignment, after 'else' we just put the variable itself, no = assignment.

    def start(self):
        # Setting the run status to running, no constraints needed... (I hope so)
        self.status = "running"


    def pause(self):
        self.status = "paused" if self.status == "running" else "idle"


    def stop(self):
        self.status = "stopped"

        # Resetting index
        self.electric_index = 0
        self.vibration_index = 0