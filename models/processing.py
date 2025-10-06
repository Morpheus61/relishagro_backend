from sqlalchemy import Column, String, Text, DateTime, Numeric, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from database import Base
import uuid

class FlavorCoreProcessing(Base):
    __tablename__ = "flavorcore_processing"

    process_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lot_id = Column(Text, ForeignKey("lots.lot_id"))
    in_scan_weight = Column(Numeric)
    in_scan_date = Column(DateTime(timezone=True))
    supervisor_id = Column(UUID(as_uuid=True))
    drying_start_time = Column(DateTime(timezone=True))
    drying_end_time = Column(DateTime(timezone=True))
    sample_tests = Column(JSONB)
    final_products = Column(JSONB)
    by_products = Column(JSONB)
    flavorcore_yield_pct = Column(Numeric)
    total_yield_pct = Column(Numeric)
    qr_labels_generated = Column(JSONB)
    processed_date = Column(DateTime(timezone=True))
    handled_by = Column(UUID(as_uuid=True))
    status = Column(Text, default="in_progress", index=True)
    submitted_at = Column(DateTime(timezone=True))
    approved_by = Column(UUID(as_uuid=True))
    approved_at = Column(DateTime(timezone=True))
    
    # Relationships
    qr_labels = relationship("QRLabel", back_populates="process")

class QRLabel(Base):
    __tablename__ = "qr_labels"

    qr_code = Column(Text, primary_key=True)
    process_id = Column(UUID(as_uuid=True), ForeignKey("flavorcore_processing.process_id"))
    product_type = Column(Text, nullable=False)
    net_weight = Column(Numeric, nullable=False)
    traceability_data = Column(JSONB, nullable=False)
    generated_by = Column(UUID(as_uuid=True))
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    process = relationship("FlavorCoreProcessing", back_populates="qr_labels")