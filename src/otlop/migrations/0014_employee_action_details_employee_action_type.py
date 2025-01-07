# Generated by Django 5.1.4 on 2025-01-06 01:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('otlop', '0013_employee_late_minutes_employee_loan_taken_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='action_details',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='employee',
            name='action_type',
            field=models.CharField(blank=True, choices=[('delay_penalty', 'خصم بسبب تأخير'), ('absence_penalty', 'خصم بسبب غياب'), ('other_penalty', 'خصم آخر'), ('loan', 'سلفة')], max_length=100, null=True),
        ),
    ]
