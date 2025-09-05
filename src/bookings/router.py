from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, date

from src.database import get_db
from src.bookings.schemas import (
    BookingReservationRequest, BookingReservation, BookingConfirmation,
    BookingModificationRequest, BookingCancellationRequest, BookingStatus,
    PaymentStatus, PaymentMethod, PaymentConfirmationRequest, BookingSearchFilters, BookingAnalytics,
    DigitalTicket, TicketValidationRequest, TicketValidationResponse,
    PDFTicketGeneration, QRCodeGeneration, RefundRequest
)
from src.bookings.booking_service import BookingService
from src.bookings.ticket_service import TicketService
from src.bookings.journey_service import JourneyPlanningService

router = APIRouter()

# Journey Planning Endpoints
@router.post("/plan-journey")
def plan_journey_for_booking(
    from_station_id: int = Query(..., description="Origin station ID"),
    to_station_id: int = Query(..., description="Destination station ID"),
    departure_time: datetime = Query(..., description="Preferred departure time"),
    passenger_count: int = Query(1, ge=1, le=10, description="Number of passengers"),
    optimization: str = Query("time", description="Route optimization preference"),
    max_transfers: int = Query(3, ge=0, le=5, description="Maximum transfers allowed"),
    db: Session = Depends(get_db)
):
    """Plan a journey for booking purposes"""
    
    journey_service = JourneyPlanningService(db)
    
    try:
        journey = journey_service.plan_journey(
            from_station_id=from_station_id,
            to_station_id=to_station_id,
            departure_time=departure_time,
            passenger_count=passenger_count,
            optimization=optimization,
            max_transfers=max_transfers
        )
        
        if not journey:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No route found between the specified stations"
            )
        
        return journey
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to plan journey: {str(e)}"
        )

@router.get("/journey/{journey_id}")
def get_journey_details(
    journey_id: str,
    db: Session = Depends(get_db)
):
    """Get journey details by ID"""
    
    journey_service = JourneyPlanningService(db)
    journey = journey_service.get_journey_by_id(journey_id)
    
    if not journey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journey not found or expired"
        )
    
    return journey

@router.get("/journey/{journey_id}/alternatives")
def get_journey_alternatives(
    journey_id: str,
    max_alternatives: int = Query(3, ge=1, le=5, description="Maximum alternatives"),
    db: Session = Depends(get_db)
):
    """Get alternative journey options"""
    
    journey_service = JourneyPlanningService(db)
    alternatives = journey_service.get_alternative_journeys(journey_id, max_alternatives)
    
    return {
        "original_journey_id": journey_id,
        "alternatives": alternatives,
        "total_alternatives": len(alternatives)
    }

# Booking Management Endpoints
@router.post("/reserve", response_model=BookingReservation)
def create_booking_reservation(
    request: BookingReservationRequest,
    db: Session = Depends(get_db)
):
    """Create a new booking reservation"""
    
    booking_service = BookingService(db)
    
    try:
        reservation = booking_service.create_reservation(request)
        return reservation
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create reservation: {str(e)}"
        )

@router.post("/{booking_id}/confirm", response_model=BookingConfirmation)
def confirm_booking(
    booking_id: str,
    payment_request: PaymentConfirmationRequest,
    db: Session = Depends(get_db)
):
    """Confirm a booking with payment"""
    
    booking_service = BookingService(db)
    
    # Create payment method
    payment_method = PaymentMethod(
        method_type=payment_request.payment_method_type,
        method_details=payment_request.payment_details
    )
    
    try:
        confirmation = booking_service.confirm_booking(booking_id, payment_method)
        return confirmation
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to confirm booking: {str(e)}"
        )

@router.get("/{booking_id}", response_model=BookingReservation)
def get_booking(
    booking_id: str,
    db: Session = Depends(get_db)
):
    """Get booking details by ID"""
    
    booking_service = BookingService(db)
    booking = booking_service.get_booking(booking_id)
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    return booking

@router.get("/reference/{booking_reference}", response_model=BookingReservation)
def get_booking_by_reference(
    booking_reference: str,
    db: Session = Depends(get_db)
):
    """Get booking by reference number"""
    
    booking_service = BookingService(db)
    booking = booking_service.get_booking_by_reference(booking_reference)
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    return booking

@router.get("/user/{user_id}", response_model=List[BookingReservation])
def get_user_bookings(
    user_id: int,
    booking_status: Optional[BookingStatus] = Query(None, description="Filter by booking status"),
    payment_status: Optional[PaymentStatus] = Query(None, description="Filter by payment status"),
    date_from: Optional[date] = Query(None, description="Filter from date"),
    date_to: Optional[date] = Query(None, description="Filter to date"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    db: Session = Depends(get_db)
):
    """Get all bookings for a user"""
    
    booking_service = BookingService(db)
    
    # Create filters
    filters = BookingSearchFilters(
        user_id=user_id,
        booking_status=booking_status,
        payment_status=payment_status,
        date_from=date_from,
        date_to=date_to
    )
    
    bookings = booking_service.get_user_bookings(user_id, filters)
    return bookings[:limit]

@router.put("/{booking_id}", response_model=BookingReservation)
def modify_booking(
    booking_id: str,
    modification: BookingModificationRequest,
    db: Session = Depends(get_db)
):
    """Modify an existing booking"""
    
    booking_service = BookingService(db)
    
    try:
        modified_booking = booking_service.modify_booking(booking_id, modification)
        return modified_booking
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to modify booking: {str(e)}"
        )

@router.delete("/{booking_id}")
def cancel_booking(
    booking_id: str,
    cancellation: BookingCancellationRequest,
    db: Session = Depends(get_db)
):
    """Cancel a booking"""
    
    booking_service = BookingService(db)
    
    try:
        refund_request = booking_service.cancel_booking(booking_id, cancellation)
        
        return {
            "message": "Booking cancelled successfully",
            "booking_id": booking_id,
            "refund_request": refund_request
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel booking: {str(e)}"
        )

# Ticket Management Endpoints
@router.get("/{booking_id}/tickets", response_model=List[DigitalTicket])
def get_booking_tickets(
    booking_id: str,
    db: Session = Depends(get_db)
):
    """Get all tickets for a booking"""
    
    ticket_service = TicketService(db)
    tickets = ticket_service.get_booking_tickets(booking_id)
    
    if not tickets:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No tickets found for booking"
        )
    
    return tickets

@router.get("/{booking_id}/ticket/{ticket_id}", response_model=DigitalTicket)
def get_ticket(
    booking_id: str,
    ticket_id: str,
    db: Session = Depends(get_db)
):
    """Get specific ticket details"""
    
    ticket_service = TicketService(db)
    ticket = ticket_service.get_ticket(ticket_id)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    if ticket.booking_id != booking_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ticket does not belong to this booking"
        )
    
    return ticket

@router.get("/{booking_id}/ticket/{ticket_id}/qr")
def get_ticket_qr_code(
    booking_id: str,
    ticket_id: str,
    size: int = Query(300, ge=100, le=1000, description="QR code size in pixels"),
    db: Session = Depends(get_db)
):
    """Get QR code image for ticket"""
    
    ticket_service = TicketService(db)
    ticket = ticket_service.get_ticket(ticket_id)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    if ticket.booking_id != booking_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ticket does not belong to this booking"
        )
    
    # Generate QR code if needed
    if not ticket.qr_code_image_url:
        qr_generation = QRCodeGeneration(
            ticket_id=ticket_id,
            data_payload=ticket.qr_code_data,
            qr_size=size
        )
        qr_image_path = ticket_service.generate_qr_code_image(ticket, qr_generation)
        ticket.qr_code_image_url = f"/static/qr_codes/{os.path.basename(qr_image_path)}"
    
    # Return QR code file
    import os
    qr_file_path = ticket.qr_code_image_url.replace("/static/", "static/")
    
    if not os.path.exists(qr_file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="QR code image not found"
        )
    
    return FileResponse(
        qr_file_path,
        media_type="image/png",
        filename=f"ticket_{ticket_id}_qr.png"
    )

@router.get("/{booking_id}/pdf")
def generate_pdf_tickets(
    booking_id: str,
    template_style: str = Query("standard", description="PDF template style"),
    include_qr_codes: bool = Query(True, description="Include QR codes in PDF"),
    include_journey_map: bool = Query(False, description="Include journey map"),
    language: str = Query("en", description="Language (en/th)"),
    db: Session = Depends(get_db)
):
    """Generate PDF tickets for booking"""
    
    ticket_service = TicketService(db)
    
    # Validate booking exists
    booking_service = BookingService(db)
    booking = booking_service.get_booking(booking_id)
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    try:
        pdf_request = PDFTicketGeneration(
            booking_id=booking_id,
            include_qr_codes=include_qr_codes,
            include_journey_map=include_journey_map,
            template_style=template_style,
            language=language
        )
        
        pdf_path = ticket_service.generate_pdf_ticket(booking_id, pdf_request)
        
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=f"tickets_{booking_id}.pdf"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF: {str(e)}"
        )

# Ticket Validation Endpoints
@router.post("/tickets/validate", response_model=TicketValidationResponse)
def validate_ticket(
    validation_request: TicketValidationRequest,
    db: Session = Depends(get_db)
):
    """Validate a ticket using QR code data"""
    
    ticket_service = TicketService(db)
    
    try:
        validation_response = ticket_service.validate_ticket(validation_request)
        return validation_response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate ticket: {str(e)}"
        )

@router.get("/tickets/validation-logs")
def get_validation_logs(
    limit: int = Query(100, ge=1, le=500, description="Maximum number of logs"),
    db: Session = Depends(get_db)
):
    """Get ticket validation logs (admin only)"""
    
    ticket_service = TicketService(db)
    logs = ticket_service.get_validation_logs(limit)
    
    return {
        "logs": logs,
        "total_logs": len(logs)
    }

# Administrative Endpoints
@router.post("/cleanup-expired")
def cleanup_expired_bookings(db: Session = Depends(get_db)):
    """Clean up expired bookings (admin task)"""
    
    booking_service = BookingService(db)
    journey_service = JourneyPlanningService(db)
    
    # Clean up expired bookings
    booking_results = booking_service.process_expired_bookings()
    
    # Clean up expired journey plans
    expired_journeys = journey_service.cleanup_expired_journeys()
    
    return {
        "message": "Cleanup completed",
        "expired_bookings": booking_results["expired"],
        "cancelled_bookings": booking_results["cancelled"],
        "expired_journeys": expired_journeys
    }

@router.get("/analytics")
def get_booking_analytics(
    date_from: date = Query(..., description="Start date for analytics"),
    date_to: date = Query(..., description="End date for analytics"),
    db: Session = Depends(get_db)
):
    """Get booking analytics for date range (admin only)"""
    
    booking_service = BookingService(db)
    
    date_from_dt = datetime.combine(date_from, datetime.min.time())
    date_to_dt = datetime.combine(date_to, datetime.max.time())
    
    analytics = booking_service.get_booking_analytics(date_from_dt, date_to_dt)
    
    return analytics

@router.get("/statistics")
def get_booking_statistics(db: Session = Depends(get_db)):
    """Get overall booking and ticket statistics"""
    
    booking_service = BookingService(db)
    ticket_service = TicketService(db)
    
    # Get ticket statistics
    ticket_stats = ticket_service.get_ticket_statistics()
    
    # Get basic booking stats
    all_bookings = list(booking_service._booking_storage.values())
    booking_stats = {
        "total_bookings": len(all_bookings),
        "pending_bookings": len([b for b in all_bookings if b.booking_status == BookingStatus.PENDING]),
        "confirmed_bookings": len([b for b in all_bookings if b.booking_status == BookingStatus.CONFIRMED]),
        "cancelled_bookings": len([b for b in all_bookings if b.booking_status == BookingStatus.CANCELLED])
    }
    
    return {
        "booking_statistics": booking_stats,
        "ticket_statistics": ticket_stats,
        "last_updated": datetime.now()
    }

@router.get("/search")
def search_bookings(
    booking_reference: Optional[str] = Query(None, description="Booking reference"),
    contact_email: Optional[str] = Query(None, description="Contact email"),
    booking_status: Optional[BookingStatus] = Query(None, description="Booking status"),
    payment_status: Optional[PaymentStatus] = Query(None, description="Payment status"),
    date_from: Optional[date] = Query(None, description="From date"),
    date_to: Optional[date] = Query(None, description="To date"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    db: Session = Depends(get_db)
):
    """Search bookings with filters (admin only)"""
    
    booking_service = BookingService(db)
    
    filters = BookingSearchFilters(
        booking_reference=booking_reference,
        contact_email=contact_email,
        booking_status=booking_status,
        payment_status=payment_status,
        date_from=date_from,
        date_to=date_to
    )
    
    bookings = booking_service.search_bookings(filters)
    
    return {
        "bookings": bookings[:limit],
        "total_found": len(bookings),
        "showing": min(limit, len(bookings))
    }