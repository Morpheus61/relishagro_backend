from sqlalchemy import Column, String, Text, Integer, DateTime, Numeric, Boolean, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from database import Base
import uuid

class Dispatch(Base):
    __tablename__ = "dispatches"

    dispatch_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lot_id = Column(Text, ForeignKey("lots.lot_id"))
    vehicle_number = Column(Text, nullable=False)
    driver_id = Column(UUID(as_uuid=True), ForeignKey("person_records.id"))
    driver_name = Column(Text)
    driver_mobile = Column(Text)
    sack_count = Column(Integer, nullable=False)
    rfid_tags = Column(JSONB)
    photo_url = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    dispatch_date = Column(DateTime(timezone=True), server_default=func.now())
    trip_status = Column(Text, default="pending", index=True)
    gps_tracking_active = Column(Boolean, default=False)
    created_by = Column(UUID(as_uuid=True))
    
    # Relationships
    driver = relationship("PersonRecord", back_populates="dispatches_as_driver", foreign_keys=[driver_id])
    gps_logs = relationship("GPSTrackingLog", back_populates="dispatch")
    geofence_alerts = relationship("GeofenceAlert", back_populates="dispatch")

class GPSTrackingLog(Base):
    __tablename__ = "gps_tracking_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dispatch_id = Column(UUID(as_uuid=True), ForeignKey("dispatches.dispatch_id"), index=True)
    latitude = Column(Numeric, nullable=False)
    longitude = Column(Numeric, nullable=False)
    speed = Column(Numeric)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    is_offline_queued = Column(Boolean, default=False)
    synced_at = Column(DateTime(timezone=True))
    
    # Relationships
    dispatch = relationship("Dispatch", back_populates="gps_logs")

class GeofenceAlert(Base):
    __tablename__ = "geofence_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dispatch_id = Column(UUID(as_uuid=True), ForeignKey("dispatches.dispatch_id"), index=True)
    alert_type = Column(Text, nullable=False)
    latitude = Column(Numeric)
    longitude = Column(Numeric)
    message = Column(Text)
    acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(UUID(as_uuid=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    dispatch = relationship("Dispatch", back_populates="geofence_alerts")