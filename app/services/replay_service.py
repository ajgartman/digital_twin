import asyncio

from app.models.replay.replay_session import ReplaySession
from app.services.validation_service import validate_run_func

# Replay service will fetch the healthy baseline and then compare window/measurement by measurement with observed run,
# Constantly updating the metrics for vibration and electric readings.
# Module level: shared by functions and classes in this file
active_replays = {}


class ReplayController:
    def __init__(self):
        self.session = None
        self.interval = 2

    # Initialising the session
    def start_replay(self,run_id,speed,electric_data,vibration_data):
        self.session = ReplaySession(run_id,speed,electric_data,vibration_data)


    def advance_replay(self):
        offset = 1
        if self.session.electric_index < self.session.electric_total - offset:
            self.session.electric_index += 1
        else:
            self.session.electric_index = 0

        if self.session.vibration_index < self.session.vibration_total - offset:
            self.session.vibration_index += 1
        else:
            self.session.vibration_index = 0

    # Might add function to summarise it nicely...
    def get_state(self):
        result = {
            "run_id":self.session.run_id,
            "status":self.session.status,
            "electric_index":self.session.electric_index,
            "vibration_index":self.session.vibration_index,
            "speed":self.session.speed,
            "latest_results":self.session.latest_results}
        return result


    async def run_replay(self):
        while self.session.status == "running":
            self.session.latest_results = {"electric":self.session.electric_measurements[self.session.electric_index],
                                           "vibration":self.session.vibration_measurements[self.session.vibration_index]}

            print(self.session.latest_results)
            self.advance_replay()
            if self.session.status == "completed":
                break
            await asyncio.sleep(self.interval)


    def stop_replay(self):
        self.session.status = "completed"

    @property
    def status(self):
        return self.session.get_status


def get_replay(run_id:str):
    result = active_replays.get(run_id,None)
    if result is None:
        raise ValueError ("Key does not exist or session has not started!")
    return result


def register_replay(run_id:str,controller:ReplayController):
    active_replays[run_id] = controller


# 1. Replay function
def start_replay(run_id:str):

    # Getting the healthy and observed data for given run. Reusing the existing functions, toggling the bit
    electric_output, vibration_output, speed_sp = validate_run_func(run_id,replay_mode=True)

    # Creating replay controller class
    replay_controller = ReplayController()
    # Creating replay session
    replay_controller.start_replay(run_id,speed_sp,electric_output,vibration_output)
    replay_controller.session.start() # Setting the state to 'running'
    # Registering controller
    register_replay(run_id,replay_controller)

    # Remember to keep the object inside the logic sections, we only expose certain data/attributes!
    return replay_controller #We are returning replay controller... which will be running? Interesting...



if __name__ == "__main__":
    pass