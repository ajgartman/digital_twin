from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, UniqueConstraint
from app.database.base import Base


class VibrationMeasurement(Base):
    __tablename__ = "vibration_measurements"

    id: Mapped[int] = mapped_column(primary_key=True)
    process_measurement_id: Mapped[int] = mapped_column(ForeignKey("process_measurements.id"))
    process_measurement: Mapped["ProcessMeasurement"] = relationship(back_populates="vibration_measurements")
    channel: Mapped[int] = mapped_column()
    measurement_id: Mapped[int] = mapped_column()
    mean: Mapped[float] = mapped_column()
    rms: Mapped[float] = mapped_column()
    std: Mapped[float] = mapped_column()
    peak: Mapped[float] = mapped_column()

    def __repr__(self):
        return (f"Vibration Measurement run_id={self.id},"
                f" Measurement ID='{self.measurement_id}',"
                f" Channel = {self.channel}")


class ElectricMeasurement(Base):
    __tablename__ = "electric_measurements"

    id: Mapped[int] = mapped_column(primary_key=True)
    process_measurement_id: Mapped[int] = mapped_column(ForeignKey("process_measurements.id"))
    process_measurement: Mapped["ProcessMeasurement"] = relationship(back_populates="electric_measurements")
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
                f"Measurement ID = {self.measurement_id}, "
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
    healthy_electric_baselines: Mapped[list["HealthyElectricFeatures"]] = relationship(back_populates="process_measurement",
                                                                                       cascade="all, delete-orphan")
    healthy_vibration_baselines: Mapped[list["HealthyVibrationFeatures"]] = relationship(back_populates="process_measurement",
                                                                                         cascade="all, delete-orphan")

    def __repr__(self):
        return (f"Process Measurement run ID(run_id={self.run_id},"
                f" Setup='{self.setup}',"
                f" Severity={self.severity}),"
                f" Condition description= = {self.condition_desc}")


class HealthyElectricFeatures(Base):
    __tablename__ = "healthy_electric_features"

    # Adding unique constraint - process measurement + channel + feature has to be unique!
    __table_args__ = (UniqueConstraint("process_measurement_id",
                                       "channel",
                                       "feature",
                                       name="uq_electric_baseline_run_channel_feature"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    process_measurement_id: Mapped[int] = mapped_column(ForeignKey("process_measurements.id"))
    process_measurement: Mapped["ProcessMeasurement"] = relationship(back_populates="healthy_electric_baselines")
    channel: Mapped[int] = mapped_column()
    feature: Mapped[str] = mapped_column()
    mean: Mapped[float] = mapped_column()
    std: Mapped[float] = mapped_column()
    feature_max: Mapped[float] = mapped_column()
    feature_min: Mapped[float] = mapped_column()


    def __repr__(self):
        return (f"Healthy electric baseline for: Process Measurement run ID(run_id={self.process_measurement_id})"
                f"Run ID: {self.id}")


class HealthyVibrationFeatures(Base):
    __tablename__ = "healthy_vibration_features"

    # Adding unique constraint - process measurement + channel + feature has to be unique!
    __table_args__ = (UniqueConstraint("process_measurement_id",
                                       "channel",
                                       "feature",
                                       name="uq_vibration_baseline_run_channel_feature"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    process_measurement_id: Mapped[int] = mapped_column(ForeignKey("process_measurements.id"))
    process_measurement: Mapped["ProcessMeasurement"] = relationship(back_populates="healthy_vibration_baselines")
    channel: Mapped[int] = mapped_column()
    feature: Mapped[str] = mapped_column()
    mean: Mapped[float] = mapped_column()
    std: Mapped[float] = mapped_column()
    feature_max: Mapped[float] = mapped_column()
    feature_min: Mapped[float] = mapped_column()


    def __repr__(self):
        return (f"Healthy vibration baseline for: Process Measurement run ID(run_id={self.process_measurement_id})"
                f"Run ID: {self.id}")


class HealthySetpointBaseline(Base):
    __tablename__ = "healthy_setpoint_baseline"

    __table_args__ = (
        UniqueConstraint(
            "speed_sp",
            "measurement_type",
            "channel",
            "feature",
            name="uq_healthy_baseline_condition",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    speed_sp: Mapped[int] = mapped_column()
    measurement_type: Mapped[str] = mapped_column()
    channel: Mapped[int] = mapped_column()
    feature: Mapped[str] = mapped_column()
    mean: Mapped[float] = mapped_column()
    std: Mapped[float] = mapped_column()
    feature_min: Mapped[float] = mapped_column()
    feature_max: Mapped[float] = mapped_column()

    def __repr__(self):
        return f"Healthy setpoint baseline: {self.speed_sp} for Measurement Type: {self.measurement_type})"
