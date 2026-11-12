import secrets

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Create local demo accounts for admin, restaurant manager, and courier roles.'

    ACCOUNTS = [
        ('demo_admin', 'admin.demo@jetfood.local', 'admin'),
        ('demo_manager', 'manager.demo@jetfood.local', 'manager'),
        ('demo_courier', 'courier.demo@jetfood.local', 'delivery'),
    ]

    def handle(self, *args, **options):
        user_model = get_user_model()
        created_credentials = []
        for username, email, role in self.ACCOUNTS:
            user = user_model.objects.filter(username=username).first()
            if user:
                if user.role != role or (role == 'admin' and not user.is_superuser):
                    raise CommandError(
                        f'{username} already exists with a different role or privilege level.'
                    )
                continue

            password = secrets.token_urlsafe(18)
            if role == 'admin':
                user_model.objects.create_superuser(
                    username=username,
                    email=email,
                    password=password,
                    role=role,
                )
            else:
                user_model.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    role=role,
                )
            created_credentials.append((username, role, password))

        if created_credentials:
            self.stdout.write(self.style.SUCCESS('New demo accounts (save these passwords now):'))
            for username, role, password in created_credentials:
                self.stdout.write(f'{role}: {username} / {password}')
        else:
            self.stdout.write('All three demo accounts already exist; no credentials were changed.')
