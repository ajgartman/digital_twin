# Testing the API endpoints
from fastapi.testclient import TestClient
from app.api.routes.validation import get_validation_service
from app.main import app
from app.models.validation.exceptions import MeasurementNotFoundError

client = TestClient(app)


def test_validation_returns_summaries(monkeypatch):
    # Note to future me, mock return HAS to match the pydantic schema structure for the real API endpoint!
    def fake_validate_measurement(run_id):
        summary = {
                    "feature_count": 24,
                    "evaluated_features": 24,
                    "check_failures": {"mean_check": 0, "std_check": 0},
                    "check_unknowns": {"mean_check": 0, "std_check": 0},
                    "features_with_any_violation": 0,
                    "features_with_any_violation_rate": 0.0,
                    "run_status": "WITHIN_HEALTHY_ENVELOPE",
                    "max_envelope_ratio": 1.0,}
        return summary,summary

    monkeypatch.setattr("app.api.routes.validation.validate_run", fake_validate_measurement)

    # Running a healthy run, expecting healthy result for both vibration and electric
    response = client.get("/api/measurements/M2_50_healthy_1_0/validation")

    assert response.status_code == 200
    data = response.json()

    # Checking correct data structure and values - API Contract.
    assert "electric_summary" in data
    assert "vibration_summary" in data

    assert data["electric_summary"]["run_status"] == "WITHIN_HEALTHY_ENVELOPE"
    assert data["vibration_summary"]["run_status"] == "WITHIN_HEALTHY_ENVELOPE"

    assert data["electric_summary"]["feature_count"] == 24
    assert data["vibration_summary"]["feature_count"] == 20

    assert data["run_id"] == "M2_50_healthy_1_0"


def test_validation_returns_404_for_missing_measurement(monkeypatch):
    def fake_validate_measurement(run_id):
        raise MeasurementNotFoundError("Measurement not found")
    monkeypatch.setattr("app.api.routes.validation.validate_run",fake_validate_measurement)

    response = client.get(f"/api/measurements/M2_50_healthy_8_0/validation")

    assert response.status_code == 404
    assert response.json()["detail"] =="No process measurement found for M2_50_healthy_8_0" #Message optional, we care about the code


def test_validation_returns_summaries_dependency_override():

    # Fake function
    def fake_func(run_id):
        fake_summary = {
            "feature_count": 24,
            "evaluated_features": 24,
            "check_failures": {"mean_check": 0, "std_check": 0},
            "check_unknowns": {"mean_check": 0, "std_check": 0},
            "features_with_any_violation": 0,
            "features_with_any_violation_rate": 0.0,
            "run_status": "WITHIN_HEALTHY_ENVELOPE",
            "max_envelope_ratio": 1.0, }
        return fake_summary, fake_summary

    # Override dependency
    def override_dependency():
        return fake_func

    app.dependency_overrides[get_validation_service] = override_dependency
    try:
        response = client.get("/api/measurements/M2_50_healthy_1_0/validation")
        assert response.status_code == 200
        data = response.json()
        assert "electric_summary" in data
        assert "vibration_summary" in data

    finally:
        app.dependency_overrides.clear()


def test_validation_returns_500_error():

    def fake_return_func(run_id):
        raise RuntimeError ("Unexpected Failure")

    def override_dependency(run_id):
        return fake_return_func

    # Overwriting the dependency
    app.dependency_overrides[get_validation_service] = override_dependency
    try:
        response = client.get("/api/measurements/M2_50_healthy_1_0/validation")
        assert response.status_code == 500
    finally:
        app.dependency_overrides.clear()
