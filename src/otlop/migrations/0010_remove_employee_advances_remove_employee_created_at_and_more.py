# Generated by Django 5.1.4 on 2025-01-06 00:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('otlop', '0009_employee'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='employee',
            name='advances',
        ),
        migrations.RemoveField(
            model_name='employee',
            name='created_at',
        ),
        migrations.RemoveField(
            model_name='employee',
            name='deductions',
        ),
        migrations.RemoveField(
            model_name='employee',
            name='late_minutes',
        ),
        migrations.RemoveField(
            model_name='employee',
            name='late_penalty_per_minute',
        ),
        migrations.RemoveField(
            model_name='employee',
            name='net_salary',
        ),
        migrations.AddField(
            model_name='employee',
            name='employee_id',
            field=models.CharField(default='0000', max_length=50, unique=True),
        ),
        migrations.AddField(
            model_name='employee',
            name='phone',
            field=models.CharField(default='0000000000', max_length=20),
        ),
        migrations.AddField(
            model_name='employee',
            name='tasks',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='employee',
            name='name',
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name='employee',
            name='position',
            field=models.CharField(max_length=255),
        ),
    ]
