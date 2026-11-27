from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('support', '0005_refresh_default_payment_faq')]
    operations = [migrations.AddField(
        model_name='supportmessage', name='source',
        field=models.CharField(blank=True, choices=[('ai', 'AI provider'), ('catalog', 'JetFood catalog')], default='', max_length=16),
    )]
