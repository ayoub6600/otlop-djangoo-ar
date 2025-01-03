from django.db import models
from django.db.models import Sum

# نموذج الطلب
class Order(models.Model):
    DELIVERY_STATUS_CHOICES = [
        ('Pending', 'Pending'),        # قيد الانتظار
        ('Delivered', 'Delivered'),    # تم التوصيل
        ('Cancelled', 'Cancelled'),    # ملغاة
    ]

    customer_name = models.CharField(max_length=100, verbose_name="اسم الزبون")
    customer_area = models.CharField(max_length=100, null=True, blank=True, verbose_name="منطقة الزبون")
    restaurant_name = models.CharField(max_length=100, null=True, blank=True, verbose_name="اسم المطعم")
    restaurant_area = models.CharField(max_length=100, null=True, blank=True, verbose_name="منطقة المطعم")
    delivery_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        verbose_name="سعر التوصيل"
    )
    order_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        verbose_name="سعر الطلب"
    )
    notes = models.TextField(null=True, blank=True, verbose_name="ملاحظات")
    order_details = models.TextField(null=True, blank=True, verbose_name="تفاصيل الطلب")
    delivery_person = models.ForeignKey(
        'DeliveryPerson',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="مندوب التوصيل",
        related_name="orders"
    )
    delivery_status = models.CharField(
        max_length=20,
        choices=DELIVERY_STATUS_CHOICES,
        default='Pending',
        verbose_name="حالة الطلب"
    )
    is_paid = models.BooleanField(default=False, verbose_name="مدفوع")  # حالة الدفع
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإضافة")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")

    class Meta:
        verbose_name = "طلب"
        verbose_name_plural = "الطلبات"
        ordering = ['-created_at']  # عرض الطلبات بترتيب زمني تنازلي

    def __str__(self):
        return f"Order #{self.id} - {self.customer_name}"


# نموذج مندوب التوصيل
class DeliveryPerson(models.Model):
    name = models.CharField(max_length=100, verbose_name="اسم المندوب")
    phone_number = models.CharField(max_length=15, unique=True, verbose_name="رقم الهاتف")
    vehicle_type = models.CharField(max_length=50, null=True, blank=True, verbose_name="نوع المركبة")
    license_number = models.CharField(max_length=50, unique=True, verbose_name="رقم الرخصة")
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=10.00, verbose_name="نسبة السائق")
    total_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="إجمالي المدفوع")
    due_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.0, verbose_name="الرصيد المستحق")    
    total_profit = models.DecimalField(max_digits=10, decimal_places=2, default=0.0, verbose_name="صافي الربح") 
    net_profit = models.DecimalField(max_digits=10, decimal_places=2, default=0.0, verbose_name="صافي الربح")  # الحقل الجديد
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإضافة")

    class Meta:
        verbose_name = "مندوب التوصيل"
        verbose_name_plural = "مندوبو التوصيل"
        ordering = ['name']
    
    def __str__(self):
        return self.name

    def calculate_due_amount(self):
        """احسب المستحقات الحالية للسائق بناءً على الطلبات"""
        delivered_orders = self.orders.filter(delivery_status='Delivered')
        total_earnings = delivered_orders.aggregate(Sum('delivery_price'))['delivery_price__sum'] or 0
        due_amount = (total_earnings * self.percentage / 100) - self.total_paid
        return due_amount

    def calculate_profit(self):
        """احسب صافي الربح من السائق"""
        delivered_orders = self.orders.filter(delivery_status='Delivered')
        total_revenue = delivered_orders.aggregate(Sum('delivery_price'))['delivery_price__sum'] or 0
        profit = (total_revenue * (100 - self.percentage)) / 100
        return profit


# نموذج الدفعات
class Payment(models.Model):
    driver = models.ForeignKey(DeliveryPerson, on_delete=models.CASCADE, verbose_name="مندوب التوصيل")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="المبلغ")
    date = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الدفعة")
    notes = models.TextField(null=True, blank=True, verbose_name="ملاحظات")
    PAYMENT_METHOD_CHOICES = [
        ('Cash', 'نقدي'),
        ('Bank Transfer', 'تحويل بنكي'),
        ('Other', 'أخرى'),
    ]
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='Cash',
        verbose_name="طريقة الدفع"
    )

    class Meta:
        verbose_name = "دفعة"
        verbose_name_plural = "الدفعات"
        ordering = ['-date']

    def __str__(self):
        return f"دفعة بقيمة {self.amount} للسائق {self.driver.name}"


# نموذج المستخدم
class User(models.Model):
    username = models.CharField(max_length=50, unique=True, verbose_name="اسم المستخدم")
    email = models.EmailField(unique=True, verbose_name="البريد الإلكتروني")
    password = models.CharField(max_length=255, verbose_name="كلمة المرور")
    is_admin = models.BooleanField(default=False, verbose_name="مشرف النظام")

    class Meta:
        verbose_name = "مستخدم"
        verbose_name_plural = "المستخدمون"
        ordering = ['username']

    def __str__(self):
        return self.username