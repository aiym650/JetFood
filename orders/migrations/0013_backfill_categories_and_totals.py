from django.db import migrations


def backfill(apps, schema_editor):
    Item = apps.get_model('orders', 'MenuItem')
    Category = apps.get_model('restaurants', 'MenuCategory')
    Order = apps.get_model('orders', 'Order')
    db = schema_editor.connection.alias
    for item in Item.objects.using(db).filter(menu_category__isnull=True).iterator():
        category, _ = Category.objects.using(db).get_or_create(restaurant_id=item.restaurant_id, name=item.category or 'Menu')
        Item.objects.using(db).filter(pk=item.pk).update(menu_category_id=category.pk)
    from django.db.models import F
    Order.objects.using(db).update(items_amount=F('total_amount'))


class Migration(migrations.Migration):
    dependencies = [('orders', '0012_promocode_promoredemption_menuitem_demo_key_and_more')]
    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
