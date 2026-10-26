from fastapi import APIRouter, HTTPException, Depends
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