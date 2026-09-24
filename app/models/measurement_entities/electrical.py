from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey
from app.database.base import Base
from app.models.measurement_entities.process import ProcessMeasurement

class ElectricMeasurement(Base):
    __tablename__ = "electric_measurements"

    id: Mapped[int] = mapped_column(primary_key=True)
    process_measurement_id: Mapped[int] = mapped_column(ForeignKey("process_measurements.id"))
    process_measurement: Mapped["ProcessMeasurement"] = relationship(back_populates="electric_measurements")
    measurement_type: Mapped[str] = mapped_column()
    condition: Mapped[str] = mapped_column()
    severity: Mapped[int] = mapped_column()
    channel: Mapped[int] = mapped_column()
    window_id: Mapped[int] = mapped_column()
    measurement_id: Mapped[int] = mapped_column()
    device: Mapped[str] = mapped_column()
    speed: Mapped[int] = mapped_column()
    mean: Mapped[float] = mapped_column()
    rms: Mapped[float] = mapped_column()
    std: Mapped[float] = mapped_column()
    peak: Mapped[float] = mapped_column()

    def __repr__(self):
        return (f"Electrical Measurement(run_id={self.run_id},"
                f" condition='{self.condition}',"
                f" severity={self.severity})"
                f" channel = {self.channel}")