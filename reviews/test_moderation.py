from .tests import ReviewApiTests
from .models import Review, ReviewDecision
from .policy import decide, screen
from users.models import User


from django.test import TestCase


class ModerationTests(TestCase):
    setUp = ReviewApiTests.setUp
    payload = ReviewApiTests.payload
    def test_normal_negative_feedback_is_published(self):
        status, _ = screen('The food was cold and delivery was bad.')
        self.assertEqual(status, Review.STATUS_PUBLISHED)

    def test_links_personal_information_threats_and_discrimination(self):
        for text in ['Visit https://spam.example for free money', 'Call me +77011234567 please', 'All people are inferior', 'I will kill you when you arrive']:
            self.assertNotEqual(screen(text)[0], Review.STATUS_PUBLISHED)

    def test_text_length_and_fractional_rating_are_rejected(self):
        for updates in [{'comment': 'short'}, {'comment': 'a'*1001}, {'food_rating': 2.5}]:
            response = self.client.post(f'/api/orders/{self.order.pk}/review', {**self.payload(), **updates}, format='json')
            self.assertEqual(response.status_code, 400, response.data)

    def test_edit_hides_published_version_and_recalculates_rating(self):
        response = self.client.post(f'/api/orders/{self.order.pk}/review', self.payload(), format='json')
        review_id = response.data['id']
        edited = self.client.patch(f'/api/reviews/{review_id}', {'comment': 'The food was cold and not tasty.'}, format='json')
        self.assertEqual(edited.status_code, 200)
        self.assertEqual(edited.data['status'], Review.STATUS_PENDING)
        self.restaurant.refresh_from_db()
        self.assertEqual(self.restaurant.reviews_count, 0)
        self.assertEqual(ReviewDecision.objects.filter(review_id=review_id).count(), 2)

    def test_other_user_cannot_edit_and_own_list_is_private(self):
        response = self.client.post(f'/api/orders/{self.order.pk}/review', self.payload(), format='json')
        self.client.force_authenticate(User.objects.create_user(username='foreign-reviewer'))
        self.assertEqual(self.client.patch(f"/api/reviews/{response.data['id']}", {'comment': 'Changed by another person'}, format='json').status_code, 403)
        self.assertEqual(self.client.get('/api/reviews/mine/').data, [])

    def test_rejection_reason_and_history_then_author_correction(self):
        response = self.client.post(f'/api/orders/{self.order.pk}/review', self.payload(), format='json')
        review = Review.objects.get(pk=response.data['id'])
        decide(review.pk, Review.STATUS_HIDDEN, 'Remove the private phone number.', self.customer)
        self.assertIn('private phone', self.client.get('/api/reviews/mine/').data[0]['moderation_reason'])
        edited = self.client.patch(f'/api/reviews/{review.pk}', {'comment': 'The meal was cold but the courier was kind.'}, format='json')
        self.assertEqual(edited.data['status'], Review.STATUS_PENDING)

    def test_moderation_outage_keeps_pending(self):
        from django.test import override_settings
        with override_settings(REVIEW_MODERATION_PROVIDER='unavailable'):
            self.assertEqual(screen('A reasonable and useful review.')[0], Review.STATUS_PENDING)

    def test_old_moderation_decision_cannot_publish_a_revised_text(self):
        response = self.client.post(f'/api/orders/{self.order.pk}/review', self.payload(), format='json')
        old_version = response.data['updated_at']
        self.client.patch(f"/api/reviews/{response.data['id']}", {'comment': 'Revised review text to moderate again.'}, format='json')
        admin = User.objects.create_user(username='review-admin', role='admin')
        self.client.force_authenticate(admin)
        decision = self.client.patch(f"/api/admin/reviews/{response.data['id']}/status", {'status': 'published', 'updated_at': old_version}, format='json')
        self.assertEqual(decision.status_code, 409)
        self.assertEqual(Review.objects.get(pk=response.data['id']).status, Review.STATUS_PENDING)
