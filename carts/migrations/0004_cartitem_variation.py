# Generated by Django 5.1.5 on 2025-05-06 14:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('carts', '0003_alter_cart_id_alter_cartitem_id'),
        ('store', '0002_alter_product_id_variation'),
    ]

    operations = [
        migrations.AddField(
            model_name='cartitem',
            name='Variation',
            field=models.ManyToManyField(blank=True, to='store.variation'),
        ),
    ]
