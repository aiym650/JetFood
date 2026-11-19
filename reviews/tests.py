from django.test import TestCase
from rest_framework.test import APIClient

from orders.models import MenuItem, Order
from restaurants.models import Restaurant
from users.models import User
from .models import Review


class ReviewApiTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(username="customer", password="pass", role="customer")
        self.courier = User.objects.create_user(username="courier", password="pass", role="delivery")
        self.restaurant = Restaurant.objects.create(
            name="Test Restaurant",
            address="Test 1",
            opening_time="09:00",
            closing_time="22:00",
        )
        self.menu_item = MenuItem.objects.create(
            name="Test Meal",
            category="Main",
            price="10.00",
            restaurant=self.restaurant,
        )
        self.order = Order.objects.create(
            order_number="TEST-1",
            customer=self.customer,
            delivery_person=self.courier,
            status="delivered",
            total_amount="10.00",
            delivery_address="Test address",
        )
        self.order.items.create(
            menu_item=self.menu_item,
            item_name="Test Meal",
            quantity=1,
            price_per_item="10.00",
            subtotal="10.00",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.customer)

    def payload(self):
        return {
            "restaurant_rating": 5,
            "food_rating": 4,
            "courier_rating": 5,
            "delivery_speed_rating": 4,
            "comment": "Excellent food and fast delivery",
        }

    def test_create_review_and_recalculate_rating(self):
        response = self.client.post(f"/api/orders/{self.order.id}/review", self.payload(), format="multipart")
        self.assertEqual(response.status_code, 201)
        self.restaurant.refresh_from_db()
        self.courier.refresh_from_db()
        self.assertEqual(self.restaurant.reviews_count, 1)
        self.assertEqual(self.courier.reviews_count, 1)
        self.assertEqual(float(self.restaurant.avg_rating), 4.5)

    def test_duplicate_review_is_rejected(self):
        first = self.client.post(f"/api/orders/{self.order.id}/review", self.payload(), format="multipart")
        second = self.client.post(f"/api/orders/{self.order.id}/review", self.payload(), format="multipart")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 409)

    def test_another_user_cannot_create_review(self):
        other = User.objects.create_user(username="other", password="pass", role="customer")
        self.client.force_authenticate(other)
        response = self.client.post(f"/api/orders/{self.order.id}/review", self.payload(), format="multipart")
        self.assertEqual(response.status_code, 403)

    def test_profanity_sends_review_to_moderation(self):
        payload = self.payload()
        payload["comment"] = "This is shit"
        response = self.client.post(f"/api/orders/{self.order.id}/review", payload, format="multipart")
        self.assertEqual(response.status_code, 201)
        review = Review.objects.get(order=self.order)
        self.assertEqual(review.status, Review.STATUS_PENDING)
