from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey
from app.database.base import Base
from app.models.measurement_entities.vibration import VibrationMeasurement
from app.models.measurement_entities.electrical import ElectricMeasurement

class ProcessMeasurement(Base):
    __tablename__ = "process_measurements"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[str] = mapped_column(index=True,unique=True)
    setup: Mapped[str] = mapped_column()
    failure_desc : Mapped[str] = mapped_column()
    severity: Mapped[int] = mapped_column(index=True)
    speed_sp: Mapped[int] = mapped_column(index=True)
    speed_rpm: Mapped[int] = mapped_column()
    pressure: Mapped[float] = mapped_column()
    flow: Mapped[float] = mapped_column()

    vibration_measurements: Mapped[list["VibrationMeasurement"]] = relationship(back_populates="process_measurement",
                                                                                cascade="all, delete-orphan")
    electric_measurements: Mapped[list["ElectricMeasurement"]] = relationship(back_populates="process_measurement",
                                                                                cascade="all, delete-orphan")

    def __repr__(self):
        return (f"Process Measurement(run_id={self.run_id},"
                f" failure_description='{self.failure_description}',"
                f" severity={self.severity})")