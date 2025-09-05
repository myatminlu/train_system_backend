from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Literal, Any
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
import uuid

class BookingStatus(str, Enum):
    """Booking status enumeration"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    COMPLETED = "completed"
    REFUNDED = "refunded"

class PaymentStatus(str, Enum):
    """Payment status enumeration"""
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIAL_REFUND = "partial_refund"

class TicketStatus(str, Enum):
    """Ticket status enumeration"""
    ACTIVE = "active"
    USED = "used"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

class RefundStatus(str, Enum):
    """Refund status enumeration"""
    NONE = "none"
    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    PROCESSED = "processed"

# Journey and Booking Models
class JourneySegment(BaseModel):
    """Individual segment of a planned journey"""
    segment_order: int
    from_station_id: int
    from_station_name: str
    to_station_id: int
    to_station_name: str
    line_id: int
    line_name: str
    transport_type: Literal["train", "transfer", "walk"]
    departure_time: datetime
    arrival_time: datetime
    duration_minutes: int
    cost: Decimal
    platform_info: Optional[str] = None
    instructions: str

class PlannedJourney(BaseModel):
    """Complete planned journey with all segments"""
    journey_id: str
    from_station_id: int
    to_station_id: int
    departure_time: datetime
    arrival_time: datetime
    total_duration_minutes: int
    total_cost: Decimal
    total_transfers: int
    segments: List[JourneySegment]
    optimization_used: Literal["time", "cost", "transfers"]
    created_at: datetime = Field(default_factory=datetime.now)

# Passenger Information
class PassengerInfo(BaseModel):
    """Individual passenger information"""
    passenger_type_id: int = 1  # Default to adult
    passenger_type_name: str = "Adult"
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    age: Optional[int] = None
    id_number: Optional[str] = None  # For discounted tickets
    special_requirements: Optional[str] = None

class GroupBookingInfo(BaseModel):
    """Information for group bookings"""
    group_name: str
    group_leader_email: str
    group_leader_phone: str
    organization: Optional[str] = None
    group_discount_percentage: Decimal = Decimal('0')
    special_instructions: Optional[str] = None

# Booking Request Models
class BookingReservationRequest(BaseModel):
    """Request to reserve/book a journey"""
    journey_id: str
    user_id: int
    passengers: List[PassengerInfo]
    contact_email: str
    contact_phone: str
    preferred_departure_time: Optional[datetime] = None
    special_requirements: Optional[str] = None
    group_booking_info: Optional[GroupBookingInfo] = None
    booking_notes: Optional[str] = None
    
    @validator('passengers')
    def validate_passengers(cls, v):
        if not v or len(v) == 0:
            raise ValueError('At least one passenger is required')
        if len(v) > 10:
            raise ValueError('Maximum 10 passengers per booking')
        return v

class BookingModificationRequest(BaseModel):
    """Request to modify an existing booking"""
    new_departure_time: Optional[datetime] = None
    additional_passengers: Optional[List[PassengerInfo]] = None
    remove_passenger_indices: Optional[List[int]] = None
    update_contact_email: Optional[str] = None
    update_contact_phone: Optional[str] = None
    update_special_requirements: Optional[str] = None
    modification_reason: str

class BookingCancellationRequest(BaseModel):
    """Request to cancel a booking"""
    cancellation_reason: str
    request_refund: bool = True
    refund_method: Optional[Literal["original", "credit", "bank_transfer"]] = "original"
    bank_details: Optional[Dict[str, str]] = None

# Booking Response Models
class BookingReservation(BaseModel):
    """Booking reservation details"""
    booking_id: str
    booking_reference: str  # Human-readable reference
    user_id: int
    journey: PlannedJourney
    passengers: List[PassengerInfo]
    contact_email: str
    contact_phone: str
    booking_status: BookingStatus
    payment_status: PaymentStatus
    total_amount: Decimal
    currency: str = "THB"
    booking_created_at: datetime
    booking_expires_at: datetime
    confirmation_deadline: datetime
    group_booking_info: Optional[GroupBookingInfo] = None
    special_requirements: Optional[str] = None
    booking_notes: Optional[str] = None

class BookingConfirmation(BaseModel):
    """Booking confirmation with ticket details"""
    booking: BookingReservation
    tickets: List['DigitalTicket']
    payment_details: Optional['PaymentDetails'] = None
    confirmation_number: str
    qr_codes_generated: bool
    pdf_tickets_available: bool

# Ticket Models
class TicketSecurityInfo(BaseModel):
    """Security information for ticket validation"""
    ticket_hash: str
    validation_code: str
    encryption_key: Optional[str] = None
    issued_timestamp: datetime
    expires_at: datetime

class DigitalTicket(BaseModel):
    """Digital ticket with QR code"""
    ticket_id: str
    booking_id: str
    passenger_info: PassengerInfo
    journey: PlannedJourney
    ticket_status: TicketStatus
    qr_code_data: str
    qr_code_image_url: Optional[str] = None
    security_info: TicketSecurityInfo
    issued_at: datetime
    valid_from: datetime
    valid_until: datetime
    usage_restrictions: Optional[Dict[str, Any]] = None
    is_transferable: bool = False
    used_at: Optional[datetime] = None
    validated_at: Optional[datetime] = None

class TicketValidationRequest(BaseModel):
    """Request to validate a ticket"""
    ticket_id: str
    qr_code_data: str
    validation_station_id: int
    validator_id: Optional[str] = None  # Staff/machine ID
    validation_timestamp: datetime = Field(default_factory=datetime.now)

class TicketValidationResponse(BaseModel):
    """Response from ticket validation"""
    ticket_id: str
    is_valid: bool
    validation_status: Literal["valid", "invalid", "expired", "already_used", "not_found", "tampered"]
    passenger_name: Optional[str] = None
    journey_info: Optional[str] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    validation_message: str
    validation_timestamp: datetime
    allow_entry: bool

# Payment Models (simplified - no actual payment processing)
class PaymentMethod(BaseModel):
    """Payment method information"""
    method_type: Literal["credit_card", "debit_card", "mobile_wallet", "bank_transfer", "cash"]
    method_details: Dict[str, str]  # Card last 4 digits, wallet name, etc.

class PaymentConfirmationRequest(BaseModel):
    """Request to confirm a booking with payment"""
    payment_method_type: Literal["credit_card", "debit_card", "mobile_wallet", "bank_transfer", "cash"]
    payment_details: Dict[str, str] = Field(default_factory=dict, description="Payment method details")

class PaymentDetails(BaseModel):
    """Payment details for booking"""
    payment_id: str
    booking_id: str
    amount: Decimal
    currency: str = "THB"
    payment_method: PaymentMethod
    payment_status: PaymentStatus
    transaction_id: Optional[str] = None
    processed_at: Optional[datetime] = None
    refund_amount: Decimal = Decimal('0')
    refund_processed_at: Optional[datetime] = None

# Booking Management Models
class BookingSearchFilters(BaseModel):
    """Filters for searching bookings"""
    user_id: Optional[int] = None
    booking_status: Optional[BookingStatus] = None
    payment_status: Optional[PaymentStatus] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    booking_reference: Optional[str] = None
    contact_email: Optional[str] = None
    line_ids: Optional[List[int]] = None
    station_ids: Optional[List[int]] = None

class BookingAnalytics(BaseModel):
    """Booking analytics and statistics"""
    total_bookings: int
    confirmed_bookings: int
    cancelled_bookings: int
    total_revenue: Decimal
    average_booking_value: Decimal
    popular_routes: List[Dict[str, Any]]
    booking_trends: List[Dict[str, Any]]
    passenger_distribution: Dict[str, int]
    peak_booking_times: List[str]

class RefundRequest(BaseModel):
    """Refund request details"""
    refund_id: str
    booking_id: str
    requested_amount: Decimal
    refund_reason: str
    refund_status: RefundStatus
    requested_at: datetime
    processed_at: Optional[datetime] = None
    refund_method: Literal["original", "credit", "bank_transfer"]
    processing_notes: Optional[str] = None

# Booking Expiration and Cleanup
class BookingExpiration(BaseModel):
    """Booking expiration handling"""
    booking_id: str
    expires_at: datetime
    warning_sent_at: Optional[datetime] = None
    final_warning_sent_at: Optional[datetime] = None
    expired_at: Optional[datetime] = None
    auto_cancelled: bool = False

class BookingCleanupTask(BaseModel):
    """Task for cleaning up expired bookings"""
    task_id: str
    scheduled_time: datetime
    processed_bookings: int = 0
    expired_bookings: int = 0
    cancelled_bookings: int = 0
    errors: List[str] = []
    completed_at: Optional[datetime] = None

# Booking Statistics and Reports
class BookingReport(BaseModel):
    """Comprehensive booking report"""
    report_id: str
    report_type: Literal["daily", "weekly", "monthly", "custom"]
    date_range_start: date
    date_range_end: date
    total_bookings: int
    confirmed_bookings: int
    cancelled_bookings: int
    total_passengers: int
    total_revenue: Decimal
    average_booking_value: Decimal
    top_routes: List[Dict[str, Any]]
    booking_by_hour: Dict[int, int]
    booking_by_day: Dict[str, int]
    passenger_type_distribution: Dict[str, int]
    generated_at: datetime

class BookingValidation(BaseModel):
    """Booking validation results"""
    is_valid: bool
    errors: List[str] = []
    warnings: List[str] = []
    journey_available: bool = True
    capacity_available: bool = True
    schedule_conflicts: List[str] = []
    estimated_total_cost: Optional[Decimal] = None

# QR Code and PDF Models
class QRCodeGeneration(BaseModel):
    """QR code generation request"""
    ticket_id: str
    data_payload: str
    qr_size: int = 300
    border_size: int = 4
    error_correction: Literal["L", "M", "Q", "H"] = "M"
    include_logo: bool = False

class PDFTicketGeneration(BaseModel):
    """PDF ticket generation request"""
    booking_id: str
    include_qr_codes: bool = True
    include_journey_map: bool = False
    template_style: Literal["standard", "compact", "detailed"] = "standard"
    language: Literal["en", "th"] = "en"

class BulkBookingOperation(BaseModel):
    """Bulk booking operation for group bookings"""
    operation_id: str
    operation_type: Literal["create", "modify", "cancel"]
    bookings: List[str]  # Booking IDs
    batch_size: int = 10
    started_at: datetime
    completed_at: Optional[datetime] = None
    success_count: int = 0
    error_count: int = 0
    errors: List[Dict[str, str]] = []

# Forward reference resolution
BookingConfirmation.model_rebuild()