from sqlalchemy import Column, String, Text, Date, Numeric, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy import ForeignKey
from database import Base

class Lot(Base):
    __tablename__ = "lots"

    lot_id = Column(Text, primary_key=True)
    crop = Column(Text, nullable=False)
    raw_weight = Column(Numeric)
    half_day_weight = Column(Numeric)
    full_day_weight = Column(Numeric)
    threshed_weight = Column(Numeric)
    estate_yield_pct = Column(Numeric)
    date_harvested = Column(Date, nullable=False, index=True)
    workers_involved = Column(ARRAY(UUID(as_uuid=True)))
    created_by = Column(UUID(as_uuid=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())