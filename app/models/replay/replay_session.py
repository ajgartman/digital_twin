# Replay session class

class ReplaySession:
    def __init__(self,run_id:str,speed:float,electric_data:list[dict],vibration_data:list[dict]):

        self.run_id = run_id
        self.status = "idle"

        self.electric_index = 0
        self.vibration_index = 0
        # We know that measurement has specified no. of output rows.
        self.electric_measurements = electric_data
        self.vibration_measurements = vibration_data
        self.electric_total = len(self.electric_measurements)
        self.vibration_total = len(self.vibration_measurements)
        self.speed = speed
        self.latest_results = None

    # Property getter
    @property
    def get_status(self):
        return self.status

    def start(self):
        self.status = "running"
