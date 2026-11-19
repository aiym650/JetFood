# food_delivery_system

## Feedback / Rating module

The Django backend includes review, photo, reply, report, rating aggregation and moderation models.

Run migrations:

```powershell
python manage.py migrate
```

Run reminder delivery (schedule every 10–15 minutes):

```powershell
python manage.py send_review_reminders
```

Run tests:

```powershell
python manage.py test reviews
```

Run the Angular frontend:

```powershell
cd frontend
npm start
```

Main API routes:

- `POST /api/orders/:orderId/review`
- `PUT|PATCH|DELETE /api/reviews/:id`
- `GET /api/restaurants/:id/reviews`
- `GET /api/restaurants/:id/rating`
- `GET /api/couriers/:id/rating`
- `POST /api/reviews/:id/reply`
- `POST /api/reviews/:id/report`
- `GET /api/admin/reviews?status=pending_moderation`
- `PATCH /api/admin/reviews/:id/status`