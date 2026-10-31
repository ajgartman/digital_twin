import asyncio

from fastapi import APIRouter, HTTPException, Depends
from app.services.replay_service import ReplayController, get_replay, active_replays, start_replay
from app.services.validation_service import validate_run_func
from app.api.schemas.validation import ValidationResponse
from app.models.validation.exceptions import MeasurementNotFoundError, InvalidRunIdError

router = APIRouter()

# Setting up the dependency. We choose what we want to inject/pass inside the function.
def get_validation_service():
    return validate_run_func

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


# Adding dependency
def get_replay_controller():
    return get_replay


@router.get("/api/replay/{run_id}")
def replay(run_id:str,service = Depends(get_replay_controller)):
    try:
        # Getting the controller object
        result:ReplayController = service(run_id)
        return result.get_state()
    except ValueError as v:
        raise HTTPException(status_code=404, detail=str(v))


@router.post("/api/replay/start/{run_id}")
async def start_replay_endpoint(run_id: str):
    active_run:ReplayController = active_replays.get(run_id,None)
    if active_run:
        # Checking run status
        if active_run.status == "running":
            return {"message":"Run already active!"}
        else:
            # If it is already there and not running.
            return {"message":active_run.get_state()}
    else:
        controller = start_replay(run_id)
        # Scheduling task - important!
        asyncio.create_task(controller.run_replay())
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

@router.post("/api/replay/{run_id}/start")
def start(run_id:str, service = Depends(get_replay_controller)):
    print("Start command request triggerred!")
    try:
        # Getting the controller object
        replay_controller: ReplayController = service(run_id)
        # Calling the pause method
        replay_controller.start()
        return replay_controller.get_state()
    except ValueError as v:
        raise HTTPException(status_code=404, detail=str(v))

@router.post("/api/replay/{run_id}/stop")
def stop(run_id:str, service = Depends(get_replay_controller)):
    print("Stop command triggerred!")
    try:
        # Getting the controller object
        replay_controller: ReplayController = service(run_id)
        # Calling the pause method
        replay_controller.stop()
        return replay_controller.get_state()
    except ValueError as v:
        raise HTTPException(status_code=404, detail=str(v))