# Generated by Django 5.1.4 on 2025-01-06 22:36

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('otlop', '0021_remove_employeeaction_date_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='employee',
            name='discount_amount',
        ),
        migrations.RemoveField(
            model_name='employee',
            name='loan_taken_date',
        ),
        migrations.RemoveField(
            model_name='employee',
            name='phone',
        ),
        migrations.RemoveField(
            model_name='employee',
            name='position',
        ),
    ]
