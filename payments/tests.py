from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from orders.models import MenuItem, Order
from restaurants.models import Restaurant
from .models import Payment
from .serializers import luhn_is_valid

User = get_user_model()


class PaymentApiTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            username="customer", password="pass12345", role="customer"
        )
        self.other_customer = User.objects.create_user(
            username="other-customer", password="pass12345", role="customer"
        )
        self.manager = User.objects.create_user(
            username="manager", password="pass12345", role="manager"
        )
        self.courier = User.objects.create_user(
            username="courier", password="pass12345", role="delivery"
        )
        restaurant = Restaurant.objects.create(
            name="Payment Test Kitchen",
            address="Payment Street 1",
        )
        self.menu_item = MenuItem.objects.create(
            name="Payment test meal",
            category="Test",
            price="25.00",
            restaurant=restaurant,
        )
        self.client = APIClient()

    def create_order(self, method="cash"):
        self.client.force_authenticate(user=self.customer)
        response = self.client.post(
            "/api/orders/",
            {
                "delivery_address": "1 Main Street",
                "payment_method": method,
                "items": [{"item_id": self.menu_item.id, "quantity": 1}],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return Order.objects.get(pk=response.data["id"])

    def card_data(self, card_number):
        return {
            "card_number": card_number,
            "expiry": "12/99",
            "cvv": "123",
            "cardholder_name": "TEST USER",
        }

    def pay_order(self, order, card_number):
        return self.client.post(
            f"/api/payments/{order.id}/pay/",
            self.card_data(card_number),
            format="json",
        )

    def test_online_payment_starts_pending_and_customer_history_is_private(self):
        order = self.create_order("online")
        payment = Payment.objects.get(order=order)
        self.assertEqual(payment.status, "pending")

        paid = self.pay_order(order, "4242 4242 4242 4242")
        self.assertEqual(paid.status_code, status.HTTP_200_OK)
        payment.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(payment.status, "paid")
        self.assertEqual(order.status, "confirmed")
        self.assertTrue(payment.transaction_id.startswith("SIM-"))
        self.assertIsNotNone(payment.paid_at)

        response = self.client.get("/api/payments/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["results"][0]["order_number"], order.order_number
        )

        self.client.force_authenticate(user=self.other_customer)
        response = self.client.get("/api/payments/")
        self.assertEqual(response.data["results"], [])

    def test_luhn_validation_and_field_errors(self):
        self.assertTrue(luhn_is_valid("4242424242424242"))
        self.assertFalse(luhn_is_valid("4242424242424243"))
        order = self.create_order("online")

        invalid_number = self.client.post(
            f"/api/payments/{order.id}/pay/",
            self.card_data("4242424242424243"),
            format="json",
        )
        self.assertEqual(invalid_number.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("card_number", invalid_number.data)

        invalid_expiry = self.card_data("4242424242424242")
        invalid_expiry["expiry"] = "00/99"
        expiry_response = self.client.post(
            f"/api/payments/{order.id}/pay/", invalid_expiry, format="json"
        )
        self.assertEqual(expiry_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("expiry", expiry_response.data)

        invalid_cvv = self.card_data("4242424242424242")
        invalid_cvv["cvv"] = "12"
        cvv_response = self.client.post(
            f"/api/payments/{order.id}/pay/", invalid_cvv, format="json"
        )
        self.assertEqual(cvv_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cvv", cvv_response.data)

    def test_test_card_outcomes_and_retry_after_failure(self):
        order = self.create_order("online")

        declined = self.pay_order(order, "4000000000000002")
        self.assertEqual(declined.status_code, status.HTTP_200_OK)
        self.assertEqual(declined.data["status"], "failed")
        self.assertEqual(declined.data["failure_reason"], "Card declined")
        order.refresh_from_db()
        self.assertEqual(order.status, "pending")

        insufficient = self.pay_order(order, "4000000000009995")
        self.assertEqual(insufficient.data["status"], "failed")
        self.assertEqual(insufficient.data["failure_reason"], "Insufficient funds")

        succeeded = self.pay_order(order, "4242424242424242")
        self.assertEqual(succeeded.data["status"], "paid")
        self.assertEqual(succeeded.data["card_brand"], "visa")
        self.assertEqual(succeeded.data["card_last4"], "4242")
        order.refresh_from_db()
        self.assertEqual(order.status, "confirmed")

        other_valid_order = self.create_order("online")
        other_valid = self.pay_order(other_valid_order, "4111111111111111")
        self.assertEqual(other_valid.data["status"], "paid")

    def test_paid_order_payment_is_idempotent(self):
        order = self.create_order("online")
        first = self.pay_order(order, "4242424242424242")
        transaction_id = first.data["transaction_id"]
        paid_at = first.data["paid_at"]

        second = self.pay_order(order, "4000000000000002")

        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(second.data["status"], "paid")
        self.assertEqual(second.data["transaction_id"], transaction_id)
        self.assertEqual(second.data["paid_at"], paid_at)
        self.assertEqual(Payment.objects.filter(order=order).count(), 1)

    def test_only_order_owner_can_pay_and_staff_cannot_pay(self):
        order = self.create_order("online")
        self.client.force_authenticate(user=self.other_customer)
        other_customer_response = self.pay_order(order, "4242424242424242")
        self.assertEqual(other_customer_response.status_code, status.HTTP_404_NOT_FOUND)

        self.client.force_authenticate(user=self.manager)
        manager_response = self.pay_order(order, "4242424242424242")
        self.assertEqual(manager_response.status_code, status.HTTP_403_FORBIDDEN)
        payment = Payment.objects.get(order=order)
        self.assertEqual(payment.status, "pending")

    def test_unpaid_online_order_cannot_be_confirmed_by_staff(self):
        order = self.create_order("online")
        self.client.force_authenticate(user=self.manager)

        response = self.client.post(
            f"/api/orders/{order.id}/status/",
            {"status": "confirmed"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        order.refresh_from_db()
        self.assertEqual(order.status, "pending")

    def test_card_number_is_not_persisted_or_returned(self):
        order = self.create_order("online")
        card_number = "4242424242424242"
        card_data = self.card_data(card_number)
        card_data["cvv"] = "987"
        card_data["cardholder_name"] = "PRIVATE NAME"
        response = self.client.post(
            f"/api/payments/{order.id}/pay/", card_data, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn(card_number, response.content.decode())
        payment = Payment.objects.get(order=order)
        self.assertEqual(payment.card_last4, "4242")
        self.assertEqual(payment.card_brand, "visa")
        self.assertNotIn(card_number, repr(payment.__dict__))
        self.assertNotIn("987", response.content.decode())
        self.assertNotIn("PRIVATE NAME", repr(payment.__dict__))
        self.assertNotIn("987", repr(payment.__dict__))
        self.assertNotIn("PRIVATE NAME", response.content.decode())

    def test_receipt_permissions_and_masked_card_metadata(self):
        order = self.create_order("online")
        self.pay_order(order, "4242424242424242")
        payment = Payment.objects.get(order=order)

        own_receipt = self.client.get(f"/api/payments/{payment.id}/receipt/")
        self.assertEqual(own_receipt.status_code, status.HTTP_200_OK)
        self.assertEqual(own_receipt.data["order_number"], order.order_number)
        self.assertEqual(own_receipt.data["card_last4"], "4242")

        self.client.force_authenticate(user=self.other_customer)
        private_receipt = self.client.get(f"/api/payments/{payment.id}/receipt/")
        self.assertEqual(private_receipt.status_code, status.HTTP_404_NOT_FOUND)

        self.client.force_authenticate(user=self.manager)
        manager_receipt = self.client.get(f"/api/payments/{payment.id}/receipt/")
        self.assertEqual(manager_receipt.status_code, status.HTTP_200_OK)

    def test_cash_payment_requires_delivery_confirmation(self):
        order = self.create_order("cash")
        payment = Payment.objects.get(order=order)
        self.assertEqual(payment.status, "pending")
        order.delivery_person = self.courier
        order.save(update_fields=["delivery_person"])
        self.client.force_authenticate(user=self.courier)

        early = self.client.post(f"/api/payments/{payment.id}/confirm-cash/")
        self.assertEqual(early.status_code, status.HTTP_400_BAD_REQUEST)
        payment.refresh_from_db()
        self.assertEqual(payment.status, "pending")

        order.status = "delivered"
        order.save(update_fields=["status"])
        confirmed = self.client.post(f"/api/payments/{payment.id}/confirm-cash/")
        self.assertEqual(confirmed.status_code, status.HTTP_200_OK)
        payment.refresh_from_db()
        self.assertEqual(payment.status, "paid")
        self.assertIsNotNone(payment.paid_at)

    def test_cancelled_online_order_requests_manager_refund(self):
        order = self.create_order("online")
        payment = Payment.objects.get(order=order)
        paid = self.pay_order(order, "4242424242424242")
        self.assertEqual(paid.status_code, status.HTTP_200_OK)
        self.client.force_authenticate(user=self.manager)
        cancelled = self.client.post(
            f"/api/orders/{order.id}/status/",
            {
                "status": "cancelled",
            },
            format="json",
        )
        self.assertEqual(cancelled.status_code, status.HTTP_200_OK)
        payment.refresh_from_db()
        self.assertEqual(payment.status, "refund_requested")

        self.client.force_authenticate(user=self.customer)
        forbidden = self.client.post(
            f"/api/payments/{payment.id}/refund/",
            {"reason": "Order cancelled"},
            format="json",
        )
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.manager)
        refunded = self.client.post(
            f"/api/payments/{payment.id}/refund/",
            {"reason": "Order was cancelled before preparation."},
            format="json",
        )
        self.assertEqual(refunded.status_code, status.HTTP_200_OK)
        payment.refresh_from_db()
        self.assertEqual(payment.status, "refunded")
        self.assertIsNotNone(payment.refunded_at)

        repeated = self.client.post(
            f"/api/payments/{payment.id}/refund/",
            {"reason": "Duplicate request"},
            format="json",
        )
        self.assertEqual(repeated.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cancelled_cash_order_does_not_remain_payable(self):
        order = self.create_order("cash")
        payment = Payment.objects.get(order=order)
        self.client.force_authenticate(user=self.customer)
        response = self.client.post(
            f"/api/orders/{order.id}/status/",
            {
                "status": "cancelled",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payment.refresh_from_db()
        self.assertEqual(payment.status, "cancelled")
