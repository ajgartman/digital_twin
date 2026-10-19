# Testing the API endpoints
from fastapi.testclient import TestClient
from app.main import app
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
                    "max_envelope_ratio": 1.0,
                }
        return summary,summary

    monkeypatch.setattr("app.api.routes.validation.validate_measurement", fake_validate_measurement)

    # Running a healthy run, expecting healthy result for both vibration and electric
    response = client.get("/api/measurements/M2_50_healthy_1_0/validation")

    assert response.status_code == 200
    data = response.json()

    assert data["electric_summary"]["run_status"] == "WITHIN_HEALTHY_ENVELOPE"
    assert data["vibration_summary"]["run_status"] == "WITHIN_HEALTHY_ENVELOPE"
    assert data["run_id"] == "M2_50_healthy_1_0"


def test_validation_returns_404_for_value_error(monkeypatch):
    def fake_validate_measurement(run_id):
        raise ValueError("Measurement not found")

    monkeypatch.setattr("app.api.routes.validation.validate_measurement",fake_validate_measurement)

    response = client.get("/api/measurements/invalid_run/validation")

    assert response.status_code == 404
    assert response.json()["detail"] == "Measurement not found"