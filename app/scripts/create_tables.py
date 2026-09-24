from app.database.connection import engine
from app.database.base import Base
from app.models.measurement_entities.process import ProcessMeasurement

Base.metadata.create_all(bind=engine)

print("Tables created!")