from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from decimal import Decimal
import uuid
import hashlib
import secrets
from collections import defaultdict

from src.bookings.schemas import (
    BookingReservationRequest, BookingReservation, BookingConfirmation,
    BookingModificationRequest, BookingCancellationRequest, BookingStatus,
    PaymentStatus, PassengerInfo, GroupBookingInfo, PaymentDetails,
    PaymentMethod, RefundRequest, RefundStatus, BookingSearchFilters,
    BookingExpiration, BookingAnalytics
)
from src.bookings.journey_service import JourneyPlanningService

class BookingService:
    """Service for managing train journey bookings"""
    
    def __init__(self, db: Session):
        self.db = db
        self.journey_service = JourneyPlanningService(db)
        self._booking_storage = {}  # In-memory storage (would use database)
        self._booking_counter = 10000
        self._expiration_tasks = []
    
    def create_reservation(self, request: BookingReservationRequest) -> BookingReservation:
        """Create a new booking reservation"""
        
        # Validate journey exists and is bookable
        validation = self.journey_service.validate_journey_for_booking(
            request.journey_id, 
            request.passengers
        )
        
        if not validation.is_valid:
            raise ValueError(f"Journey cannot be booked: {', '.join(validation.errors)}")
        
        # Get journey details
        journey = self.journey_service.get_journey_by_id(request.journey_id)
        if not journey:
            raise ValueError("Journey not found")
        
        # Generate booking IDs
        booking_id = str(uuid.uuid4())
        booking_reference = self._generate_booking_reference()
        
        # Calculate total amount
        total_amount = validation.estimated_total_cost or journey.total_cost
        
        # Apply group discount if applicable
        if request.group_booking_info:
            discount = request.group_booking_info.group_discount_percentage
            total_amount = total_amount * (Decimal('100') - discount) / Decimal('100')
        
        # Set expiration times
        booking_created_at = datetime.now()
        booking_expires_at = booking_created_at + timedelta(minutes=30)  # 30 min to confirm
        confirmation_deadline = journey.departure_time - timedelta(hours=2)  # 2 hours before departure
        
        # Create booking reservation
        reservation = BookingReservation(
            booking_id=booking_id,
            booking_reference=booking_reference,
            user_id=request.user_id,
            journey=journey,
            passengers=request.passengers,
            contact_email=request.contact_email,
            contact_phone=request.contact_phone,
            booking_status=BookingStatus.PENDING,
            payment_status=PaymentStatus.PENDING,
            total_amount=total_amount,
            booking_created_at=booking_created_at,
            booking_expires_at=booking_expires_at,
            confirmation_deadline=confirmation_deadline,
            group_booking_info=request.group_booking_info,
            special_requirements=request.special_requirements,
            booking_notes=request.booking_notes
        )
        
        # Store reservation
        self._booking_storage[booking_id] = reservation
        
        # Schedule expiration task
        self._schedule_expiration_task(booking_id, booking_expires_at)
        
        return reservation
    
    def confirm_booking(
        self, 
        booking_id: str,
        payment_method: PaymentMethod
    ) -> BookingConfirmation:
        """Confirm a pending booking with payment"""
        
        reservation = self._booking_storage.get(booking_id)
        if not reservation:
            raise ValueError("Booking not found")
        
        if reservation.booking_status != BookingStatus.PENDING:
            raise ValueError(f"Booking cannot be confirmed. Status: {reservation.booking_status}")
        
        if datetime.now() > reservation.booking_expires_at:
            raise ValueError("Booking has expired")
        
        # Process payment (simplified - no actual payment processing)
        payment_details = self._process_payment(reservation, payment_method)
        
        if payment_details.payment_status != PaymentStatus.PAID:
            raise ValueError("Payment processing failed")
        
        # Update booking status
        reservation.booking_status = BookingStatus.CONFIRMED
        reservation.payment_status = PaymentStatus.PAID
        
        # Generate tickets
        from src.bookings.ticket_service import TicketService
        ticket_service = TicketService(self.db)
        tickets = ticket_service.generate_tickets(reservation)
        
        # Generate confirmation number
        confirmation_number = self._generate_confirmation_number(booking_id)
        
        confirmation = BookingConfirmation(
            booking=reservation,
            tickets=tickets,
            payment_details=payment_details,
            confirmation_number=confirmation_number,
            qr_codes_generated=True,
            pdf_tickets_available=True
        )
        
        return confirmation
    
    def modify_booking(
        self, 
        booking_id: str,
        modification: BookingModificationRequest
    ) -> BookingReservation:
        """Modify an existing booking"""
        
        reservation = self._booking_storage.get(booking_id)
        if not reservation:
            raise ValueError("Booking not found")
        
        if reservation.booking_status not in [BookingStatus.PENDING, BookingStatus.CONFIRMED]:
            raise ValueError(f"Booking cannot be modified. Status: {reservation.booking_status}")
        
        # Check modification deadline (can't modify within 2 hours of departure)
        if datetime.now() > reservation.journey.departure_time - timedelta(hours=2):
            raise ValueError("Cannot modify booking within 2 hours of departure")
        
        # Apply modifications
        modified = False
        
        if modification.new_departure_time:
            # Would need to re-plan journey with new time
            # For now, just update the time
            time_diff = modification.new_departure_time - reservation.journey.departure_time
            reservation.journey.departure_time = modification.new_departure_time
            reservation.journey.arrival_time += time_diff
            modified = True
        
        if modification.additional_passengers:
            reservation.passengers.extend(modification.additional_passengers)
            # Recalculate total amount
            new_passenger_count = len(reservation.passengers)
            base_cost_per_person = reservation.journey.total_cost / len(reservation.passengers)
            reservation.total_amount += base_cost_per_person * len(modification.additional_passengers)
            modified = True
        
        if modification.remove_passenger_indices:
            # Remove passengers by index (in reverse order to maintain indices)
            for index in sorted(modification.remove_passenger_indices, reverse=True):
                if 0 <= index < len(reservation.passengers):
                    reservation.passengers.pop(index)
                    # Reduce total amount
                    base_cost_per_person = reservation.journey.total_cost / (len(reservation.passengers) + 1)
                    reservation.total_amount -= base_cost_per_person
                    modified = True
        
        if modification.update_contact_email:
            reservation.contact_email = modification.update_contact_email
            modified = True
        
        if modification.update_contact_phone:
            reservation.contact_phone = modification.update_contact_phone
            modified = True
        
        if modification.update_special_requirements:
            reservation.special_requirements = modification.update_special_requirements
            modified = True
        
        if not modified:
            raise ValueError("No valid modifications provided")
        
        # Add modification fee (simplified)
        if reservation.booking_status == BookingStatus.CONFIRMED:
            modification_fee = Decimal('50.00')  # 50 THB modification fee
            reservation.total_amount += modification_fee
        
        return reservation
    
    def cancel_booking(
        self, 
        booking_id: str,
        cancellation: BookingCancellationRequest
    ) -> RefundRequest:
        """Cancel a booking and process refund if applicable"""
        
        reservation = self._booking_storage.get(booking_id)
        if not reservation:
            raise ValueError("Booking not found")
        
        if reservation.booking_status == BookingStatus.CANCELLED:
            raise ValueError("Booking is already cancelled")
        
        # Calculate refund amount based on cancellation timing
        refund_amount = self._calculate_refund_amount(reservation)
        
        # Update booking status
        reservation.booking_status = BookingStatus.CANCELLED
        
        # Create refund request if applicable
        refund_request = None
        if cancellation.request_refund and refund_amount > 0:
            refund_id = str(uuid.uuid4())
            refund_request = RefundRequest(
                refund_id=refund_id,
                booking_id=booking_id,
                requested_amount=refund_amount,
                refund_reason=cancellation.cancellation_reason,
                refund_status=RefundStatus.REQUESTED,
                requested_at=datetime.now(),
                refund_method=cancellation.refund_method
            )
            
            # Auto-approve small refunds (simplified)
            if refund_amount <= Decimal('500.00'):
                refund_request.refund_status = RefundStatus.APPROVED
                refund_request.processed_at = datetime.now()
        
        # Cancel associated tickets
        # Would cancel tickets in real implementation
        
        return refund_request
    
    def get_booking(self, booking_id: str) -> Optional[BookingReservation]:
        """Get booking by ID"""
        return self._booking_storage.get(booking_id)
    
    def get_booking_by_reference(self, booking_reference: str) -> Optional[BookingReservation]:
        """Get booking by reference number"""
        for booking in self._booking_storage.values():
            if booking.booking_reference == booking_reference:
                return booking
        return None
    
    def get_user_bookings(
        self, 
        user_id: int,
        filters: Optional[BookingSearchFilters] = None
    ) -> List[BookingReservation]:
        """Get all bookings for a user"""
        
        bookings = [b for b in self._booking_storage.values() if b.user_id == user_id]
        
        if filters:
            bookings = self._apply_booking_filters(bookings, filters)
        
        # Sort by creation date (newest first)
        return sorted(bookings, key=lambda x: x.booking_created_at, reverse=True)
    
    def search_bookings(self, filters: BookingSearchFilters) -> List[BookingReservation]:
        """Search bookings with filters"""
        
        bookings = list(self._booking_storage.values())
        return self._apply_booking_filters(bookings, filters)
    
    def process_expired_bookings(self) -> Dict[str, int]:
        """Process expired bookings and clean up"""
        
        current_time = datetime.now()
        expired_count = 0
        cancelled_count = 0
        
        for booking_id, booking in self._booking_storage.items():
            if (booking.booking_status == BookingStatus.PENDING and 
                current_time > booking.booking_expires_at):
                
                booking.booking_status = BookingStatus.EXPIRED
                expired_count += 1
                
                # Auto-cancel if past confirmation deadline
                if current_time > booking.confirmation_deadline:
                    booking.booking_status = BookingStatus.CANCELLED
                    cancelled_count += 1
        
        return {
            "expired": expired_count,
            "cancelled": cancelled_count
        }
    
    def get_booking_analytics(
        self, 
        date_from: datetime,
        date_to: datetime
    ) -> BookingAnalytics:
        """Generate booking analytics for date range"""
        
        bookings = [
            b for b in self._booking_storage.values()
            if date_from <= b.booking_created_at <= date_to
        ]
        
        total_bookings = len(bookings)
        confirmed_bookings = len([b for b in bookings if b.booking_status == BookingStatus.CONFIRMED])
        cancelled_bookings = len([b for b in bookings if b.booking_status == BookingStatus.CANCELLED])
        
        total_revenue = sum(
            b.total_amount for b in bookings 
            if b.booking_status == BookingStatus.CONFIRMED
        )
        
        avg_booking_value = total_revenue / confirmed_bookings if confirmed_bookings > 0 else Decimal('0')
        
        # Calculate popular routes
        route_counts = defaultdict(int)
        for booking in bookings:
            route_key = f"{booking.journey.from_station_id}-{booking.journey.to_station_id}"
            route_counts[route_key] += 1
        
        popular_routes = [
            {
                "route": route,
                "bookings": count,
                "percentage": (count / total_bookings) * 100 if total_bookings > 0 else 0
            }
            for route, count in sorted(route_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        ]
        
        # Passenger type distribution
        passenger_distribution = defaultdict(int)
        for booking in bookings:
            for passenger in booking.passengers:
                passenger_distribution[passenger.passenger_type_name] += 1
        
        return BookingAnalytics(
            total_bookings=total_bookings,
            confirmed_bookings=confirmed_bookings,
            cancelled_bookings=cancelled_bookings,
            total_revenue=total_revenue,
            average_booking_value=avg_booking_value,
            popular_routes=popular_routes,
            booking_trends=[],  # Would calculate trends
            passenger_distribution=dict(passenger_distribution),
            peak_booking_times=["09:00-10:00", "14:00-15:00", "18:00-19:00"]  # Simplified
        )
    
    def _generate_booking_reference(self) -> str:
        """Generate human-readable booking reference"""
        self._booking_counter += 1
        return f"BKK{self._booking_counter:06d}"
    
    def _process_payment(
        self, 
        reservation: BookingReservation,
        payment_method: PaymentMethod
    ) -> PaymentDetails:
        """Process payment for booking (simplified simulation)"""
        
        payment_id = str(uuid.uuid4())
        transaction_id = f"TXN{secrets.token_hex(8).upper()}"
        
        # Simulate payment processing
        payment_success = True  # Would integrate with payment gateway
        
        payment_details = PaymentDetails(
            payment_id=payment_id,
            booking_id=reservation.booking_id,
            amount=reservation.total_amount,
            payment_method=payment_method,
            payment_status=PaymentStatus.PAID if payment_success else PaymentStatus.FAILED,
            transaction_id=transaction_id,
            processed_at=datetime.now() if payment_success else None
        )
        
        return payment_details
    
    def _calculate_refund_amount(self, reservation: BookingReservation) -> Decimal:
        """Calculate refund amount based on cancellation timing"""
        
        current_time = datetime.now()
        departure_time = reservation.journey.departure_time
        time_until_departure = departure_time - current_time
        
        # Refund policy (simplified)
        if time_until_departure.total_seconds() <= 0:
            return Decimal('0')  # No refund after departure
        elif time_until_departure.days >= 7:
            return reservation.total_amount * Decimal('0.9')  # 90% refund if 7+ days
        elif time_until_departure.days >= 3:
            return reservation.total_amount * Decimal('0.7')  # 70% refund if 3-6 days
        elif time_until_departure.days >= 1:
            return reservation.total_amount * Decimal('0.5')  # 50% refund if 1-2 days
        elif time_until_departure.total_seconds() >= 7200:  # 2 hours
            return reservation.total_amount * Decimal('0.3')  # 30% refund if 2+ hours
        else:
            return Decimal('0')  # No refund within 2 hours
    
    def _apply_booking_filters(
        self, 
        bookings: List[BookingReservation],
        filters: BookingSearchFilters
    ) -> List[BookingReservation]:
        """Apply search filters to booking list"""
        
        if filters.booking_status:
            bookings = [b for b in bookings if b.booking_status == filters.booking_status]
        
        if filters.payment_status:
            bookings = [b for b in bookings if b.payment_status == filters.payment_status]
        
        if filters.date_from:
            bookings = [b for b in bookings if b.booking_created_at.date() >= filters.date_from]
        
        if filters.date_to:
            bookings = [b for b in bookings if b.booking_created_at.date() <= filters.date_to]
        
        if filters.booking_reference:
            bookings = [b for b in bookings if filters.booking_reference.lower() in b.booking_reference.lower()]
        
        if filters.contact_email:
            bookings = [b for b in bookings if filters.contact_email.lower() in b.contact_email.lower()]
        
        return bookings
    
    def _schedule_expiration_task(self, booking_id: str, expires_at: datetime):
        """Schedule task to handle booking expiration"""
        
        expiration_task = BookingExpiration(
            booking_id=booking_id,
            expires_at=expires_at
        )
        
        self._expiration_tasks.append(expiration_task)
    
    def _generate_confirmation_number(self, booking_id: str) -> str:
        """Generate confirmation number"""
        hash_input = f"{booking_id}{datetime.now().isoformat()}"
        hash_object = hashlib.md5(hash_input.encode())
        return f"CNF{hash_object.hexdigest()[:8].upper()}"