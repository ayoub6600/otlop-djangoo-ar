# Generated by Django 5.1.4 on 2025-01-01 01:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('otlop', '0002_user'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='deliveryperson',
            name='email',
        ),
        migrations.AddField(
            model_name='deliveryperson',
            name='due_amount',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=10, verbose_name='الرصيد المستحق'),
        ),
    ]
