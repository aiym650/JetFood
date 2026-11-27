from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('support', '0006_supportmessage_source')]
    operations = [migrations.AlterField(
        model_name='supportmessage', name='source',
        field=models.CharField(blank=True, choices=[('ai', 'AI provider'), ('catalog', 'JetFood catalog'), ('facts', 'Verified JetFood data')], default='', max_length=16),
    )]
