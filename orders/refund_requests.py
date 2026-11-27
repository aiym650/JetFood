from datetime import timedelta
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from payments.models import Payment
from users.models import Notification, User
from users.notifications import notify_order_status

from .models import Order, RefundRequest


ORDER_ACTIONS_BY_STATUS = {
    "pending": {"cancel": "instant"},
    "confirmed": {"cancel": "instant"},
    "preparing": {"cancel": "request"},
    "ready_for_pickup": {"cancel": "request"},
    "delivering": {"cancel": "request"},
    "delivered": {"refund": "request"},
}
REFUND_REQUEST_WINDOW = timedelta(hours=24)


def _customer_order(order_id, customer):
    try:
        return Order.objects.select_for_update().get(pk=order_id, customer=customer)
    except Order.DoesNotExist as error:
        raise NotFound("Order not found.") from error


def _payment_for_update(order):
    return Payment.objects.select_for_update().filter(order=order).first()


def _notify(user, title, message, link):
    Notification.objects.create(
        user=user,
        notification_type="system",
        title=title,
        message=message,
        link=link,
    )


def cancel_customer_order(order_id, customer, reason):
    with transaction.atomic():
        order = _customer_order(order_id, customer)
        if ORDER_ACTIONS_BY_STATUS.get(order.status, {}).get("cancel") != "instant":
            raise ValidationError({
                "detail": "This order requires a cancellation request for manager approval."
            })

        payment = _payment_for_update(order)
        if payment and payment.status == "refund_requested":
            raise ValidationError({
                "detail": "A cancellation request for this order is already awaiting a decision."
            })

        order.status = "cancelled"
        order.cancellation_reason = reason
        order.save(update_fields=["status", "cancellation_reason", "updated_at"])

        if payment:
            if payment.method == "online" and payment.status == "paid":
                payment.refunded_amount = payment.amount
                payment.status = "refunded"
                payment.refunded_at = timezone.now()
                payment.refund_reason = reason
                payment.save(update_fields=[
                    "status", "refunded_amount", "refunded_at", "refund_reason", "updated_at",
                ])
            elif payment.status in {"pending", "failed", "paid"}:
                payment.status = "cancelled"
                payment.refund_reason = reason
                payment.save(update_fields=["status", "refund_reason", "updated_at"])
            elif payment.status not in {"cancelled", "refunded"}:
                raise ValidationError({"detail": "The payment cannot be cancelled in its current state."})

        notify_order_status(order)
        return order


def create_customer_refund_request(order_id, customer, request_type, reason_category, reason_text):
    try:
        with transaction.atomic():
            order = _customer_order(order_id, customer)
            action = ORDER_ACTIONS_BY_STATUS.get(order.status, {}).get(request_type)
            if action != "request":
                raise ValidationError({
                    "detail": "A request of this type is not available for the current order status."
                })

            payment = _payment_for_update(order)
            if request_type == "refund":
                delivered_at = order.actual_delivery_time or order.delivery_confirmed_at
                if not delivered_at or timezone.now() > delivered_at + REFUND_REQUEST_WINDOW:
                    raise ValidationError({
                        "detail": "The 24-hour refund request window has expired."
                    })
                if not payment or payment.status != "paid":
                    raise ValidationError({
                        "detail": "A refund can only be requested for a paid order."
                    })
            elif payment and payment.method == "online" and payment.status != "paid":
                raise ValidationError({
                    "detail": "A cancellation request requires a completed online payment."
                })

            request = RefundRequest.objects.create(
                order=order,
                requested_by=customer,
                request_type=request_type,
                reason_category=reason_category,
                reason_text=reason_text,
            )
            if payment and request_type == "refund" and payment.method == "online":
                payment.status = "refund_requested"
                payment.save(update_fields=["status", "updated_at"])
            elif payment and request_type == "cancel" and payment.method == "online":
                payment.status = "refund_requested"
                payment.save(update_fields=["status", "updated_at"])

            title = "New cancellation request" if request_type == "cancel" else "New refund request"
            message = f"{customer.username} requested {request_type} for order {order.order_number}: {reason_text}"
            link = f"/orders?requestId={request.id}"
            for manager in User.objects.filter(role__in=["admin", "manager"]):
                _notify(manager, title, message, link)
            return request
    except IntegrityError as error:
        if RefundRequest.objects.filter(order_id=order_id, status="pending").exists():
            raise ValidationError({
                "detail": "There is already a pending request for this order."
            }) from error
        raise


def decide_refund_request(request_id, manager, decision, decision_note="", refund_amount=None):
    if decision not in {"approve", "reject"}:
        raise ValueError(f"Unsupported refund request decision: {decision}")

    with transaction.atomic():
        try:
            order_id = RefundRequest.objects.values_list("order_id", flat=True).get(pk=request_id)
        except RefundRequest.DoesNotExist as error:
            raise NotFound("Request not found.") from error
        order = Order.objects.select_for_update().get(pk=order_id)
        try:
            request = RefundRequest.objects.select_for_update().get(
                pk=request_id,
                order_id=order.pk,
            )
        except RefundRequest.DoesNotExist as error:
            raise NotFound("Request not found.") from error
        if request.status != "pending":
            raise ValidationError({"detail": "This request has already been decided."})

        payment = _payment_for_update(order)
        now = timezone.now()

        if decision == "reject":
            if not decision_note.strip():
                raise ValidationError({"decision_note": "A note is required when rejecting a request."})
            if payment and payment.method == "online" and payment.status == "refund_requested":
                payment.status = "paid"
                payment.save(update_fields=["status", "updated_at"])
            request.status = "rejected"
            request.decided_by = manager
            request.decided_at = now
            request.decision_note = decision_note.strip()
            request.save(update_fields=[
                "status", "decided_by", "decided_at", "decision_note",
            ])
            _notify(
                request.requested_by,
                "Order request rejected",
                f"Your request for order {order.order_number} was rejected. Note: {request.decision_note}",
                f"/orders?orderId={order.id}",
            )
            return request

        cancel_as_refund = request.request_type == "cancel" and order.status == "delivered"
        if request.request_type == "cancel" and not cancel_as_refund:
            if ORDER_ACTIONS_BY_STATUS.get(order.status, {}).get("cancel") != "request":
                raise ValidationError({
                    "detail": "The order can no longer be cancelled. Reject this request with a note."
                })
        elif request.request_type == "refund" and order.status != "delivered":
            raise ValidationError({"detail": "Refund requests can only be approved after delivery."})

        paid_amount = (
            payment.amount
            if payment and payment.status in {"paid", "refund_requested"}
            else Decimal("0.00")
        )
        amount = paid_amount if refund_amount is None else refund_amount
        if amount > paid_amount:
            raise ValidationError({"refund_amount": "The refund cannot exceed the amount paid."})

        unpaid_cash_cancellation = (
            request.request_type == "cancel"
            and not cancel_as_refund
            and payment is not None
            and payment.method == "cash"
            and payment.status == "pending"
            and amount == 0
        )
        no_payment_cancellation = (
            request.request_type == "cancel"
            and not cancel_as_refund
            and payment is None
            and amount == 0
        )
        if amount <= 0 and not unpaid_cash_cancellation and not no_payment_cancellation:
            raise ValidationError({"refund_amount": "The refund amount must be greater than zero."})
        refund_approval = request.request_type == "refund" or cancel_as_refund
        if refund_approval and (not payment or payment.status not in {"paid", "refund_requested"}):
            raise ValidationError({"detail": "Only paid orders can be refunded."})
        if payment and payment.method == "online" and payment.status != "refund_requested":
            raise ValidationError({"detail": "The online payment is not awaiting a refund decision."})

        if payment:
            payment.refund_reason = request.reason_text
            if request.request_type == "cancel" and not cancel_as_refund and payment.method == "cash":
                payment.status = "cancelled"
            else:
                previous_refunded = payment.refunded_amount
                payment.refunded_amount = min(payment.amount, previous_refunded + amount)
                payment.status = "refunded"
                payment.refunded_at = now
            payment.save(update_fields=[
                "status", "refunded_amount", "refund_reason", "refunded_at", "updated_at",
            ])
            if payment.status in {"refunded", "partially_refunded"}:
                from loyalty.services import apply_refund
                apply_refund(order, payment.refunded_amount, full=payment.refunded_amount >= payment.amount)

        if request.request_type == "cancel" and not cancel_as_refund:
            order.status = "cancelled"
            order.cancellation_reason = request.reason_text
            order.save(update_fields=["status", "cancellation_reason", "updated_at"])

        request.status = "approved"
        request.decided_by = manager
        request.decided_at = now
        request.decision_note = decision_note.strip()
        request.refund_amount = amount
        request.save(update_fields=[
            "status", "decided_by", "decided_at", "decision_note", "refund_amount",
        ])

        if cancel_as_refund:
            title = "Cancellation request approved as a refund"
        elif request.request_type == "cancel":
            title = "Cancellation request approved"
        else:
            title = "Refund request approved"
        message = f"Your request for order {order.order_number} was approved for {amount}."
        if request.decision_note:
            message += f" Note: {request.decision_note}"
        _notify(request.requested_by, title, message, f"/orders?orderId={order.id}")

        if request.request_type == "cancel" and not cancel_as_refund and order.status == "cancelled" and order.delivery_person_id:
            _notify(
                order.delivery_person,
                "Delivery stopped",
                f"Delivery for order {order.order_number} was stopped after its cancellation request was approved.",
                f"/orders?orderId={order.id}",
            )
        return request
