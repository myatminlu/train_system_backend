"""
Booking & Ticketing System Module

This module provides comprehensive booking and ticketing functionality for the
Bangkok Train Transport System. It includes:

- Journey planning for booking purposes
- Complete booking lifecycle management (reserve, confirm, modify, cancel)
- Digital ticket generation with QR codes
- Ticket validation and security features
- PDF ticket generation for printing
- Group booking capabilities
- Refund and cancellation management
- Booking analytics and reporting

Key Components:
- journey_service.py: Journey planning and validation for bookings
- booking_service.py: Core booking management with reservation system
- ticket_service.py: Digital ticket generation with QR codes and PDF export
- router.py: FastAPI endpoints for booking and ticket management
- schemas.py: Pydantic models for booking and ticket data structures

Features:
- Complete booking workflow from journey planning to ticket validation
- QR code generation with security features and encryption
- PDF ticket generation with multiple template styles
- Real-time booking validation with capacity and schedule checking
- Intelligent refund calculation based on cancellation timing
- Group booking support with discounts and bulk operations
- Comprehensive booking search and analytics
- Ticket validation system for entry gates and conductors
"""

from .router import router
from .journey_service import JourneyPlanningService
from .booking_service import BookingService
from .ticket_service import TicketService
from .schemas import (
    BookingReservationRequest, BookingReservation, BookingConfirmation,
    BookingModificationRequest, BookingCancellationRequest, BookingStatus,
    PaymentStatus, DigitalTicket, TicketStatus, TicketValidationRequest,
    TicketValidationResponse, PlannedJourney, BookingAnalytics
)

__all__ = [
    "router",
    "JourneyPlanningService",
    "BookingService", 
    "TicketService",
    "BookingReservationRequest",
    "BookingReservation",
    "BookingConfirmation",
    "BookingModificationRequest",
    "BookingCancellationRequest", 
    "BookingStatus",
    "PaymentStatus",
    "DigitalTicket",
    "TicketStatus",
    "TicketValidationRequest",
    "TicketValidationResponse",
    "PlannedJourney",
    "BookingAnalytics"
]