from datetime import datetime
from typing import ClassVar

from sqlalchemy import DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from . import Base


class Feedback(Base):
    __tablename__ = "feedback"
    __table_args__: ClassVar = {"schema": "config"}

    id_feedback: Mapped[int] = mapped_column(primary_key=True)
    report_type: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    contact: Mapped[str] = mapped_column(nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
