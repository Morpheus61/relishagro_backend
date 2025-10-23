# models/job_type.py
from sqlalchemy import Column, String, DateTime, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class DailyJobType(Base):
    __tablename__ = 'daily_job_types'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_name = Column(String, nullable=False, unique=True)
    category = Column(String, nullable=True)
    unit_of_measurement = Column(String, nullable=True)
    expected_output_per_worker = Column(Numeric, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey('auth.users.id'), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f"<DailyJobType(id={self.id}, job_name='{self.job_name}', category='{self.category}')>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': str(self.id),
            'job_name': self.job_name,
            'category': self.category,
            'unit_of_measurement': self.unit_of_measurement,
            'expected_output_per_worker': float(self.expected_output_per_worker) if self.expected_output_per_worker else 0,
            'created_by': str(self.created_by) if self.created_by else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }