import asyncio

from app.models.classification.classify_run import classify_run
from app.models.performance.process_performance_model import get_healthy_performance_model
from app.models.replay.replay_session import ReplaySession
from app.models.validation.validation_logic import summarize_by_row
from app.repositories.database_access import get_process_data
from app.services.validation_service import validate_run_func

# Replay service will fetch the healthy baseline and then compare window/measurement by measurement with observed run,
# Constantly updating the metrics for vibration and electric readings.
# Module level: shared by functions and classes in this file
active_replays = {}


class ReplayController:
    def __init__(self):
        self.session = None
        self.interval = 2
        self.electric_violation_bool = False
        self.vibration_violation_bool = False
        self.classification_completed_bool = False

    # Initialising the session
    def start_replay(self,run_id,speed,electric_data,vibration_data,process_data,healthy_process_baseline):
        self.session = ReplaySession(run_id,speed,electric_data,vibration_data,process_data,healthy_process_baseline)


    def advance_replay(self):
        offset = 1
        if self.session.electric_index < self.session.electric_total - offset:
            self.session.electric_index += 1
        else:
            self.electric_violation_bool = True
            self.session.electric_index = 0

        if self.session.vibration_index < self.session.vibration_total - offset:
            self.session.vibration_index += 1
        else:
            self.vibration_violation_bool = True
            self.session.vibration_index = 0

    def calculate_violation_rate(self):
        # Task of this function is to calculate feature violation rate.
        total_electric = self.session.electric_total
        total_vibration = self.session.vibration_total
        # Fetching latest result
        latest_result_electric = self.session.latest_results["electric"]
        latest_result_vibration = self.session.latest_results["vibration"]
        if latest_result_electric["violation"] and not self.electric_violation_bool:
            self.session.electric_violation_qty += 1
        if latest_result_vibration["violation"] and not self.vibration_violation_bool:
            self.session.vibration_violation_qty += 1

        self.session.electric_violation_rate = self.session.electric_violation_qty / total_electric * 100
        self.session.vibration_violation_rate = self.session.vibration_violation_qty / total_vibration * 100


    def inject_fault(self,faulty_run_id,
                     faulty_electric_data,
                     faulty_vibration_data,
                     process_data):

        # Caching the healthy_run_data and process data
        self.session.electric_cache_measurements = self.session.electric_measurements
        self.session.vibration_cache_measurements = self.session.vibration_measurements
        self.session.process_cache_data = self.session.process_data

        # Setting the fault id. Session run_id remains the same.
        self.session.fault_id = faulty_run_id
        # Replacing the healthy data with new faulty one.
        self.session.electric_measurements = faulty_electric_data
        self.session.vibration_measurements = faulty_vibration_data
        self.session.process_data = process_data
        # Resetting the index values and faults.
        # Electric data
        self.session.electric_index = 0
        self.session.electric_violation_qty = 0
        self.session.electric_violation_rate = 0
        # Vibration data
        self.session.vibration_index = 0
        self.session.vibration_violation_qty = 0
        self.session.vibration_violation_rate = 0
        # Resetting violation data
        self.vibration_violation_bool = False
        self.electric_violation_bool = False
        # Resetting classification bool
        self.classification_completed_bool = False
        # Resetting the classification data
        self.session.fault_classification_data = None


    def revert_fault(self):

        self.session.electric_measurements = self.session.electric_cache_measurements
        self.session.vibration_measurements = self.session.vibration_cache_measurements
        self.session.process_data = self.session.process_cache_data

        self.session.electric_cache_measurements = None
        self.session.vibration_cache_measurements = None
        self.session.process_cache_data = None
        self.session.fault_id = None

        # Resetting the index values and faults.
        # Electric data
        self.session.electric_index = 0
        self.session.electric_violation_qty = 0
        self.session.electric_violation_rate = 0
        # Vibration data
        self.session.vibration_index = 0
        self.session.vibration_violation_qty = 0
        self.session.vibration_violation_rate = 0

        # booleans
        self.vibration_violation_bool = False
        self.electric_violation_bool = False
        self.classification_completed_bool = False

        # Resetting the classification data
        self.session.fault_classification_data = None


    def fault_classifier(self):
        print("--- FAULT CLASSIFIER TRIGGERRED! ---")
        # Running the classifier function
        # If we have fault injected, we are using fault_id, if not, it defaults to just run_id
        run_id = self.session.fault_id if self.session.fault_id else self.session.run_id
        self.session.fault_classification_data = classify_run(run_id)
        self.classification_completed_bool = True

    # Might add function to summarise it nicely...
    def get_state(self):
        result = {
            "run_id":self.session.run_id,
            "status":self.session.status,
            "electric_index":self.session.electric_index,
            "vibration_index":self.session.vibration_index,
            "speed":self.session.speed,
            "latest_results":self.session.latest_results,
            "process_data":self.session.process_data,
            "violation_data":{"electric_violations": self.session.electric_violation_qty,
                              "electric_violations_rate": self.session.electric_violation_rate,
                              "vibration_violations": self.session.vibration_violation_qty,
                              "vibration_violations_rate": self.session.vibration_violation_rate},
            "healthy_process_baseline":self.session.healthy_process_baseline,
            "fault_classification_data":self.session.fault_classification_data}
        return result


    @property
    def status(self):
        return self.session.get_status


    def pause(self):
        self.session.pause()


    def start(self):
        self.session.start()


    def stop(self):
        self.session.stop()
        self.vibration_violation_bool = False
        self.electric_violation_bool = False
        self.classification_completed_bool = False


    async def run_replay(self):
        while self.session.status in ["running","paused"]:
            if self.session.status != "paused":
                self.advance_replay()
                self.session.latest_results = {"electric":summarize_by_row(self.session.electric_measurements[self.session.electric_index]),
                                               "vibration":summarize_by_row(self.session.vibration_measurements[self.session.vibration_index])}
                # Calculating the violation rates
                if not self.electric_violation_bool or not self.vibration_violation_bool:
                    self.calculate_violation_rate()
                # If both bools are True, this means cycle has been completed, and we can run classification function, should be ONS
                if self.electric_violation_bool and self.vibration_violation_bool and not self.classification_completed_bool:
                    self.fault_classifier()
                print(self.session.latest_results)
                print("Session status: ",self.session.status)
            await asyncio.sleep(self.interval)
        print("Replay function terminated.")


# --- --- --- ---
def get_replay(run_id:str):
    result = active_replays.get(run_id,None)
    if result is None:
        raise ValueError (f"Key does not exist or session has not started! Current controller list: {active_replays} ")
    return result


def register_replay(run_id:str,controller:ReplayController):
    active_replays[run_id] = controller


def remove_replay(run_id:str):
    active_replays.pop(run_id,None)


# 1. Replay function
def start_replay(run_id:str,fault_injection_func = False):
    # Getting the healthy and observed data for given run. Reusing the existing functions, toggling the bit
    electric_output, vibration_output, speed_sp = validate_run_func(run_id,replay_mode=True)
    # Fetching the process data
    process_data = get_process_data(run_id)
    # If we decide to inject a fault, we are going to return those values.
    if fault_injection_func:
        return electric_output,vibration_output,process_data
    # Fetching healthy baseline data
    healthy_process_baseline = get_healthy_performance_model(speed_sp)
    # Creating replay controller class
    replay_controller = ReplayController()
    # Creating replay session
    replay_controller.start_replay(run_id,speed_sp,electric_output,vibration_output,process_data,healthy_process_baseline)
    replay_controller.session.start() # Setting the state to 'running'
    # Registering controller
    register_replay(run_id,replay_controller)

    # Remember to keep the object inside the logic sections, we only expose certain data/attributes!
    return replay_controller #We are returning replay controller... which will be running? Interesting...

if __name__ == "__main__":
    pass