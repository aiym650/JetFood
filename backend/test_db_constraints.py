"""
Proof that the database itself rejects wrong data (CHECK and UNIQUE constraints).
Run:  python manage.py test backend.test_db_constraints -v 2
Every test tries to insert BAD data and expects IntegrityError, and also shows that GOOD data is accepted.
"""

from datetime import date, time
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from analytics.models import PerformanceReport
from integration.models import ExternalIntegration, IntegrationLog
from orders.models import MenuItem, Order, OrderItem, RefundRequest
from payments.models import Payment
from restaurants.models import Restaurant
from users.models import DeliveryAddress, User


class DbConstraintTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("u1", "u1@x.com", "pw12345678")
        cls.rest = Restaurant.objects.create(
            name="R1", address="A", opening_time=time(9), closing_time=time(22)
        )
        cls.item = MenuItem.objects.create(
            name="Pizza", category="Main", price=10, restaurant=cls.rest
        )
        cls.order = Order.objects.create(
            order_number="ORD-1",
            customer=cls.user,
            total_amount=10,
            delivery_address="addr",
        )

    def rejected(self, make):
        """The database must refuse: IntegrityError. atomic() keeps the test transaction usable."""
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                make()

    # ------------------------------------------------------------ users
    def test_unique_email(self):
        self.rejected(lambda: User.objects.create_user("u2", "u1@x.com", "pw12345678"))

    def test_empty_email_allowed_many_times(self):
        User.objects.create_user("e1", "", "pw12345678")
        User.objects.create_user("e2", "", "pw12345678")

    def test_check_role_valid(self):
        self.rejected(
            lambda: User.objects.create_user(
                "u3", "u3@x.com", "pw12345678", role="hacker"
            )
        )

    def test_unique_one_default_address_per_user(self):
        DeliveryAddress.objects.create(
            user=self.user, address_line="a", city="c", is_default=True
        )
        self.rejected(
            lambda: DeliveryAddress.objects.create(
                user=self.user, address_line="b", city="c", is_default=True
            )
        )

    def test_many_non_default_addresses_allowed(self):
        for i in range(3):
            DeliveryAddress.objects.create(
                user=self.user, address_line=f"a{i}", city="c"
            )

    # ------------------------------------------------------------ restaurants
    def test_unique_restaurant_name(self):
        self.rejected(
            lambda: Restaurant.objects.create(
                name="R1", address="B", opening_time=time(9), closing_time=time(18)
            )
        )

    def test_check_opening_differs_from_closing(self):
        self.rejected(
            lambda: Restaurant.objects.create(
                name="R2", address="B", opening_time=time(9), closing_time=time(9)
            )
        )

    # ------------------------------------------------------------ menu items
    def test_check_menuitem_price_positive(self):
        self.rejected(
            lambda: MenuItem.objects.create(
                name="Free", category="X", price=0, restaurant=self.rest
            )
        )

    def test_check_menuitem_rating_range(self):
        self.rejected(
            lambda: MenuItem.objects.create(
                name="Bad",
                category="X",
                price=5,
                rating=Decimal("5.5"),
                restaurant=self.rest,
            )
        )

    def test_unique_menuitem_name_per_restaurant(self):
        self.rejected(
            lambda: MenuItem.objects.create(
                name="Pizza", category="X", price=5, restaurant=self.rest
            )
        )

    def test_same_menuitem_name_in_other_restaurant_allowed(self):
        other = Restaurant.objects.create(
            name="R3", address="C", opening_time=time(9), closing_time=time(20)
        )
        MenuItem.objects.create(
            name="Pizza", category="Main", price=7, restaurant=other
        )

    # ------------------------------------------------------------ orders
    def test_unique_order_number(self):
        self.rejected(
            lambda: Order.objects.create(
                order_number="ORD-1",
                customer=self.user,
                total_amount=5,
                delivery_address="x",
            )
        )

    def test_check_order_total_not_negative(self):
        self.rejected(
            lambda: Order.objects.create(
                order_number="ORD-2",
                customer=self.user,
                total_amount=-1,
                delivery_address="x",
            )
        )

    def test_check_order_status_valid(self):
        self.rejected(
            lambda: Order.objects.create(
                order_number="ORD-3",
                customer=self.user,
                total_amount=1,
                delivery_address="x",
                status="flying",
            )
        )

    def test_check_order_priority_valid(self):
        self.rejected(
            lambda: Order.objects.create(
                order_number="ORD-4",
                customer=self.user,
                total_amount=1,
                delivery_address="x",
                priority="whenever",
            )
        )

    def test_check_orderitem_quantity_positive(self):
        self.rejected(
            lambda: OrderItem.objects.create(
                order=self.order, item_name="Pizza", quantity=0, price_per_item=10
            )
        )

    def test_check_orderitem_price_not_negative(self):
        self.rejected(
            lambda: OrderItem.objects.create(
                order=self.order, item_name="Pizza", quantity=1, price_per_item=-5
            )
        )

    def test_valid_orderitem_accepted(self):
        item = OrderItem.objects.create(
            order=self.order, item_name="Pizza", quantity=2, price_per_item=10
        )
        self.assertEqual(item.subtotal, 20)

    # ------------------------------------------------------------ payments
    def test_unique_payment_per_order(self):
        Payment.objects.create(order=self.order, method="cash", amount=10)
        self.rejected(
            lambda: Payment.objects.create(order=self.order, method="cash", amount=10)
        )

    def test_check_payment_amount_not_negative(self):
        self.rejected(
            lambda: Payment.objects.create(order=self.order, method="cash", amount=-1)
        )

    def test_check_payment_method_valid(self):
        self.rejected(
            lambda: Payment.objects.create(
                order=self.order, method="bitcoin", amount=10
            )
        )

    def test_check_payment_status_valid(self):
        self.rejected(
            lambda: Payment.objects.create(
                order=self.order, method="cash", amount=10, status="lost"
            )
        )

    def test_check_payment_failed_status_accepted(self):
        payment = Payment.objects.create(
            order=self.order, method="online", amount=10, status="failed"
        )
        self.assertEqual(payment.status, "failed")

    def test_check_paid_payment_needs_paid_at(self):
        self.rejected(
            lambda: Payment.objects.create(
                order=self.order, method="online", amount=10, status="paid"
            )
        )
        Payment.objects.create(
            order=self.order,
            method="online",
            amount=10,
            status="paid",
            paid_at=timezone.now(),
        )

    def test_unique_transaction_id(self):
        o2 = Order.objects.create(
            order_number="ORD-5",
            customer=self.user,
            total_amount=1,
            delivery_address="x",
        )
        Payment.objects.create(
            order=self.order,
            method="online",
            amount=10,
            transaction_id="SIM-1",
            status="paid",
            paid_at=timezone.now(),
        )
        self.rejected(
            lambda: Payment.objects.create(
                order=o2,
                method="online",
                amount=1,
                transaction_id="SIM-1",
                status="paid",
                paid_at=timezone.now(),
            )
        )

    # ------------------------------------------------------------ refund requests
    def test_one_pending_refund_request_per_order(self):
        RefundRequest.objects.create(
            order=self.order,
            requested_by=self.user,
            request_type="cancel",
            reason_text="Please cancel this order.",
        )
        self.rejected(
            lambda: RefundRequest.objects.create(
                order=self.order,
                requested_by=self.user,
                request_type="cancel",
                reason_text="I still want to cancel this order.",
            )
        )

    def test_resolved_request_allows_a_new_pending_request(self):
        manager = User.objects.create_user("manager", "manager@example.com", "pw12345678", role="manager")
        previous = RefundRequest.objects.create(
            order=self.order,
            requested_by=self.user,
            request_type="cancel",
            reason_text="Please cancel this order.",
        )
        previous.status = "rejected"
        previous.decided_by = manager
        previous.decided_at = timezone.now()
        previous.decision_note = "The order is already being delivered."
        previous.save()

        current = RefundRequest.objects.create(
            order=self.order,
            requested_by=self.user,
            request_type="cancel",
            reason_text="I still want to cancel this order.",
        )
        self.assertEqual(current.status, "pending")

    def test_refund_request_checks_reject_invalid_values(self):
        def create(**overrides):
            values = {
                "order": self.order,
                "requested_by": self.user,
                "request_type": "cancel",
                "reason_text": "Please cancel this order.",
            }
            values.update(overrides)
            RefundRequest.objects.create(**values)

        self.rejected(lambda: create(request_type="invalid"))
        self.rejected(lambda: create(status="invalid"))
        self.rejected(lambda: create(reason_text="Too short"))
        self.rejected(lambda: create(reason_category="missing_items"))
        self.rejected(lambda: create(status="approved", refund_amount="1.00"))
        self.rejected(lambda: create(refund_amount="1.00"))
        self.rejected(lambda: create(refund_amount="-1.00"))

    def test_approved_request_requires_complete_decision_data(self):
        manager = User.objects.create_user("manager", "manager@example.com", "pw12345678", role="manager")
        self.rejected(lambda: RefundRequest.objects.create(
            order=self.order,
            requested_by=self.user,
            request_type="refund",
            reason_category="missing_items",
            reason_text="Some items were missing.",
            status="approved",
            refund_amount="5.00",
        ))

        request = RefundRequest.objects.create(
            order=self.order,
            requested_by=self.user,
            request_type="refund",
            reason_category="missing_items",
            reason_text="Some items were missing.",
            status="approved",
            decided_by=manager,
            decided_at=timezone.now(),
            refund_amount="5.00",
        )
        self.assertEqual(request.status, "approved")

    # ------------------------------------------------------------ analytics
    def test_check_report_end_after_start(self):
        self.rejected(
            lambda: PerformanceReport.objects.create(
                period="daily", start_date=date(2026, 1, 10), end_date=date(2026, 1, 1)
            )
        )

    def test_check_report_counters_not_negative(self):
        self.rejected(
            lambda: PerformanceReport.objects.create(
                period="daily",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 1),
                total_orders=-5,
            )
        )

    def test_unique_report_period(self):
        PerformanceReport.objects.create(
            period="daily", start_date=date(2026, 1, 1), end_date=date(2026, 1, 1)
        )
        self.rejected(
            lambda: PerformanceReport.objects.create(
                period="daily", start_date=date(2026, 1, 1), end_date=date(2026, 1, 1)
            )
        )

    # ------------------------------------------------------------ integration
    def test_unique_integration_name(self):
        ExternalIntegration.objects.create(
            name="Maps", integration_type="mapping_service", api_endpoint="http://a.kz"
        )
        self.rejected(
            lambda: ExternalIntegration.objects.create(
                name="Maps",
                integration_type="mapping_service",
                api_endpoint="http://b.kz",
            )
        )

    def test_check_integration_status_valid(self):
        self.rejected(
            lambda: ExternalIntegration.objects.create(
                name="X",
                integration_type="mapping_service",
                api_endpoint="http://a.kz",
                status="broken",
            )
        )

    def test_check_log_status_code_range(self):
        integ = ExternalIntegration.objects.create(
            name="Y", integration_type="mapping_service", api_endpoint="http://a.kz"
        )
        IntegrationLog.objects.create(
            integration=integ, level="info", message="ok", status_code=200
        )
        IntegrationLog.objects.create(
            integration=integ, level="info", message="no code"
        )
        self.rejected(
            lambda: IntegrationLog.objects.create(
                integration=integ, level="info", message="bad", status_code=999
            )
        )
