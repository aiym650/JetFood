from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.utils import timezone
from django.db import IntegrityError
from rest_framework import status
from rest_framework.test import APITestCase

from payments.models import Payment
from users.models import Notification, User

from .models import Order, RefundRequest
from .refund_requests import decide_refund_request


class RefundRequestApiTests(APITestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            username="refund-customer",
            password="pass12345",
            role="customer",
        )
        self.other_customer = User.objects.create_user(
            username="other-customer",
            password="pass12345",
            role="customer",
        )
        self.manager = User.objects.create_user(
            username="refund-manager",
            password="pass12345",
            role="manager",
        )
        self.admin = User.objects.create_user(
            username="refund-admin",
            password="pass12345",
            role="admin",
        )
        self.courier = User.objects.create_user(
            username="refund-courier",
            password="pass12345",
            role="delivery",
        )
        self.order_sequence = 0

    def create_order(
        self,
        order_status="preparing",
        method="online",
        payment_status="paid",
        *,
        delivery_person=None,
        actual_delivery_time=None,
        delivery_confirmed_at=None,
    ):
        self.order_sequence += 1
        now = timezone.now()
        order = Order.objects.create(
            order_number=f"ORD-REFUND-{self.order_sequence}",
            customer=self.customer,
            delivery_person=delivery_person,
            status=order_status,
            total_amount=Decimal("50.00"),
            delivery_address="1 Main Street",
            actual_delivery_time=actual_delivery_time,
            delivery_confirmed_at=delivery_confirmed_at,
        )
        Payment.objects.create(
            order=order,
            method=method,
            status=payment_status,
            amount=Decimal("50.00"),
            paid_at=now if payment_status == "paid" else None,
        )
        return order

    def create_request(self, order, request_type="cancel", **overrides):
        data = {
            "request_type": request_type,
            "reason_text": "The order cannot be completed as requested.",
        }
        if request_type == "refund":
            data["reason_category"] = "missing_items"
        data.update(overrides)
        self.client.force_authenticate(self.customer)
        return self.client.post(
            f"/api/orders/{order.id}/requests/",
            data,
            format="json",
        )

    def decide(self, refund_request, action, data):
        self.client.force_authenticate(self.manager)
        return self.client.post(
            f"/api/orders/requests/{refund_request.id}/{action}/",
            data,
            format="json",
        )

    def test_instant_cancel_requires_reason_and_refunds_paid_online_order(self):
        order = self.create_order("confirmed", "online", "paid")
        self.client.force_authenticate(self.customer)

        missing_reason = self.client.post(
            f"/api/orders/{order.id}/cancel/",
            {},
            format="json",
        )
        self.assertEqual(missing_reason.status_code, status.HTTP_400_BAD_REQUEST)
        order.refresh_from_db()
        self.assertEqual(order.status, "confirmed")

        cancelled = self.client.post(
            f"/api/orders/{order.id}/cancel/",
            {"reason": "I changed my mind about this order."},
            format="json",
        )
        self.assertEqual(cancelled.status_code, status.HTTP_200_OK, cancelled.data)
        order.refresh_from_db()
        self.assertEqual(order.status, "cancelled")
        self.assertEqual(order.cancellation_reason, "I changed my mind about this order.")
        self.assertEqual(order.payment.status, "refunded")
        self.assertEqual(order.payment.refund_reason, order.cancellation_reason)

    def test_instant_cancel_allowed_only_before_preparation_and_cancels_unpaid_cash(self):
        self.client.force_authenticate(self.customer)
        for order_status in ("pending", "confirmed"):
            order = self.create_order(order_status, "cash", "pending")
            response = self.client.post(
                f"/api/orders/{order.id}/status/",
                {"status": "cancelled", "reason": "I no longer need this order."},
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            order.refresh_from_db()
            self.assertEqual(order.status, "cancelled")
            self.assertEqual(order.payment.status, "cancelled")

        for order_status in ("preparing", "ready_for_pickup", "delivering", "delivered"):
            order = self.create_order(order_status, "cash", "pending")
            response = self.client.post(
                f"/api/orders/{order.id}/cancel/",
                {"reason": "I no longer need this order."},
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            order.refresh_from_db()
            self.assertEqual(order.status, order_status)

    def test_cancel_request_is_allowed_only_while_order_is_in_progress(self):
        self.client.force_authenticate(self.customer)
        for order_status in ("preparing", "ready_for_pickup", "delivering"):
            order = self.create_order(order_status, "cash", "pending")
            response = self.create_request(order)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
            self.assertEqual(response.data["status"], "pending")

        for order_status in ("pending", "confirmed", "delivered", "cancelled"):
            order = self.create_order(order_status, "cash", "pending")
            response = self.create_request(order)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_refund_request_requires_category_comment_and_delivery_within_24_hours(self):
        self.client.force_authenticate(self.customer)
        delivered = timezone.now() - timedelta(hours=23)
        order = self.create_order(
            "delivered",
            "online",
            "paid",
            actual_delivery_time=delivered,
        )
        missing_comment = self.create_request(order, "refund", reason_text="")
        self.assertEqual(missing_comment.status_code, status.HTTP_400_BAD_REQUEST)

        missing_category = self.create_request(order, "refund", reason_category="")
        self.assertEqual(missing_category.status_code, status.HTTP_400_BAD_REQUEST)

        short_comment = self.create_request(
            order,
            "refund",
            reason_category="missing_items",
            reason_text="Too short",
        )
        self.assertEqual(short_comment.status_code, status.HTTP_400_BAD_REQUEST)

        accepted = self.create_request(order, "refund")
        self.assertEqual(accepted.status_code, status.HTTP_201_CREATED, accepted.data)
        self.assertEqual(Payment.objects.get(order=order).status, "refund_requested")

        expired_order = self.create_order(
            "delivered",
            "cash",
            "paid",
            actual_delivery_time=timezone.now() - timedelta(hours=24, seconds=1),
        )
        expired = self.create_request(expired_order, "refund")
        self.assertEqual(expired.status_code, status.HTTP_400_BAD_REQUEST)

        fallback_order = self.create_order(
            "delivered",
            "cash",
            "paid",
            delivery_confirmed_at=timezone.now() - timedelta(hours=1),
        )
        fallback = self.create_request(fallback_order, "refund")
        self.assertEqual(fallback.status_code, status.HTTP_201_CREATED, fallback.data)

    def test_only_one_pending_request_per_order_and_duplicate_api_returns_400(self):
        order = self.create_order("preparing", "cash", "pending")
        first = self.create_request(order)
        second = self.create_request(order)

        self.assertEqual(first.status_code, status.HTTP_201_CREATED, first.data)
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(RefundRequest.objects.filter(order=order, status="pending").count(), 1)

    def test_approval_cancels_order_and_refunds_payment_atomically(self):
        order = self.create_order("preparing", "online", "paid")
        created = self.create_request(order)
        refund_request = RefundRequest.objects.get(pk=created.data["id"])
        self.assertEqual(Payment.objects.get(order=order).status, "refund_requested")

        approved = self.decide(refund_request, "approve", {"refund_amount": "50.00"})
        self.assertEqual(approved.status_code, status.HTTP_200_OK, approved.data)
        order.refresh_from_db()
        refund_request.refresh_from_db()
        self.assertEqual(order.status, "cancelled")
        self.assertEqual(order.payment.status, "refunded")
        self.assertEqual(refund_request.status, "approved")
        self.assertEqual(refund_request.refund_amount, Decimal("50.00"))
        self.assertEqual(refund_request.decided_by, self.manager)
        self.assertIsNotNone(refund_request.decided_at)
        self.assertTrue(Notification.objects.filter(
            user=self.customer,
            title="Cancellation request approved",
        ).exists())

    def test_decision_rolls_back_order_and_payment_when_request_write_fails(self):
        order = self.create_order("preparing", "online", "paid")
        created = self.create_request(order)
        refund_request = RefundRequest.objects.get(pk=created.data["id"])

        with patch.object(RefundRequest, "save", side_effect=IntegrityError("simulated failure")):
            with self.assertRaises(IntegrityError):
                decide_refund_request(
                    refund_request.id,
                    self.manager,
                    "approve",
                    refund_amount=Decimal("50.00"),
                )

        order.refresh_from_db()
        refund_request.refresh_from_db()
        self.assertEqual(order.status, "preparing")
        self.assertEqual(order.payment.status, "refund_requested")
        self.assertEqual(refund_request.status, "pending")

    def test_rejection_restores_online_payment_and_requires_note(self):
        order = self.create_order("ready_for_pickup", "online", "paid")
        created = self.create_request(order)
        refund_request = RefundRequest.objects.get(pk=created.data["id"])

        missing_note = self.decide(refund_request, "reject", {})
        self.assertEqual(missing_note.status_code, status.HTTP_400_BAD_REQUEST)
        rejected = self.decide(
            refund_request,
            "reject",
            {"decision_note": "The courier is already on the way."},
        )
        self.assertEqual(rejected.status_code, status.HTTP_200_OK, rejected.data)
        order.refresh_from_db()
        refund_request.refresh_from_db()
        self.assertEqual(order.status, "ready_for_pickup")
        self.assertEqual(order.payment.status, "paid")
        self.assertEqual(refund_request.status, "rejected")
        self.assertEqual(refund_request.decision_note, "The courier is already on the way.")

    def test_refund_amount_cannot_exceed_paid_amount_and_partial_refund_keeps_delivery(self):
        order = self.create_order(
            "delivered",
            "online",
            "paid",
            actual_delivery_time=timezone.now() - timedelta(hours=2),
        )
        created = self.create_request(order, "refund")
        refund_request = RefundRequest.objects.get(pk=created.data["id"])

        too_large = self.decide(refund_request, "approve", {"refund_amount": "50.01"})
        self.assertEqual(too_large.status_code, status.HTTP_400_BAD_REQUEST)

        approved = self.decide(refund_request, "approve", {"refund_amount": "12.50"})
        self.assertEqual(approved.status_code, status.HTTP_200_OK, approved.data)
        order.refresh_from_db()
        refund_request.refresh_from_db()
        self.assertEqual(order.status, "delivered")
        self.assertEqual(order.payment.status, "refunded")
        self.assertEqual(refund_request.refund_amount, Decimal("12.50"))

    def test_cancel_request_that_reaches_delivery_is_approved_as_refund(self):
        order = self.create_order("delivering", "online", "paid")
        created = self.create_request(order)
        refund_request = RefundRequest.objects.get(pk=created.data["id"])
        order.status = "delivered"
        order.actual_delivery_time = timezone.now()
        order.save(update_fields=["status", "actual_delivery_time", "updated_at"])

        approved = self.decide(refund_request, "approve", {"refund_amount": "20.00"})
        self.assertEqual(approved.status_code, status.HTTP_200_OK, approved.data)
        order.refresh_from_db()
        self.assertEqual(order.status, "delivered")
        self.assertEqual(order.payment.status, "refunded")
        self.assertEqual(approved.data["refund_amount"], "20.00")

    def test_approved_delivering_cancellation_notifies_assigned_courier(self):
        order = self.create_order(
            "delivering",
            "cash",
            "pending",
            delivery_person=self.courier,
        )
        created = self.create_request(order)
        refund_request = RefundRequest.objects.get(pk=created.data["id"])

        approved = self.decide(refund_request, "approve", {"refund_amount": "0.00"})
        self.assertEqual(approved.status_code, status.HTTP_200_OK, approved.data)
        order.refresh_from_db()
        self.assertEqual(order.status, "cancelled")
        self.assertTrue(Notification.objects.filter(
            user=self.courier,
            title="Delivery stopped",
        ).exists())

    def test_request_permissions_and_staff_notifications(self):
        order = self.create_order("preparing", "cash", "pending")
        created = self.create_request(order)
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Notification.objects.filter(
            user=self.manager,
            title="New cancellation request",
        ).exists())
        self.assertTrue(Notification.objects.filter(
            user=self.admin,
            title="New cancellation request",
        ).exists())

        self.client.force_authenticate(self.other_customer)
        hidden = self.client.get("/api/orders/requests/")
        self.assertEqual(hidden.status_code, status.HTTP_200_OK)
        self.assertEqual(hidden.data, [])
        cannot_create = self.client.post(
            f"/api/orders/{order.id}/requests/",
            {
                "request_type": "cancel",
                "reason_text": "Please cancel this order.",
            },
            format="json",
        )
        self.assertEqual(cannot_create.status_code, status.HTTP_404_NOT_FOUND)

        self.client.force_authenticate(self.courier)
        forbidden_list = self.client.get("/api/orders/requests/")
        self.assertEqual(forbidden_list.status_code, status.HTTP_403_FORBIDDEN)
        forbidden_create = self.client.post(
            f"/api/orders/{order.id}/requests/",
            {
                "request_type": "cancel",
                "reason_text": "Please cancel this order.",
            },
            format="json",
        )
        self.assertEqual(forbidden_create.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.customer)
        forbidden_decision = self.client.post(
            f"/api/orders/requests/{created.data['id']}/approve/",
            {},
            format="json",
        )
        self.assertEqual(forbidden_decision.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.admin)
        all_requests = self.client.get("/api/orders/requests/?status=pending")
        self.assertEqual(all_requests.status_code, status.HTTP_200_OK)
        self.assertEqual(len(all_requests.data), 1)
        admin_decision = self.client.post(
            f"/api/orders/requests/{created.data['id']}/approve/",
            {"refund_amount": "0.00"},
            format="json",
        )
        self.assertEqual(admin_decision.status_code, status.HTTP_200_OK, admin_decision.data)
