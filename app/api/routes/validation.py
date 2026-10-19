from fastapi import APIRouter, HTTPException
from app.models.validation.run_validation import validate_measurement
from app.api.schemas.validation import ValidationResponse

router = APIRouter()

@router.get("/api/measurements/{run_id}/validation",response_model=ValidationResponse) # Adding expected response model
def validate_run(run_id: str):
    try:
        result = validate_measurement(run_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "run_id": run_id,
        "electric_summary": result[0],
        "vibration_summary": result[1],
        "status": "ok"}