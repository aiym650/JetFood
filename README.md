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
### AI, moderation, hosted payments and cashback (2026-11-23)

Setup, migrations, financial rules, sandbox configuration and demonstration steps:
[COMMERCE_IMPLEMENTATION.txt](COMMERCE_IMPLEMENTATION.txt).
The 30 frontend acceptance scenarios and measured results are documented in
[FRONTEND_TEST_REPORT.md](FRONTEND_TEST_REPORT.md); AI questions and real-model
limitations are in [AI_SUPPORT_EVALUATION.txt](AI_SUPPORT_EVALUATION.txt).
Настройка тестовой оплаты с автоматическим `.env` и скрытым вводом ключа:
[PAYMENT_SETUP_RU.txt](PAYMENT_SETUP_RU.txt). Диагностика: `py manage.py check_payments`.
JetPoints: правила 5%/7%/10%, второй заказ +1000, журнал и миграция прежнего кэшбэка:
[JETPOINTS_IMPLEMENTATION.txt](JETPOINTS_IMPLEMENTATION.txt).
