from pydantic import BaseModel


class ValidationSummary(BaseModel):
    feature_count: int
    evaluated_features: int
    check_failures: dict[str,int]
    check_unknowns: dict[str,int]
    features_with_any_violation: int
    features_with_any_violation_rate: float
    run_status:str
    max_envelope_ratio:float


class ValidationResponse(BaseModel):
    run_id: str
    electric_summary: ValidationSummary
    vibration_summary: ValidationSummary
    status: str