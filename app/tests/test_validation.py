import pytest
from app.models.validation.run_validation import validate_measurement
# Testing suite for validation function


def test_invalid_run_id_raises_value_error():
    # We are expecting ValueError
    with pytest.raises(ValueError):
        validate_measurement("invalid_run_id") # Inserting fake "id"


def test_valid_run_returns_two_summaries():
    result = validate_measurement("M2_50_healthy_1_0")

    assert isinstance(result, tuple)
    assert len(result) == 2
    assert "run_status" in result[0]
    assert "run_status" in result[1]


def test_healthy_run_is_within_healthy_envelope():
    electric_summary,vibration_summary = validate_measurement("M2_50_healthy_1_0") # adding healthy run_id

    assert electric_summary["run_status"] == "WITHIN_HEALTHY_ENVELOPE"
    assert vibration_summary["run_status"] == "WITHIN_HEALTHY_ENVELOPE"