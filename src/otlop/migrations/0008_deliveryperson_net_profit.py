# Generated by Django 5.1.4 on 2025-01-02 01:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('otlop', '0007_delete_systemsettings'),
    ]

    operations = [
        migrations.AddField(
            model_name='deliveryperson',
            name='net_profit',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=10, verbose_name='صافي الربح'),
        ),
    ]
