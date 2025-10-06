from sqlalchemy import Column, Text, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import ForeignKey
from database import Base
import uuid

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipient_id = Column(UUID(as_uuid=True), ForeignKey("person_records.id"), index=True)
    notification_type = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    message = Column(Text, nullable=False)
    data = Column(JSONB)
    read = Column(Boolean, default=False, index=True)
    read_at = Column(DateTime(timezone=True))
    sent_via_sms = Column(Boolean, default=False)
    sent_via_whatsapp = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)