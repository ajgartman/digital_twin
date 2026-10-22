import pytest
from app.models.validation.exceptions import MeasurementNotFoundError, InvalidRunIdError
from app.services.validation_service import validate_run_func
# Testing suite for validation function


def test_invalid_run_id_raises_custom_error():
    # We are expecting custom error
    with pytest.raises(InvalidRunIdError): # This can trigger InvalidInputTypeError
        validate_run_func("M2_abc") # Inserting fake "id"

def test_run_not_found_raises_custom_error():
    # We are expecting custom error #2
    with pytest.raises(MeasurementNotFoundError):
        validate_run_func("M2_50_healthy_7_0")


def test_valid_run_returns_two_summaries():
    result = validate_run_func("M2_50_healthy_1_0")

    assert isinstance(result, tuple)
    assert len(result) == 2
    assert "run_status" in result[0]
    assert "run_status" in result[1]


def test_healthy_run_is_within_healthy_envelope():
    electric_summary,vibration_summary = validate_run_func("M2_50_healthy_1_0") # adding healthy run_id

    assert electric_summary["run_status"] == "WITHIN_HEALTHY_ENVELOPE"
    assert vibration_summary["run_status"] == "WITHIN_HEALTHY_ENVELOPE"