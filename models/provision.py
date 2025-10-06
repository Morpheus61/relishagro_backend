from sqlalchemy import Column, Text, DateTime, Numeric, func
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy import ForeignKey
from database import Base
import uuid

class ProvisionRequest(Base):
    __tablename__ = "provision_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_type = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    amount = Column(Numeric)
    vendor = Column(Text)
    requested_date = Column(DateTime(timezone=True))
    receipt_images = Column(ARRAY(Text))
    status = Column(Text, default="pending", index=True)
    requested_by = Column(UUID(as_uuid=True))
    approved_by = Column(UUID(as_uuid=True))
    reviewed_by_fc_manager = Column(UUID(as_uuid=True))
    reviewed_by_fc_manager_at = Column(DateTime(timezone=True))
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("person_records.id"))
    vendor_notified_at = Column(DateTime(timezone=True))
    vendor_response = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())