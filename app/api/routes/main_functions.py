import asyncio
from fastapi import APIRouter, HTTPException, Depends
from app.services.replay_service import ReplayController, get_replay, active_replays, start_replay, remove_replay
from app.services.validation_service import validate_run_func
from app.api.schemas.validation import ValidationResponse
from app.models.validation.exceptions import MeasurementNotFoundError, InvalidRunIdError

router = APIRouter()

# Setting up the dependency. We choose what we want to inject/pass inside the function.
def get_validation_service():
    return validate_run_func

# Adding dependency 1
def get_replay_controller():
    return get_replay

# Adding dependency 2
def get_remove_controller():
    return remove_replay

@router.get("/api/measurements/{run_id}/validation",response_model=ValidationResponse) # Adding expected response model
def validate_run(run_id: str,service = Depends(get_validation_service)):
    try:
        result = service(run_id)
    except MeasurementNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as r_e:
        raise HTTPException(status_code=500, detail=str(r_e))
    except InvalidRunIdError as i_e:
        raise HTTPException(status_code=422,detail=str(i_e))

    return {
        "run_id": run_id,
        "electric_summary": result[0],
        "vibration_summary": result[1],
        "status": "ok"}


# SCADA GET data endpoint. Important!
@router.get("/api/replay/{run_id}")
def replay(run_id:str,service = Depends(get_replay_controller)):
    try:
        # Getting the controller object
        result:ReplayController = service(run_id)
        return result.get_state()
    except ValueError as v:
        raise HTTPException(status_code=404, detail=str(v))


@router.post("/api/replay/{run_id}/start")
async def start_replay_endpoint(run_id: str):
    existing_run:ReplayController = active_replays.get(run_id,None)
    if existing_run:
        print("Run id already present in the dictionary!")
        # Checking run status
        if existing_run.status == "running":
            return {"message":"Run already active!"}
        else:
            # If it is already there and not running.
            # Setting the state to 'run' and creating new background task.
            existing_run.start()
            asyncio.create_task(existing_run.run_replay())
            return {"message":existing_run.get_state()}
    else:
        controller = start_replay(run_id)
        # Scheduling task - important!
        asyncio.create_task(controller.run_replay())
        print("Current controllers:",active_replays)
        return controller.get_state()


@router.post("/api/replay/{run_id}/pause")
def pause(run_id:str, service = Depends(get_replay_controller)):
    print("Pause command triggerred!")
    try:
        # Getting the controller object
        replay_controller: ReplayController = service(run_id)
        # Calling the pause method
        replay_controller.pause()
        return replay_controller.get_state()
    except ValueError as v:
        raise HTTPException(status_code=404, detail=str(v))

@router.post("/api/replay/{run_id}/resume")
def resume(run_id:str, service = Depends(get_replay_controller)):
    print("Resume command request triggerred!")
    try:
        # Getting the controller object
        replay_controller: ReplayController = service(run_id)
        # Calling the resume method
        replay_controller.start()
        return replay_controller.get_state()
    except ValueError as v:
        raise HTTPException(status_code=404, detail=str(v))

@router.post("/api/replay/{run_id}/stop")
def stop(run_id:str, get_service = Depends(get_replay_controller)):
    print("Stop command triggerred!")
    print(f"Current controllers in dictionary: {active_replays}")
    try:
        # Getting the controller object
        replay_controller: ReplayController = get_service(run_id)
        # Calling the pause method
        replay_controller.stop()
        # Popping the service, not using it for now...
        return replay_controller.get_state()
    except ValueError as v:
        raise HTTPException(status_code=404, detail=str(v))


@router.post("/api/replay/{run_id}/inject-fault/{fault_id}")
def inject_fault(run_id:str,fault_id:str, get_service = Depends(get_replay_controller)):
    try:
        # Getting the controller object
        replay_controller:ReplayController = get_service(run_id)
        # Something needs to happen here...
        # We need to fetch the current controller and replace the data with new, faulty one...
        electric_output, vibration_output, process_data = start_replay(fault_id,True)
        # Calling the function that changes the data inside the replay object
        replay_controller.inject_fault(fault_id,electric_output,vibration_output,process_data)
        return replay_controller.get_state()
    except ValueError as v:
        raise HTTPException(status_code=404,detail=str(v))


@router.post("/api/replay/{run_id}/revert-fault")
def revert_fault(run_id, get_service = Depends(get_replay_controller)):
    try:
        # Getting the controller object
        replay_controller:ReplayController = get_service(run_id)
        replay_controller.revert_fault()
        return replay_controller.get_state()
    except ValueError as v:
        raise HTTPException(status_code=404,detail=str(v))