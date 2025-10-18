from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from models import Notification, PersonRecord
from config import settings
import uuid
from datetime import datetime, date  # ADDED 'date' import here
from database import get_db_connection
import asyncpg

class NotificationService:
    """
    Enhanced Multi-channel notification service: In-app, SMS, WhatsApp
    Now with comprehensive system notifications and supervisor alerts
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
    
    # ============================================================================
    # NEW SYSTEM NOTIFICATION METHODS
    # ============================================================================
    
    async def send_system_notification(
        self,
        title: str,
        message: str,
        notification_type: str = "info",
        target_roles: List[str] = None,
        target_users: List[str] = None,
        action_url: Optional[str] = None,
        send_sms: bool = False,
        send_whatsapp: bool = False
    ):
        """Send system notification to specified users or roles"""
        try:
            conn = await get_db_connection()
            
            # Get target user IDs based on roles
            user_ids = []
            if target_roles:
                role_query = """
                SELECT id FROM person_records 
                WHERE person_type = ANY($1) AND status = 'active'
                """
                role_users = await conn.fetch(role_query, target_roles)
                user_ids.extend([str(row['id']) for row in role_users])
            
            # Add specific target users
            if target_users:
                user_ids.extend(target_users)
            
            # Remove duplicates
            user_ids = list(set(user_ids))
            
            # Create notifications for each user
            for user_id in user_ids:
                query = """
                INSERT INTO notifications (
                    recipient_id, title, message, notification_type, 
                    data, created_at, is_read, is_system
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id
                """
                
                notification_data = {
                    "action_url": action_url,
                    "system_notification": True
                }
                
                notification_id = await conn.fetchval(
                    query,
                    uuid.UUID(user_id),
                    title,
                    message,
                    notification_type,
                    notification_data,
                    datetime.now(),
                    False,
                    True
                )
                
                # Send SMS/WhatsApp if requested
                if send_sms or send_whatsapp:
                    await self._send_external_notifications(
                        conn, user_id, message, send_sms, send_whatsapp
                    )
            
            await conn.close()
            return True
            
        except Exception as e:
            print(f"Error sending system notification: {str(e)}")
            return False
    
    async def _send_external_notifications(self, conn, user_id: str, message: str, send_sms: bool, send_whatsapp: bool):
        """Send SMS/WhatsApp notifications"""
        try:
            # Get user contact details
            user_query = """
            SELECT contact_number FROM person_records WHERE id = $1
            """
            user = await conn.fetchrow(user_query, uuid.UUID(user_id))
            
            if not user or not user['contact_number']:
                return
            
            phone_number = user['contact_number']
            
            # Send SMS
            if send_sms and self.twilio_client:
                self._send_sms(phone_number, message)
            
            # Send WhatsApp
            if send_whatsapp and self.twilio_client:
                self._send_whatsapp(phone_number, message)
                
        except Exception as e:
            print(f"Error sending external notifications: {str(e)}")
    
    # ============================================================================
    # ENHANCED ONBOARDING NOTIFICATIONS
    # ============================================================================
    
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
    
    async def notify_new_onboarding_request(
        self,
        request_id: str,
        request_type: str,
        person_name: str,
        submitted_by: str
    ):
        """Notify admins about new onboarding request - NEW FEATURE"""
        title = f"New {request_type.title()} Onboarding Request"
        message = f"{person_name} has submitted a {request_type} onboarding request. Submitted by: {submitted_by}"
        
        await self.send_system_notification(
            title=title,
            message=message,
            notification_type="info",
            target_roles=["admin", "harvestflow_manager"],
            action_url=f"/onboarding/review/{request_id}",
            send_sms=True,
            send_whatsapp=False
        )
    
    async def notify_onboarding_approved(
        self,
        person_id: str,
        person_name: str,
        staff_id: str,
        approved_by: str
    ):
        """Notify about onboarding approval - NEW FEATURE"""
        title = "Onboarding Approved"
        message = f"{person_name} (Staff ID: {staff_id}) has been approved by {approved_by}"
        
        await self.send_system_notification(
            title=title,
            message=message,
            notification_type="success",
            target_roles=["admin", "harvestflow_manager"],
            action_url=f"/persons/{person_id}",
            send_sms=True,
            send_whatsapp=True
        )
    
    async def notify_supplier_onboarding(
        self,
        request_id: str,
        supplier_name: str,
        firm_name: str
    ):
        """Notify about new supplier/vendor onboarding - NEW FEATURE"""
        title = f"New Supplier Onboarding"
        message = f"{supplier_name} from {firm_name} has submitted supplier onboarding request"
        
        await self.send_system_notification(
            title=title,
            message=message,
            notification_type="info",
            target_roles=["admin", "harvestflow_manager"],
            action_url=f"/onboarding/supplier/{request_id}",
            send_sms=True,
            send_whatsapp=False
        )
    
    # ============================================================================
    # QUALITY TESTING & PRODUCTION NOTIFICATIONS
    # ============================================================================
    
    async def notify_quality_test_completion(
        self,
        lot_id: str,
        crop: str,
        supervisor_name: str,
        quality_score: float = None
    ):
        """Notify about quality test completion - NEW FEATURE"""
        title = f"Quality Test Completed - {crop}"
        score_text = f" with score: {quality_score}" if quality_score else ""
        message = f"Supervisor {supervisor_name} has completed quality testing for lot {lot_id}{score_text}"
        
        await self.send_system_notification(
            title=title,
            message=message,
            notification_type="success",
            target_roles=["admin", "flavorcore_manager"],
            action_url=f"/quality/results/{lot_id}",
            send_sms=True,
            send_whatsapp=False
        )
    
    async def notify_quality_test_required(
        self,
        lot_id: str,
        crop: str,
        supervisor_id: str
    ):
        """Notify supervisor that quality test is required - NEW FEATURE"""
        title = f"Quality Test Required - {crop}"
        message = f"Quality testing is required for lot {lot_id} ({crop})"
        
        await self.send_system_notification(
            title=title,
            message=message,
            notification_type="warning",
            target_users=[supervisor_id],
            action_url=f"/quality/tests/new?lot_id={lot_id}",
            send_sms=True,
            send_whatsapp=False
        )
    
    async def notify_product_submission(
        self,
        lot_id: str,
        quantity_packed: float,
        packaging_type: str,
        supervisor_name: str
    ):
        """Notify about packed product submission - NEW FEATURE"""
        title = f"Products Submitted - Lot {lot_id}"
        message = f"{supervisor_name} submitted {quantity_packed} kg of {packaging_type} for lot {lot_id}"
        
        await self.send_system_notification(
            title=title,
            message=message,
            notification_type="info",
            target_roles=["admin", "flavorcore_manager"],
            action_url=f"/products/submitted/{lot_id}",
            send_sms=True,
            send_whatsapp=False
        )
    
    # ============================================================================
    # ATTENDANCE & WORKER MANAGEMENT NOTIFICATIONS
    # ============================================================================
    
    async def notify_attendance_alert(
        self,
        person_name: str,
        alert_type: str,
        location: str = None
    ):
        """Send attendance-related alerts - NEW FEATURE"""
        location_text = f" at {location}" if location else ""
        title = f"Attendance {alert_type.title()}"
        message = f"{person_name} - {alert_type} attendance alert{location_text}"
        
        await self.send_system_notification(
            title=title,
            message=message,
            notification_type="warning",
            target_roles=["supervisor", "admin"],
            send_sms=True,
            send_whatsapp=False
        )
    
    async def notify_worker_assignment(
        self,
        worker_id: str,
        worker_name: str,
        assigned_jobs: List[str],
        assigned_by: str
    ):
        """Notify worker about new assignment - NEW FEATURE"""
        jobs_text = ", ".join(assigned_jobs) if assigned_jobs else "general duties"
        title = "New Work Assignment"
        message = f"You have been assigned to: {jobs_text} by {assigned_by}"
        
        await self.send_system_notification(
            title=title,
            message=message,
            notification_type="info",
            target_users=[worker_id],
            action_url="/my-assignments",
            send_sms=True,
            send_whatsapp=True
        )
    
    async def notify_rfid_scan(
        self,
        worker_name: str,
        location: str,
        scan_type: str = "check-in"
    ):
        """Notify about RFID scan activity - NEW FEATURE"""
        title = f"RFID {scan_type.title()}"
        message = f"{worker_name} {scan_type} at {location}"
        
        await self.send_system_notification(
            title=title,
            message=message,
            notification_type="info",
            target_roles=["supervisor"],
            send_sms=False,
            send_whatsapp=False
        )
    
    # ============================================================================
    # PRODUCTION & HARVEST NOTIFICATIONS
    # ============================================================================
    
    async def notify_harvest_completion(
        self,
        lot_id: str,
        crop: str,
        total_weight: float,
        workers_count: int
    ):
        """Notify about harvest completion - NEW FEATURE"""
        title = f"Harvest Completed - {crop}"
        message = f"Lot {lot_id}: {total_weight} kg harvested by {workers_count} workers"
        
        await self.send_system_notification(
            title=title,
            message=message,
            notification_type="success",
            target_roles=["supervisor", "admin", "harvestflow_manager"],
            action_url=f"/lots/{lot_id}",
            send_sms=True,
            send_whatsapp=False
        )
    
    async def notify_yield_alert(
        self,
        lot_id: str,
        crop: str,
        expected_yield: float,
        actual_yield: float
    ):
        """Notify about yield variance - NEW FEATURE"""
        variance = ((actual_yield - expected_yield) / expected_yield) * 100
        title = f"Yield Alert - {crop}"
        message = f"Lot {lot_id}: Yield is {variance:+.1f}% ({actual_yield} vs expected {expected_yield})"
        
        notification_type = "warning" if abs(variance) > 10 else "info"
        
        await self.send_system_notification(
            title=title,
            message=message,
            notification_type=notification_type,
            target_roles=["supervisor", "admin"],
            action_url=f"/lots/{lot_id}",
            send_sms=True if abs(variance) > 15 else False,
            send_whatsapp=False
        )
    
    # ============================================================================
    # SYSTEM ALERTS & MAINTENANCE NOTIFICATIONS
    # ============================================================================
    
    async def notify_system_alert(
        self,
        alert_type: str,
        description: str,
        severity: str = "medium"
    ):
        """Send system-wide alerts - NEW FEATURE"""
        severity_colors = {
            "low": "info",
            "medium": "warning", 
            "high": "error",
            "critical": "error"
        }
        
        title = f"System Alert: {alert_type}"
        message = description
        
        await self.send_system_notification(
            title=title,
            message=message,
            notification_type=severity_colors.get(severity, "warning"),
            target_roles=["admin", "harvestflow_manager", "flavorcore_manager"],
            send_sms=severity in ["high", "critical"],
            send_whatsapp=severity == "critical"
        )
    
    async def notify_daily_summary(
        self,
        summary_date: date,  # This was causing the error - now fixed with import
        total_workers: int,
        total_lots: int,
        total_production: float
    ):
        """Send daily summary notification to managers - NEW FEATURE"""
        title = f"Daily Summary - {summary_date}"
        message = f"Workers: {total_workers}, Lots: {total_lots}, Production: {total_production} kg"
        
        await self.send_system_notification(
            title=title,
            message=message,
            notification_type="info",
            target_roles=["admin", "harvestflow_manager", "flavorcore_manager"],
            action_url=f"/reports/daily/{summary_date}",
            send_sms=False,
            send_whatsapp=False
        )
    
    # ============================================================================
    # EXISTING NOTIFICATION METHODS (KEPT FOR BACKWARD COMPATIBILITY)
    # ============================================================================
    
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

# Global instance for easy access
notification_service = NotificationService()