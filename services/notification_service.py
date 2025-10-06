from typing import List, Optional
from sqlalchemy.orm import Session
from models import Notification, PersonRecord
from config import settings
import uuid
from datetime import datetime

class NotificationService:
    """
    Multi-channel notification service: In-app, SMS, WhatsApp
    """
    
    def __init__(self):
        self.twilio_client = None
        self._initialize_twilio()
    
    def _initialize_twilio(self):
        """Initialize Twilio client for SMS/WhatsApp"""
        try:
            if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
                from twilio.rest import Client
                self.twilio_client = Client(
                    settings.TWILIO_ACCOUNT_SID,
                    settings.TWILIO_AUTH_TOKEN
                )
                print("✅ Twilio client initialized")
        except Exception as e:
            print(f"⚠️ Twilio initialization failed: {e}")
    
    async def create_notification(
        self,
        db: Session,
        recipient_id: uuid.UUID,
        notification_type: str,
        title: str,
        message: str,
        data: Optional[dict] = None,
        send_sms: bool = False,
        send_whatsapp: bool = False
    ) -> Notification:
        """
        Create in-app notification and optionally send SMS/WhatsApp
        """
        
        # Create in-app notification
        notification = Notification(
            recipient_id=recipient_id,
            notification_type=notification_type,
            title=title,
            message=message,
            data=data
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)
        
        # Get recipient details for SMS/WhatsApp
        recipient = db.query(PersonRecord).filter(
            PersonRecord.id == recipient_id
        ).first()
        
        if not recipient or not recipient.contact_number:
            return notification
        
        # Send SMS if requested
        if send_sms and self.twilio_client:
            try:
                self._send_sms(recipient.contact_number, message)
                notification.sent_via_sms = True
            except Exception as e:
                print(f"❌ SMS send failed: {e}")
        
        # Send WhatsApp if requested
        if send_whatsapp and self.twilio_client:
            try:
                self._send_whatsapp(recipient.contact_number, message)
                notification.sent_via_whatsapp = True
            except Exception as e:
                print(f"❌ WhatsApp send failed: {e}")
        
        db.commit()
        return notification
    
    def _send_sms(self, phone_number: str, message: str):
        """Send SMS via Twilio"""
        if not self.twilio_client:
            return
        
        # Ensure phone number has country code
        if not phone_number.startswith('+'):
            phone_number = f'+91{phone_number}'  # Indian country code
        
        self.twilio_client.messages.create(
            body=message,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=phone_number
        )
    
    def _send_whatsapp(self, phone_number: str, message: str):
        """Send WhatsApp message via Twilio"""
        if not self.twilio_client:
            return
        
        # Ensure phone number has country code
        if not phone_number.startswith('+'):
            phone_number = f'+91{phone_number}'
        
        self.twilio_client.messages.create(
            body=message,
            from_=f'whatsapp:{settings.TWILIO_PHONE_NUMBER}',
            to=f'whatsapp:{phone_number}'
        )
    
    async def notify_onboarding_approval(
        self,
        db: Session,
        manager_id: uuid.UUID,
        worker_name: str
    ):
        """Notify manager that their onboarding request needs approval"""
        await self.create_notification(
            db=db,
            recipient_id=manager_id,
            notification_type="onboarding_approval",
            title="Onboarding Request Submitted",
            message=f"Worker {worker_name} has been submitted for admin approval.",
            send_sms=False,
            send_whatsapp=False
        )
    
    async def notify_provision_request(
        self,
        db: Session,
        recipient_id: uuid.UUID,
        request_type: str,
        amount: float,
        requester_name: str
    ):
        """Notify about provision request"""
        await self.create_notification(
            db=db,
            recipient_id=recipient_id,
            notification_type="provision_request",
            title=f"New {request_type} Request",
            message=f"{requester_name} requested {request_type} for ₹{amount:.2f}",
            send_sms=True,
            send_whatsapp=True
        )
    
    async def notify_geofence_alert(
        self,
        db: Session,
        managers: List[uuid.UUID],
        driver_name: str,
        alert_type: str
    ):
        """Notify managers about geofence alert"""
        for manager_id in managers:
            await self.create_notification(
                db=db,
                recipient_id=manager_id,
                notification_type="geofence_alert",
                title=f"GPS Alert: {alert_type}",
                message=f"Driver {driver_name} - {alert_type}",
                send_sms=True,
                send_whatsapp=False
            )
    
    async def notify_lot_completion(
        self,
        db: Session,
        manager_id: uuid.UUID,
        lot_id: str,
        supervisor_name: str
    ):
        """Notify FlavorCore manager about lot completion"""
        await self.create_notification(
            db=db,
            recipient_id=manager_id,
            notification_type="lot_completion",
            title="Lot Processing Complete",
            message=f"{supervisor_name} completed processing for {lot_id}. Awaiting approval.",
            send_sms=True,
            send_whatsapp=False
        )