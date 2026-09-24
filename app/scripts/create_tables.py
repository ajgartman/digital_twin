from app.database.connection import engine
from app.database.base import Base
from app.models.measurement_entities.orm_models import ProcessMeasurement,ElectricMeasurement,VibrationMeasurement

Base.metadata.create_all(bind=engine)

print("Tables created!")