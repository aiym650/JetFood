import re
import threading
import unicodedata
from django.db import transaction


PROFANITY = {
    "бля", "бляд", "сука", "сукин", "хуйн", "хуй", "пизд", "мудак", "дерьмо",
    "shit", "fuck", "bitch", "asshole", "damn", "loser",
    "жах", "отбасы", "алаяқ", "сокыр",
}
POSITIVE = {"good", "great", "excellent", "love", "awesome", "хорош", "отлич", "супер", "вкусн", "рахмет", "жақсы"}
NEGATIVE = {"bad", "terrible", "awful", "hate", "плох", "ужас", "мерз", "жаман", "нашар", "хуже"}


def normalize_text(text):
    text = unicodedata.normalize("NFKC", text or "").lower()
    text = text.replace("ё", "е").replace("ү", "у").replace("ұ", "у").replace("і", "и").replace("ң", "н").replace("ғ", "г").replace("қ", "к").replace("ә", "а").replace("ө", "о").replace("һ", "h")
    text = re.sub(r"[^a-zа-я0-9\s]", " ", text)
    return " ".join(text.split())


def contains_profanity(text):
    normalized = normalize_text(text)
    return any(word in normalized for word in PROFANITY)


def detect_sentiment(text):
    normalized = normalize_text(text)
    positive = sum(normalized.count(word) for word in POSITIVE)
    negative = sum(normalized.count(word) for word in NEGATIVE)
    if positive > negative:
        return "positive"
    if negative > positive:
        return "negative"
    return "neutral"


def analyze_sentiment_async(review_id):
    def run():
        from .models import Review
        try:
            review = Review.objects.filter(pk=review_id).first()
            if not review:
                return
            sentiment = detect_sentiment(review.comment)
            with transaction.atomic():
                review.sentiment = sentiment
                review.save(update_fields=["sentiment", "updated_at"])
        except Exception:
            return

    threading.Thread(target=run, daemon=True).start()
