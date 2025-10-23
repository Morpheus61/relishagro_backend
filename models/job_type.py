from sqlalchemy import Column, Text, Numeric, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from database import Base
import uuid

class DailyJobType(Base):
    __tablename__ = "daily_job_types"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_name = Column(Text, nullable=False, unique=True)  # Add unique to match constraint
    category = Column(Text, nullable=True)  # ✅ Allow NULL (matches your schema)
    unit_of_measurement = Column(Text, nullable=True)
    expected_output_per_worker = Column(Numeric, nullable=True)
    is_active = Column(Boolean, default=True)
    created_by = Column(UUID(as_uuid=True), nullable=True)  # ✅ Allow NULL
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())