from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey
from app.database.base import Base


class VibrationMeasurement(Base):
    __tablename__ = "vibration_measurements"

    id: Mapped[int] = mapped_column(primary_key=True)
    process_measurement_id: Mapped[int] = mapped_column(ForeignKey("process_measurements.id"))
    process_measurement: Mapped["ProcessMeasurement"] = relationship(back_populates="vibration_measurements")
    measurement_type: Mapped[str] = mapped_column()
    channel: Mapped[int] = mapped_column()
    measurement_id: Mapped[int] = mapped_column()
    mean: Mapped[float] = mapped_column()
    rms: Mapped[float] = mapped_column()
    std: Mapped[float] = mapped_column()
    peak: Mapped[float] = mapped_column()

    def __repr__(self):
        return (f"Vibration Measurement run_id={self.id},"
                f" Measurement Type='{self.measurement_type}',"
                f" Channel = {self.channel}")


class ElectricMeasurement(Base):
    __tablename__ = "electric_measurements"

    id: Mapped[int] = mapped_column(primary_key=True)
    process_measurement_id: Mapped[int] = mapped_column(ForeignKey("process_measurements.id"))
    process_measurement: Mapped["ProcessMeasurement"] = relationship(back_populates="electric_measurements")
    measurement_type: Mapped[str] = mapped_column()
    channel: Mapped[int] = mapped_column()
    window_id: Mapped[int] = mapped_column()
    measurement_id: Mapped[int] = mapped_column()
    mean: Mapped[float] = mapped_column()
    rms: Mapped[float] = mapped_column()
    std: Mapped[float] = mapped_column()
    peak: Mapped[float] = mapped_column()

    def __repr__(self):
        return (f"Electrical Measurement ID = {self.id},"
                f"Process Measurement ID = {self.process_measurement_id}, "
                f"Measurement Type = {self.measurement_type}, "
                f"Channel = {self.channel}")


class ProcessMeasurement(Base):
    __tablename__ = "process_measurements"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[str] = mapped_column(index=True,unique=True)
    setup: Mapped[str] = mapped_column()
    condition_desc : Mapped[str] = mapped_column()
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
        return (f"Process Measurement run ID(run_id={self.run_id},"
                f" Setup='{self.setup}',"
                f" Severity={self.severity})"
                f" Condition description= = {self.condition_desc}")