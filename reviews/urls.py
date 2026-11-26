from django.urls import path
from . import views

urlpatterns = [
    path("reviews/mine/", views.own_reviews),
    path("orders/<int:order_id>/review", views.create_review),
    path("reviews/<int:review_id>", views.update_review),
    path("reviews/<int:review_id>/", views.update_review),
    path("reviews/<int:review_id>/report", views.report_review),
    path("reviews/<int:review_id>/reply", views.reply_to_review),
    path("restaurants/<int:restaurant_id>/reviews", views.restaurant_reviews),
    path("restaurants/<int:restaurant_id>/rating", views.restaurant_rating),
    path("couriers/<int:courier_id>/rating", views.courier_rating),
    path("admin/reviews", views.admin_reviews),
    path("admin/reviews/<int:review_id>/status", views.admin_review_status),
]
