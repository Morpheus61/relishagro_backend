from sqlalchemy import Column, Text, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from database import Base
import uuid

class RFIDTag(Base):
    __tablename__ = "rfid_tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tag_uid = Column(Text, unique=True, nullable=False, index=True)
    tag_type = Column(Text, nullable=False)
    status = Column(Text, default="available")
    assigned_to_lot = Column(Text)
    assigned_date = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())