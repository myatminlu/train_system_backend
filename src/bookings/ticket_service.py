from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from decimal import Decimal
import uuid
import hashlib
import secrets
import json
import base64
import qrcode
from qrcode import constants
from io import BytesIO
from PIL import Image
import os

from src.bookings.schemas import (
    BookingReservation, DigitalTicket, TicketSecurityInfo, TicketStatus,
    TicketValidationRequest, TicketValidationResponse, PassengerInfo,
    QRCodeGeneration, PDFTicketGeneration
)

class TicketService:
    """Service for generating and managing digital tickets with QR codes"""
    
    def __init__(self, db: Session):
        self.db = db
        self._ticket_storage = {}  # In-memory storage (would use database)
        self._validation_logs = []
        self._encryption_key = secrets.token_hex(32)  # Would be from secure config
        
        # Ensure QR code directory exists
        self.qr_code_dir = "static/qr_codes"
        os.makedirs(self.qr_code_dir, exist_ok=True)
    
    def generate_tickets(self, booking: BookingReservation) -> List[DigitalTicket]:
        """Generate digital tickets for all passengers in a booking"""
        
        tickets = []
        
        for passenger in booking.passengers:
            ticket = self._generate_single_ticket(booking, passenger)
            tickets.append(ticket)
            self._ticket_storage[ticket.ticket_id] = ticket
        
        return tickets
    
    def get_ticket(self, ticket_id: str) -> Optional[DigitalTicket]:
        """Get ticket by ID"""
        return self._ticket_storage.get(ticket_id)
    
    def get_booking_tickets(self, booking_id: str) -> List[DigitalTicket]:
        """Get all tickets for a booking"""
        return [t for t in self._ticket_storage.values() if t.booking_id == booking_id]
    
    def validate_ticket(self, request: TicketValidationRequest) -> TicketValidationResponse:
        """Validate a ticket using QR code data"""
        
        ticket = self.get_ticket(request.ticket_id)
        
        if not ticket:
            return TicketValidationResponse(
                ticket_id=request.ticket_id,
                is_valid=False,
                validation_status="not_found",
                validation_message="Ticket not found",
                validation_timestamp=request.validation_timestamp,
                allow_entry=False
            )
        
        # Check if QR code data matches
        if ticket.qr_code_data != request.qr_code_data:
            return TicketValidationResponse(
                ticket_id=request.ticket_id,
                is_valid=False,
                validation_status="tampered",
                validation_message="Ticket data has been tampered with",
                validation_timestamp=request.validation_timestamp,
                allow_entry=False
            )
        
        # Check ticket status
        if ticket.ticket_status == TicketStatus.USED:
            return TicketValidationResponse(
                ticket_id=request.ticket_id,
                is_valid=False,
                validation_status="already_used",
                passenger_name=f"{ticket.passenger_info.first_name} {ticket.passenger_info.last_name}",
                validation_message=f"Ticket already used on {ticket.used_at.strftime('%Y-%m-%d %H:%M')}",
                validation_timestamp=request.validation_timestamp,
                allow_entry=False
            )
        
        if ticket.ticket_status in [TicketStatus.EXPIRED, TicketStatus.CANCELLED, TicketStatus.REFUNDED]:
            return TicketValidationResponse(
                ticket_id=request.ticket_id,
                is_valid=False,
                validation_status=ticket.ticket_status.value,
                validation_message=f"Ticket is {ticket.ticket_status.value}",
                validation_timestamp=request.validation_timestamp,
                allow_entry=False
            )
        
        # Check if ticket is within valid time window
        current_time = request.validation_timestamp
        if current_time < ticket.valid_from or current_time > ticket.valid_until:
            return TicketValidationResponse(
                ticket_id=request.ticket_id,
                is_valid=False,
                validation_status="expired",
                valid_from=ticket.valid_from,
                valid_until=ticket.valid_until,
                validation_message=f"Ticket valid from {ticket.valid_from.strftime('%Y-%m-%d %H:%M')} to {ticket.valid_until.strftime('%Y-%m-%d %H:%M')}",
                validation_timestamp=request.validation_timestamp,
                allow_entry=False
            )
        
        # Check if validation is at correct station
        journey_station_ids = [seg.from_station_id for seg in ticket.journey.segments] + [ticket.journey.segments[-1].to_station_id]
        if request.validation_station_id not in journey_station_ids:
            return TicketValidationResponse(
                ticket_id=request.ticket_id,
                is_valid=False,
                validation_status="invalid",
                validation_message="Ticket not valid for this station",
                validation_timestamp=request.validation_timestamp,
                allow_entry=False
            )
        
        # Ticket is valid - mark as used
        ticket.ticket_status = TicketStatus.USED
        ticket.used_at = current_time
        ticket.validated_at = current_time
        
        # Log validation
        self._log_validation(request, ticket, success=True)
        
        passenger_name = f"{ticket.passenger_info.first_name or ''} {ticket.passenger_info.last_name or ''}".strip()
        journey_info = f"{ticket.journey.segments[0].from_station_name} → {ticket.journey.segments[-1].to_station_name}"
        
        return TicketValidationResponse(
            ticket_id=request.ticket_id,
            is_valid=True,
            validation_status="valid",
            passenger_name=passenger_name,
            journey_info=journey_info,
            valid_from=ticket.valid_from,
            valid_until=ticket.valid_until,
            validation_message="Ticket validated successfully",
            validation_timestamp=request.validation_timestamp,
            allow_entry=True
        )
    
    def cancel_tickets(self, booking_id: str) -> int:
        """Cancel all tickets for a booking"""
        
        tickets = self.get_booking_tickets(booking_id)
        cancelled_count = 0
        
        for ticket in tickets:
            if ticket.ticket_status == TicketStatus.ACTIVE:
                ticket.ticket_status = TicketStatus.CANCELLED
                cancelled_count += 1
        
        return cancelled_count
    
    def generate_qr_code_image(
        self, 
        ticket: DigitalTicket,
        generation_request: Optional[QRCodeGeneration] = None
    ) -> str:
        """Generate QR code image file and return file path"""
        
        if generation_request:
            qr_data = generation_request.data_payload
            qr_size = generation_request.qr_size
            border = generation_request.border_size
            error_correction = getattr(constants, f"ERROR_CORRECT_{generation_request.error_correction}")
        else:
            qr_data = ticket.qr_code_data
            qr_size = 300
            border = 4
            error_correction = constants.ERROR_CORRECT_M
        
        # Create QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=error_correction,
            box_size=10,
            border=border,
        )
        
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        # Create QR code image
        qr_image = qr.make_image(fill_color="black", back_color="white")
        
        # Resize image
        qr_image = qr_image.resize((qr_size, qr_size), Image.LANCZOS)
        
        # Save image
        filename = f"ticket_{ticket.ticket_id}_qr.png"
        file_path = os.path.join(self.qr_code_dir, filename)
        qr_image.save(file_path)
        
        return file_path
    
    def generate_pdf_ticket(
        self, 
        booking_id: str,
        generation_request: Optional[PDFTicketGeneration] = None
    ) -> str:
        """Generate PDF ticket document"""
        
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        
        tickets = self.get_booking_tickets(booking_id)
        if not tickets:
            raise ValueError("No tickets found for booking")
        
        # PDF file setup
        filename = f"tickets_{booking_id}.pdf"
        file_path = os.path.join("static/pdf_tickets", filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        doc = SimpleDocTemplate(file_path, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title = Paragraph("Bangkok Train Transport System", styles['Title'])
        story.append(title)
        story.append(Spacer(1, 20))
        
        for i, ticket in enumerate(tickets):
            if i > 0:
                story.append(Spacer(1, 30))  # Space between tickets
            
            # Ticket header
            ticket_title = Paragraph(f"Digital Ticket #{ticket.ticket_id[:8].upper()}", styles['Heading2'])
            story.append(ticket_title)
            story.append(Spacer(1, 10))
            
            # Passenger info
            passenger_name = f"{ticket.passenger_info.first_name or ''} {ticket.passenger_info.last_name or ''}".strip()
            passenger_info = [
                ["Passenger:", passenger_name],
                ["Type:", ticket.passenger_info.passenger_type_name],
                ["Ticket Status:", ticket.ticket_status.value.title()]
            ]
            
            passenger_table = Table(passenger_info, colWidths=[100, 200])
            passenger_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            
            story.append(passenger_table)
            story.append(Spacer(1, 10))
            
            # Journey info
            journey = ticket.journey
            journey_info = [
                ["From:", journey.segments[0].from_station_name],
                ["To:", journey.segments[-1].to_station_name],
                ["Departure:", journey.departure_time.strftime("%Y-%m-%d %H:%M")],
                ["Arrival:", journey.arrival_time.strftime("%Y-%m-%d %H:%M")],
                ["Duration:", f"{journey.total_duration_minutes} minutes"],
                ["Total Cost:", f"฿{journey.total_cost}"]
            ]
            
            journey_table = Table(journey_info, colWidths=[100, 200])
            journey_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.lightblue),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            
            story.append(journey_table)
            story.append(Spacer(1, 10))
            
            # Route segments
            if generation_request and generation_request.template_style == "detailed":
                route_data = [["Order", "From", "To", "Line", "Time"]]
                for segment in journey.segments:
                    if segment.transport_type == "train":
                        route_data.append([
                            str(segment.segment_order),
                            segment.from_station_name,
                            segment.to_station_name,
                            segment.line_name,
                            segment.departure_time.strftime("%H:%M")
                        ])
                
                route_table = Table(route_data, colWidths=[40, 120, 120, 80, 60])
                route_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                story.append(route_table)
                story.append(Spacer(1, 15))
            
            # QR Code (would include QR code image if generation_request.include_qr_codes)
            if generation_request and generation_request.include_qr_codes:
                qr_text = Paragraph(f"QR Code: {ticket.qr_code_data[:20]}...", styles['Normal'])
                story.append(qr_text)
                story.append(Spacer(1, 10))
            
            # Validity info
            validity_info = Paragraph(
                f"Valid from {ticket.valid_from.strftime('%Y-%m-%d %H:%M')} "
                f"to {ticket.valid_until.strftime('%Y-%m-%d %H:%M')}",
                styles['Italic']
            )
            story.append(validity_info)
        
        # Build PDF
        doc.build(story)
        return file_path
    
    def _generate_single_ticket(
        self, 
        booking: BookingReservation, 
        passenger: PassengerInfo
    ) -> DigitalTicket:
        """Generate a single digital ticket"""
        
        ticket_id = str(uuid.uuid4())
        
        # Generate security info
        security_info = self._generate_security_info(ticket_id, booking)
        
        # Generate QR code data
        qr_data = self._generate_qr_code_data(ticket_id, booking, passenger, security_info)
        
        # Set validity period
        valid_from = booking.journey.departure_time - timedelta(hours=2)  # Can validate 2 hours early
        valid_until = booking.journey.arrival_time + timedelta(hours=1)   # Valid 1 hour after arrival
        
        # Create ticket
        ticket = DigitalTicket(
            ticket_id=ticket_id,
            booking_id=booking.booking_id,
            passenger_info=passenger,
            journey=booking.journey,
            ticket_status=TicketStatus.ACTIVE,
            qr_code_data=qr_data,
            security_info=security_info,
            issued_at=datetime.now(),
            valid_from=valid_from,
            valid_until=valid_until,
            usage_restrictions={
                "single_use": True,
                "transferable": False,
                "valid_stations": [seg.from_station_id for seg in booking.journey.segments] + [booking.journey.segments[-1].to_station_id]
            },
            is_transferable=False
        )
        
        # Generate QR code image
        qr_image_path = self.generate_qr_code_image(ticket)
        ticket.qr_code_image_url = f"/static/qr_codes/{os.path.basename(qr_image_path)}"
        
        return ticket
    
    def _generate_security_info(
        self, 
        ticket_id: str, 
        booking: BookingReservation
    ) -> TicketSecurityInfo:
        """Generate security information for ticket"""
        
        # Create hash of ticket data
        hash_input = f"{ticket_id}{booking.booking_id}{booking.journey.journey_id}{datetime.now().isoformat()}"
        ticket_hash = hashlib.sha256(hash_input.encode()).hexdigest()
        
        # Generate validation code
        validation_code = secrets.token_hex(8).upper()
        
        return TicketSecurityInfo(
            ticket_hash=ticket_hash,
            validation_code=validation_code,
            encryption_key=self._encryption_key[:16],  # Use first 16 chars as key
            issued_timestamp=datetime.now(),
            expires_at=booking.journey.arrival_time + timedelta(hours=24)
        )
    
    def _generate_qr_code_data(
        self, 
        ticket_id: str,
        booking: BookingReservation,
        passenger: PassengerInfo,
        security_info: TicketSecurityInfo
    ) -> str:
        """Generate QR code data payload"""
        
        # Create data structure
        qr_data = {
            "v": "1.0",  # Version
            "tid": ticket_id[:8],  # Short ticket ID
            "bid": booking.booking_id[:8],  # Short booking ID
            "ref": booking.booking_reference,
            "pax": {
                "name": f"{passenger.first_name} {passenger.last_name}".strip(),
                "type": passenger.passenger_type_name
            },
            "journey": {
                "from": booking.journey.from_station_id,
                "to": booking.journey.to_station_id,
                "dep": booking.journey.departure_time.isoformat(),
                "arr": booking.journey.arrival_time.isoformat()
            },
            "security": {
                "hash": security_info.ticket_hash[:16],  # Truncated hash
                "code": security_info.validation_code
            },
            "issued": security_info.issued_timestamp.isoformat(),
            "expires": security_info.expires_at.isoformat()
        }
        
        # Convert to JSON and encode
        json_data = json.dumps(qr_data, separators=(',', ':'))
        encoded_data = base64.b64encode(json_data.encode()).decode()
        
        return encoded_data
    
    def _log_validation(
        self, 
        request: TicketValidationRequest,
        ticket: DigitalTicket,
        success: bool
    ):
        """Log ticket validation attempt"""
        
        log_entry = {
            "timestamp": request.validation_timestamp.isoformat(),
            "ticket_id": request.ticket_id,
            "station_id": request.validation_station_id,
            "validator_id": request.validator_id,
            "success": success,
            "passenger": f"{ticket.passenger_info.first_name} {ticket.passenger_info.last_name}".strip(),
            "booking_ref": ticket.booking_id[:8]
        }
        
        self._validation_logs.append(log_entry)
        
        # Keep only recent logs (last 1000)
        if len(self._validation_logs) > 1000:
            self._validation_logs = self._validation_logs[-1000:]
    
    def get_validation_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent validation logs"""
        return self._validation_logs[-limit:]
    
    def get_ticket_statistics(self) -> Dict[str, Any]:
        """Get ticket usage statistics"""
        
        all_tickets = list(self._ticket_storage.values())
        total_tickets = len(all_tickets)
        
        status_counts = {}
        for status in TicketStatus:
            status_counts[status.value] = len([t for t in all_tickets if t.ticket_status == status])
        
        return {
            "total_tickets": total_tickets,
            "status_breakdown": status_counts,
            "total_validations": len(self._validation_logs),
            "recent_validations": len([log for log in self._validation_logs 
                                    if datetime.fromisoformat(log["timestamp"]) > datetime.now() - timedelta(hours=24)])
        }