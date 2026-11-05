from __future__ import annotations
from sqlalchemy import select
from app.database.connection import SessionLocal
from app.models.database.orm_models import ProcessMeasurement
from app.models.database.orm_models import ElectricMeasurement
from app.models.database.orm_models import VibrationMeasurement

from pathlib import Path
from typing import Any, Iterable, Mapping

import joblib
import pandas as pd

FEATURES = ("mean", "rms", "std", "peak")
SENSOR_MODELS = {"electric": ElectricMeasurement, "vibration": VibrationMeasurement}


class PredictionInputError(ValueError):
    """Raised when feature input does not match the trained model schema."""


def predict_fault(model_path: str | Path, measurements: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Classify a batch of already-extracted channel features.

    Each item must contain ``channel``, ``mean``, ``rms``, ``std`` and ``peak``.
    Multiple windows per channel are averaged, matching training aggregation.
    The returned confidence is the model's maximum class probability and is
    not calibrated; callers should not interpret it as a guaranteed likelihood.
    """
    artifact = joblib.load(model_path)
    if not isinstance(artifact, dict) or not {"pipeline", "feature_columns", "sensor"} <= set(artifact):
        raise PredictionInputError("Model artifact is missing required metadata")
    frame = pd.DataFrame(list(measurements))
    required = {"channel", *FEATURES}
    if frame.empty:
        raise PredictionInputError("At least one measurement row is required")
    if missing := required - set(frame.columns):
        raise PredictionInputError(f"Missing input fields: {sorted(missing)}")
    try:
        frame["channel"] = pd.to_numeric(frame["channel"], errors="raise")
        frame[list(FEATURES)] = frame[list(FEATURES)].apply(pd.to_numeric, errors="raise")
    except (TypeError, ValueError) as exc:
        raise PredictionInputError("Channel and feature values must be numeric") from exc
    if frame[list(FEATURES)].isna().any().any():
        raise PredictionInputError("Feature values cannot be missing")

    per_channel = frame.groupby("channel", sort=True)[list(FEATURES)].mean()
    values: dict[str, float] = {}
    for channel, row in per_channel.iterrows():
        for feature in FEATURES:
            values[f"{feature}_channel_{channel:g}"] = float(row[feature])
    expected = list(artifact["feature_columns"])
    absent = [column for column in expected if column not in values]
    extra = [column for column in values if column not in expected]
    if absent or extra:
        raise PredictionInputError(
            f"Input channels do not match {artifact['sensor']} model; "
            f"missing features={absent}, unexpected features={extra}"
        )
    X = pd.DataFrame([[values[column] for column in expected]], columns=expected)
    model = artifact["pipeline"]
    predicted = str(model.predict(X)[0])
    probabilities = model.predict_proba(X)[0]
    classes = list(model.classes_)
    probability_map = {str(label): float(prob) for label, prob in zip(classes, probabilities)}
    return {
        "predicted_fault": predicted,
        "confidence": probability_map[predicted],
        "confidence_kind": "uncalibrated_model_probability",
        "probabilities": probability_map,
        "model_version": artifact.get("model_version", "unknown"),
        "sensor": artifact["sensor"],
    }


def orm_to_dict(record: Any) -> dict[str, Any]:
    """Convert an SQLAlchemy ORM object into a dictionary."""
    return {column.name: getattr(record, column.name) for column in record.__table__.columns}


def classify_run(run_id: str) -> dict[str, Any]:

    with SessionLocal() as session:
        # 1. Retrieve process measurement using run_id
        statement = select(ProcessMeasurement).where(ProcessMeasurement.run_id == run_id)

        process_row = session.scalar(statement)

        if process_row is None:
            raise ValueError(f"Run {run_id!r} not found.")

        process_id = process_row.id

        results: dict[str, Any] = {
            "run_id": run_id,
            "known_condition_for_comparison_only": str(process_row.condition_desc), "sensor_results": {}}

        # 2. Retrieve measurements for each sensor
        for sensor, model_class in SENSOR_MODELS.items():
            model_path = (Path(__file__).parent / "classifier_models"/ f"{sensor}_fault_classifier.joblib")
            if not model_path.exists():
                results["sensor_results"][sensor] = {
                    "available": False,
                    "reason": f"Model not found: {model_path}"}
                continue

            statement = select(model_class).where(model_class.process_measurement_id == process_id)
            run_rows = session.scalars(statement).all()

            if not run_rows:
                results["sensor_results"][sensor] = {
                    "available": False,
                    "reason": "No measurements for this run."}
                continue

            # 3. Convert ORM objects into dictionaries
            measurements = [orm_to_dict(row) for row in run_rows]

            # 4. Run classifier
            try:
                prediction = predict_fault(model_path, measurements)
            except PredictionInputError as exc:
                results["sensor_results"][sensor] = {"available": False, "reason": str(exc)}
                continue

            results["sensor_results"][sensor] = { "available": True, "measurement_rows_used": len(run_rows),**prediction}

    return results
