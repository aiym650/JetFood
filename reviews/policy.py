"""Conservative local screening, not a guarantee of detecting abusive content."""
import re
import unicodedata
from django.conf import settings
from django.db import transaction
from .models import Review, ReviewDecision
from .services import recalculate_rating


def screen(text, edited=False):
    text = unicodedata.normalize('NFKC', text).casefold()
    if re.search(r'\b(kill you|i will kill|убью тебя|я тебя убью|смерть всем)\b', text):
        return Review.STATUS_HIDDEN, 'Threats are not allowed. Remove the threat and submit a corrected review.'
    if re.search(r'\b(fuck\w*|shit|bitch\w*|asshole\w*|сука|суки|бляд\w*|пизд\w*|хуй\w*|мудак\w*)\b', text):
        return Review.STATUS_PENDING, 'Possible abusive language. An administrator will review the text; you can edit it.'
    if re.search(r'https?://|www\.|\b\S+@\S+\.\S+|(?:\+?\d[ ()-]*){9,}|\b(buy now|free money|go back to your country|all .* are inferior|nigger\w*|faggot\w*)\b|\b(купи сейчас|все .* недолюди)\b', text):
        return Review.STATUS_PENDING, 'Possible spam, personal information or discriminatory language. Review required.'
    if re.search(r'(.)\1{7,}', text):
        return Review.STATUS_PENDING, 'Repeated content requires review.'
    # External moderation has no silent allow fallback. Local mode is explicitly heuristic.
    if settings.REVIEW_MODERATION_PROVIDER != 'local':
        return Review.STATUS_PENDING, 'External moderation is unavailable. Awaiting administrator review.'
    if edited:
        return Review.STATUS_PENDING, 'Edited review awaits administrator approval. The previous version is no longer public.'
    return Review.STATUS_PUBLISHED, 'Passed local screening.'


def record_decision(review, previous, reason, actor=None):
    ReviewDecision.objects.create(review=review, review_reference=review.pk,
        actor=actor, previous_status=previous, status=review.status, reason=reason, comment_snapshot=review.comment or '')


@transaction.atomic
def decide(review_id, status, reason, actor, expected_updated_at=None):
    review = Review.objects.select_for_update().get(pk=review_id)
    if expected_updated_at is not None:
        from django.utils.dateparse import parse_datetime
        from rest_framework.exceptions import APIException
        expected = parse_datetime(str(expected_updated_at))
        if expected != review.updated_at:
            conflict = APIException('Review changed. Reload it before making a moderation decision.')
            conflict.status_code = 409
            raise conflict
    previous = review.status
    review.status, review.moderation_reason = status, reason
    review.save(update_fields=['status', 'moderation_reason', 'updated_at'])
    record_decision(review, previous, reason, actor)
    recalculate_rating(review.restaurant_id, review.courier_id)
    return review
