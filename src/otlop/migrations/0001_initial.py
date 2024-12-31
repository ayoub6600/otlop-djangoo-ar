# Generated by Django 5.1.4 on 2024-12-30 12:24

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='DeliveryPerson',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='اسم المندوب')),
                ('phone_number', models.CharField(max_length=15, unique=True, verbose_name='رقم الهاتف')),
                ('email', models.EmailField(blank=True, max_length=254, null=True, unique=True, verbose_name='البريد الإلكتروني')),
                ('vehicle_type', models.CharField(blank=True, max_length=50, null=True, verbose_name='نوع المركبة')),
                ('license_number', models.CharField(max_length=50, unique=True, verbose_name='رقم الرخصة')),
                ('percentage', models.DecimalField(decimal_places=2, default=10.0, max_digits=5, verbose_name='نسبة السائق')),
                ('total_paid', models.DecimalField(decimal_places=2, default=0.0, max_digits=10, verbose_name='إجمالي المدفوع')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإضافة')),
            ],
            options={
                'verbose_name': 'مندوب التوصيل',
                'verbose_name_plural': 'مندوبو التوصيل',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('customer_name', models.CharField(max_length=100, verbose_name='اسم الزبون')),
                ('customer_area', models.CharField(blank=True, max_length=100, null=True, verbose_name='منطقة الزبون')),
                ('restaurant_name', models.CharField(blank=True, max_length=100, null=True, verbose_name='اسم المطعم')),
                ('restaurant_area', models.CharField(blank=True, max_length=100, null=True, verbose_name='منطقة المطعم')),
                ('delivery_price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='سعر التوصيل')),
                ('order_price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='سعر الطلب')),
                ('notes', models.TextField(blank=True, null=True, verbose_name='ملاحظات')),
                ('order_details', models.TextField(blank=True, null=True, verbose_name='تفاصيل الطلب')),
                ('delivery_status', models.CharField(choices=[('Pending', 'Pending'), ('Delivered', 'Delivered'), ('Cancelled', 'Cancelled')], default='Pending', max_length=20, verbose_name='حالة الطلب')),
                ('is_paid', models.BooleanField(default=False, verbose_name='مدفوع')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإضافة')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')),
                ('delivery_person', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='orders', to='otlop.deliveryperson', verbose_name='مندوب التوصيل')),
            ],
            options={
                'verbose_name': 'طلب',
                'verbose_name_plural': 'الطلبات',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='المبلغ')),
                ('date', models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الدفعة')),
                ('notes', models.TextField(blank=True, null=True, verbose_name='ملاحظات')),
                ('payment_method', models.CharField(choices=[('Cash', 'Cash'), ('Bank Transfer', 'Bank Transfer'), ('Other', 'Other')], default='Cash', max_length=20, verbose_name='طريقة الدفع')),
                ('driver', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='otlop.deliveryperson', verbose_name='مندوب التوصيل')),
            ],
            options={
                'verbose_name': 'دفعة',
                'verbose_name_plural': 'الدفعات',
                'ordering': ['-date'],
            },
        ),
    ]
