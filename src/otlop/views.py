from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils.dateparse import parse_date
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse, Http404
import openpyxl
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import arabic_reshaper
from bidi.algorithm import get_display
import arabic_reshaper

import os
from pdf2image import convert_from_path


# استيراد النماذج
from .models import Order, DeliveryPerson, Payment, Employee, EmployeeAction
from .forms import EmployeeActionForm  # استيراد النموذج من forms.py

# استيراد النماذج والحقول المخصصة
from .forms import OrderForm, CustomUserCreationForm

# استيراد الأدوات الخاصة بالاستعلامات وحساب الإجماليات
from django.db.models import Sum, Count, Q, F
from django.db import models

# استيراد أدوات التعامل مع الأرقام العشرية
from decimal import Decimal, InvalidOperation
from django.contrib.auth.decorators import login_required



PASSWORD = "Ayoub@@1234"  # استبدل بكلمة المرور التي تريدها

# الصفحة الرئيسية
@login_required
def home(request):
    """
    عرض الصفحة الرئيسية للموقع
    """
    return render(request, 'otlop/index.html', {'title': 'Home'})

# لوحة التحكم (Dashboard)
@login_required
def dashboard(request):
    """
    عرض لوحة التحكم التي تحتوي على إحصائيات الطلبات والعوائد والمزيد.
    """
    start_date = request.GET.get('start_date')  # استلام تاريخ البدء من الاستعلام
    end_date = request.GET.get('end_date')  # استلام تاريخ الانتهاء من الاستعلام

    orders = Order.objects.all()  # جلب كل الطلبات
    if start_date:
        start_date = parse_date(start_date)  # تحويل تاريخ البدء
        orders = orders.filter(created_at__date__gte=start_date)  # تصفية الطلبات بتاريخ بدء أكبر
    if end_date:
        end_date = parse_date(end_date)  # تحويل تاريخ الانتهاء
        orders = orders.filter(created_at__date__lte=end_date)  # تصفية الطلبات بتاريخ انتهاء أصغر

    # تصنيف الطلبات حسب الحالة
    pending_orders = orders.filter(delivery_status='Pending')
    delivered_orders = orders.filter(delivery_status='Delivered')
    cancelled_orders = orders.filter(delivery_status='Cancelled')

    # حساب إجمالي الإيرادات
    total_revenue = delivered_orders.aggregate(Sum('delivery_price'))['delivery_price__sum'] or 0
    total_orders = orders.count()  # عدد الطلبات الكلي
    total_pending = pending_orders.count()  # عدد الطلبات المعلقة
    profit_percentage = 30  # نسبة الربح
    net_profit = (total_revenue * profit_percentage) / 100  # صافي الربح

    # استعلامات لأكثر المطاعم التي تم طلبها وأكثر السائقين نشاطاً
    most_requested_restaurants = (
        orders.values('restaurant_name')
        .annotate(order_count=Count('restaurant_name'))
        .order_by('-order_count')[:5]
    )

    most_active_drivers = (
        orders.values('delivery_person')
        .annotate(order_count=Count('delivery_person'))
        .order_by('-order_count')[:5]
    )

    show_sensitive_data = False
    if request.method == "POST":
        password = request.POST.get("password")
        if password == PASSWORD:
            show_sensitive_data = True  # إظهار البيانات الحساسة إذا كانت كلمة المرور صحيحة
        else:
            messages.error(request, "كلمة المرور غير صحيحة.")  # عرض رسالة خطأ إذا كانت كلمة المرور خاطئة

    context = {
        'pending_orders': pending_orders,
        'delivered_orders': delivered_orders,
        'cancelled_orders': cancelled_orders,
        'total_orders': total_orders if show_sensitive_data else "****",  # إخفاء البيانات الحساسة إذا كانت غير مخفية
        'total_pending': total_pending,
        'total_revenue': total_revenue if show_sensitive_data else "****",  # إخفاء الإيرادات إذا كانت غير مخفية
        'net_profit': net_profit if show_sensitive_data else "****",  # إخفاء الربح إذا كان غير مخفي
        'most_requested_restaurants': most_requested_restaurants,
        'most_active_drivers': most_active_drivers,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'otlop/dashboard.html', context)

# عرض الطلبات السابقة
def previous_orders(request):
    # الحصول على تواريخ البحث من الطلب
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # تصفية الطلبات بناءً على التاريخ إذا تم إدخال تواريخ
    orders = Order.objects.all()
    if start_date and end_date:
        orders = orders.filter(created_at__range=[start_date, end_date])

    context = {
        'orders': orders,
        'start_date': start_date,  # تمرير تاريخ البداية إلى القالب
        'end_date': end_date,      # تمرير تاريخ النهاية إلى القالب
    }
    return render(request, 'otlop/previous-orders.html', context)
# دالة لتعيين السائق لطلب معين
def assign_driver(request, order_id):
    """
    تعيين سائق لطلب معين.
    - جلب الطلب باستخدام order_id.
    - عرض قائمة السائقين المتاحين لتعيينهم.
    - تحديث الطلب بالسائق المختار.

    Args:
        request: طلب HTTP.
        order_id: رقم تعريف الطلب المراد تعيين السائق له.

    Returns:
        HTTP Response: يعرض صفحة تعيين السائق أو يعيد التوجيه للطلبات السابقة عند الحفظ.
    """
    # جلب الطلب من قاعدة البيانات أو عرض 404 إذا لم يتم العثور عليه
    order = get_object_or_404(Order, id=order_id)

    # جلب جميع السائقين من قاعدة البيانات
    drivers = DeliveryPerson.objects.all()

    if request.method == 'POST':
        # الحصول على معرّف السائق المختار من الطلب
        driver_id = request.POST.get('driver')
        # جلب السائق من قاعدة البيانات
        driver = get_object_or_404(DeliveryPerson, id=driver_id)
        # تعيين السائق للطلب
        order.delivery_person = driver
        order.save()
        # رسالة نجاح
        messages.success(request, f"تم تعيين السائق {driver.name} للطلب.")
        # إعادة التوجيه إلى صفحة الطلبات السابقة
        return redirect('previous_orders')

    # عرض صفحة تعيين السائق
    return render(request, 'otlop/assign_driver.html', {'order': order, 'drivers': drivers})
def search_previous_orders(request):
    query = request.GET.get('q', '').strip()
    filter_by = request.GET.get('filter_by', '')  # الفئة المختارة للبحث
    orders = []

    if query:
        # البحث المخصص حسب الفئة
        if filter_by == 'customer_name':
            orders = Order.objects.filter(customer_name__icontains=query)
        elif filter_by == 'restaurant_name':
            orders = Order.objects.filter(restaurant_name__icontains=query)
        elif filter_by == 'driver_name':
            orders = Order.objects.filter(delivery_person__name__icontains=query)
        elif filter_by == 'date':
            orders = Order.objects.filter(created_at__icontains=query)
        else:
            # البحث العام في كل الحقول
            orders = Order.objects.filter(
                Q(customer_name__icontains=query) |
                Q(restaurant_name__icontains=query) |
                Q(order_details__icontains=query) |
                Q(delivery_person__name__icontains=query)
            )

    context = {
        'orders': orders,
        'query': query,
        'filter_by': filter_by,
    }
    return render(request, 'otlop/search_previous_orders.html', context)
# تعديل الطلب
def edit_order(request, order_id):
    """
    تعديل الطلب القائم.
    """
    order = get_object_or_404(Order, id=order_id)
    drivers = DeliveryPerson.objects.all()

    if request.method == 'POST':
        order.customer_name = request.POST.get('customer_name', order.customer_name)
        order.customer_area = request.POST.get('customer_area', order.customer_area)
        order.restaurant_name = request.POST.get('restaurant_name', order.restaurant_name)
        order.restaurant_area = request.POST.get('restaurant_area', order.restaurant_area)

        # معالجة الحقول الرقمية
        delivery_price = request.POST.get('delivery_price')
        order_price = request.POST.get('order_price')
        
        # تعيين القيم إلى None إذا كانت فارغة
        try:
            order.delivery_price = Decimal(delivery_price) if delivery_price else None
        except InvalidOperation:
            order.delivery_price = None

        try:
            order.order_price = Decimal(order_price) if order_price else None
        except InvalidOperation:
            order.order_price = None

        order.notes = request.POST.get('notes', order.notes)

        # تعيين السائق إذا تم اختياره
        delivery_person_id = request.POST.get('delivery_person')
        if delivery_person_id:
            order.delivery_person = get_object_or_404(DeliveryPerson, id=delivery_person_id)
        else:
            order.delivery_person = None

        order.save()
        messages.success(request, 'تم تحديث الطلب بنجاح!')
        return redirect('previous_orders')

    context = {
        'order': order,
        'drivers': drivers,
    }
    return render(request, 'otlop/edit-order.html', context)

# عرض قائمة السائقين
def drivers_list(request):
    """
    عرض قائمة بجميع السائقين مع دعم البحث.
    """
    query = request.GET.get('q')  # الحصول على نص البحث من المستخدم
    drivers = DeliveryPerson.objects.all()

    if query:
        # البحث عن السائقين باستخدام الاسم أو رقم الهاتف
        drivers = drivers.filter(Q(name__icontains=query) | Q(phone_number__icontains=query))

    # حساب المبالغ المستحقة للسائقين
    for driver in drivers:
        # حساب الطلبات المرتبطة بالسائق
        driver_orders = driver.orders.filter(delivery_status='Delivered')

        # حساب إجمالي الإيرادات للسائق
        driver_revenue = driver_orders.aggregate(Sum('delivery_price'))['delivery_price__sum'] or 0

        # حساب إجمالي المدفوعات للسائق
        driver_paid = driver.payment_set.aggregate(Sum('amount'))['amount__sum'] or 0

        # حساب نسبة الشركة من الإيرادات
        company_due_amount = (driver_revenue * (100 - driver.percentage)) / 100

        # خصم المدفوع من المبالغ المستحقة
        due_amount = company_due_amount - driver_paid

        # تعيين القيم المحسوبة للسائق
        driver.due_amount = due_amount if due_amount > 0 else 0  # التأكد من أن المبلغ المستحق ليس سالبًا
        driver.total_orders = driver_orders.count()  # حساب عدد الطلبات لكل سائق

    context = {
        'drivers': drivers,
        'query': query,  # إعادة نص البحث إلى القالب
    }
    return render(request, 'otlop/drivers_list.html', context)

# إضافة سائق جديد
def add_driver(request):
    """
    إضافة سائق جديد إلى النظام مع التحقق من الرمز السري.
    """
    admin_secret = "Ayoub@@1234"  # الرمز السري للمشرف (يمكن تغييره لاحقاً)

    if request.method == 'POST':
        # التحقق من الرمز السري
        secret_code = request.POST.get('secret_code')
        if secret_code != admin_secret:
            messages.error(request, 'رمز سري غير صحيح!')
            return HttpResponseForbidden("ليس لديك الصلاحية لإضافة سائق جديد.")

        # استلام البيانات المدخلة
        name = request.POST.get('name')
        phone_number = request.POST.get('phone_number')
        vehicle_type = request.POST.get('vehicle_type')
        license_number = request.POST.get('license_number')
        percentage = request.POST.get('percentage')

        # التحقق من البيانات المدخلة
        if not name or not phone_number or not license_number:
            messages.error(request, 'يرجى ملء جميع الحقول المطلوبة!')
            return redirect('add_driver')

        # التحقق من وجود سائق بنفس رقم الهاتف أو الرخصة
        if DeliveryPerson.objects.filter(phone_number=phone_number).exists():
            messages.error(request, 'يوجد سائق مسجل بنفس رقم الهاتف.')
            return redirect('add_driver')

        if DeliveryPerson.objects.filter(license_number=license_number).exists():
            messages.error(request, 'يوجد سائق مسجل بنفس رقم الرخصة.')
            return redirect('add_driver')

        # إنشاء السائق الجديد
        DeliveryPerson.objects.create(
            name=name,
            phone_number=phone_number,
            vehicle_type=vehicle_type,
            license_number=license_number,
            percentage=percentage
        )
        messages.success(request, 'تم إضافة السائق بنجاح!')
        return redirect('drivers_list')

    return render(request, 'otlop/add-driver.html')


def driver_details(request, driver_id):
    """
    عرض تفاصيل سائق معين مع حساب المبالغ المستحقة بنفس منطق DriverList.
    """
    driver = get_object_or_404(DeliveryPerson, id=driver_id)
    
    # الطلبات المرتبطة بالسائق
    driver_orders = driver.orders.filter(delivery_status='Delivered')

    # إجمالي الإيرادات للسائق
    driver_revenue = driver_orders.aggregate(Sum('delivery_price'))['delivery_price__sum'] or 0

    # إجمالي المدفوعات للسائق
    driver_paid = Payment.objects.filter(driver=driver).aggregate(Sum('amount'))['amount__sum'] or 0

    # حساب نسبة الشركة من الإيرادات
    company_due_amount = (driver_revenue * (100 - driver.percentage)) / 100

    # خصم المدفوع من المبالغ المستحقة
    due_amount = company_due_amount - driver_paid

    # التأكد من أن المبلغ المستحق ليس سالبًا
    due_amount = due_amount if due_amount > 0 else 0

    # حساب عدد الطلبات الموصلة والملغاة
    delivered_orders_count = driver_orders.count()
    cancelled_orders_count = driver.orders.filter(delivery_status='Cancelled').count()

    context = {
        'driver': driver,
        'orders': driver_orders,
        'total_earnings': driver_revenue,
        'payments': Payment.objects.filter(driver=driver),
        'total_payments': driver_paid,
        'driver_profit': driver_revenue * driver.percentage / 100,  # أرباح السائق
        'delivered_orders_count': delivered_orders_count,
        'cancelled_orders_count': cancelled_orders_count,
        'due_amount': due_amount,  # المبالغ المستحقة للشركة
    }

    return render(request, 'otlop/driver-details.html', context)

def export_driver_details_to_excel(request, driver_id):
    # احصل على تفاصيل السائق والطلبات
    driver = get_object_or_404(DeliveryPerson, id=driver_id)
    orders = driver.orders.all()
    
    # إنشاء ملف Excel جديد
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = f"تفاصيل السائق {driver.name}"
    
    # كتابة رأس الجدول
    sheet.append(['اسم السائق', 'رقم الهاتف', 'نوع المركبة', 'إجمالي الطلبات', 'إجمالي العوائد', 'إجمالي المدفوعات', 'المبالغ المستحقة'])
    
    # كتابة بيانات السائق
    sheet.append([
        driver.name,
        driver.phone_number,
        driver.vehicle_type,
        orders.count(),
        sum(order.delivery_price or 0 for order in orders),
        sum(payment.amount or 0 for payment in driver.payment_set.all()),
        sum(order.delivery_price or 0 for order in orders) - sum(payment.amount or 0 for payment in driver.payment_set.all())
    ])
    
    # إضافة تفاصيل الطلبات
    sheet.append([])
    sheet.append(['تفاصيل الطلبات:'])
    sheet.append(['رقم الطلب', 'اسم العميل', 'سعر التوصيل', 'حالة الطلب', 'تاريخ الطلب'])
    
    for order in orders:
        sheet.append([
            order.id,
            order.customer_name,
            order.delivery_price or 0,
            order.delivery_status,
            order.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    # إعداد الاستجابة لتحميل الملف
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename=driver_{driver.id}_details.xlsx'
    
    workbook.save(response)
    return response



def export_driver_to_image(request, driver_id):
    # جلب تفاصيل السائق
    driver = get_object_or_404(DeliveryPerson, id=driver_id)
    orders = driver.orders.all()
    payments = Payment.objects.filter(driver=driver)

    # إجمالي الإيرادات والمدفوعات
    total_earnings = orders.aggregate(Sum('delivery_price'))['delivery_price__sum'] or 0
    total_payments = payments.aggregate(Sum('amount'))['amount__sum'] or 0
    driver_profit = total_earnings * driver.percentage / 100
    due_amount = total_earnings - total_payments
    delivered_orders_count = orders.filter(delivery_status='Delivered').count()
    cancelled_orders_count = orders.filter(delivery_status='Cancelled').count()

    # تسجيل الخط
    FONT_PATH = "/Users/ayoubbelhaj/Documents/projects/otlopdelivery/src/otlop/static/otlop/fonts/Tajawal-ExtraBold.ttf"
    pdfmetrics.registerFont(TTFont('Tajawal', FONT_PATH))

    # إنشاء ملف PDF مؤقت
    pdf_path = "temp_driver_details.pdf"
    pdf_canvas = canvas.Canvas(pdf_path, pagesize=letter)
    pdf_canvas.setFont("Tajawal", 14)

    # كتابة البيانات على PDF
    y_position = 750
    pdf_canvas.drawString(50, y_position, process_arabic_text(f"تفاصيل السائق: {driver.name}"))
    y_position -= 20
    pdf_canvas.drawString(50, y_position, process_arabic_text(f"رقم الهاتف: {driver.phone_number}"))
    y_position -= 20
    pdf_canvas.drawString(50, y_position, process_arabic_text(f"نوع المركبة: {driver.vehicle_type}"))
    y_position -= 20
    pdf_canvas.drawString(50, y_position, process_arabic_text(f"إجمالي العوائد: {total_earnings:.2f} دينار"))
    y_position -= 20
    pdf_canvas.drawString(50, y_position, process_arabic_text(f"إجمالي المدفوعات: {total_payments:.2f} دينار"))
    y_position -= 20
    pdf_canvas.drawString(50, y_position, process_arabic_text(f"صافي ربح السائق: {driver_profit:.2f} دينار"))
    y_position -= 20
    pdf_canvas.drawString(50, y_position, process_arabic_text(f"عدد الطلبات الموصلة: {delivered_orders_count}"))
    y_position -= 20
    pdf_canvas.drawString(50, y_position, process_arabic_text(f"عدد الطلبات الملغاة: {cancelled_orders_count}"))
    y_position -= 20
    pdf_canvas.drawString(50, y_position, process_arabic_text(f"المبالغ المستحقة: {due_amount:.2f} دينار"))
    y_position -= 40

    # إنهاء PDF
    pdf_canvas.save()

    # تحويل PDF إلى صورة
    images = convert_from_path(pdf_path)
    image_path = "driver_details_image.png"
    images[0].save(image_path, "PNG")

    # حذف ملف PDF المؤقت
    os.remove(pdf_path)

    # إعداد استجابة الصورة
    with open(image_path, "rb") as img_file:
        response = HttpResponse(img_file.read(), content_type="image/png")
        response["Content-Disposition"] = f"attachment; filename=driver_{driver_id}_details.png"

    # حذف ملف الصورة المؤقت
    os.remove(image_path)

    return response

def process_arabic_text(text):
    """
    معالجة النصوص العربية لتظهر بشكل صحيح في PDF.
    """
    reshaped_text = arabic_reshaper.reshape(text)  # إعادة تشكيل النصوص
    bidi_text = get_display(reshaped_text)         # تطبيق اتجاه النص
    return bidi_text
# إضافة دفعة لسائق

def add_payment(request, driver_id):
    """
    إضافة دفعة مالية لسائق معين.
    """
    driver = get_object_or_404(DeliveryPerson, id=driver_id)
    if request.method == 'POST':
        amount = request.POST.get('amount')
        notes = request.POST.get('notes', '')
        Payment.objects.create(driver=driver, amount=amount, notes=notes)  # إنشاء دفعة جديدة
        driver.total_paid += float(amount)  # تحديث إجمالي المدفوع
        driver.save()
        messages.success(request, 'تم إضافة الدفعة بنجاح!')
        return redirect('drivers_list')
    return render(request, 'otlop/add_payment.html', {'driver': driver})

# تسجيل دفعة لسائق
def record_payment(request, driver_id):
    """
    تسجيل دفعة للسائق
    """
    driver = get_object_or_404(DeliveryPerson, id=driver_id)

    if request.method == 'POST':
        amount = request.POST.get('amount')
        payment_method = request.POST.get('payment_method')
        notes = request.POST.get('notes', '')

        if amount:
            # تحويل المبلغ إلى Decimal
            amount = Decimal(amount)

            # تحديث إجمالي المدفوعات والرصيد المستحق
            driver.total_paid += amount
            driver.due_amount -= amount
            driver.save()

            # تسجيل عملية الدفع
            Payment.objects.create(
                driver=driver,
                amount=amount,
                payment_method=payment_method,
                notes=notes
            )

            # رسالة نجاح
            messages.success(request, f"تم تسجيل دفعة بقيمة {amount} للسائق {driver.name}.")
            return redirect('drivers_list')

        else:
            messages.error(request, "يرجى إدخال مبلغ صالح.")

    return render(request, 'otlop/record_payment.html', {'driver': driver})
def search_drivers(request):
    query = request.GET.get('q', '').strip()
    drivers = []

    if query:
        drivers = DeliveryPerson.objects.filter(
            Q(name__icontains=query) | Q(phone_number__icontains=query)
        )

    context = {
        'drivers': drivers,
        'query': query,
    }
    return render(request, 'otlop/search_drivers.html', context)
# تفاصيل الطلب
def order_details(request, order_id):
    """
    عرض تفاصيل الطلب بناءً على معرف الطلب.
    """
    order = get_object_or_404(Order, id=order_id)

    context = {
        'order': order,
        'partial_details': f"من {order.restaurant_area} إلى {order.customer_area} - سعر التوصيل ({order.delivery_price or 'غير محدد'} دينار) - سعر الطلبية: ({order.order_price or 'غير محدد'} دينار).",
        'full_details': f"تفاصيل كاملة: إلى  {order.customer_name}, الطلب من {order.restaurant_name} إلى {order.customer_area} بسعر توصيل {order.delivery_price or 'غير محدد'} دينار.   سعر الطلبية  {order.order_price or 'غير محدد'}   {order.notes or 'مستعجله '}"
    }
    return render(request, 'otlop/order_details.html', context)
def global_search(request):
    query = request.GET.get('q')  # الحصول على نص البحث من المستخدم
    orders = []
    drivers = []

    if query:
        # البحث في الطلبات والسائقين
        orders = Order.objects.filter(
            Q(customer_name__icontains=query) |
            Q(order_details__icontains=query)
        )
        drivers = DeliveryPerson.objects.filter(
            Q(name__icontains=query) |
            Q(phone_number__icontains=query)
        )

        # إذا كانت هناك نتيجة واحدة فقط، إعادة التوجيه إلى الصفحة المناسبة
        if orders.count() == 1 and drivers.count() == 0:
            return redirect('order_details', order_id=orders.first().id)
        elif drivers.count() == 1 and orders.count() == 0:
            return redirect('driver_details', driver_id=drivers.first().id)

    context = {
        'query': query,
        'orders': orders,
        'drivers': drivers,
    }
    return render(request, 'otlop/global_search.html', context)
# طلب جديد

def new_order(request):
    """
    إضافة طلب جديد مع تعيين سائق افتراضي (None)، مع إمكانية تعديله لاحقًا.
    """
    partial_details = ''
    full_details = ''
    
    if request.method == 'POST':
        # استلام بيانات الطلب من الفورم
        customer_name = request.POST.get('customer_name')
        customer_area = request.POST.get('customer_area')
        restaurant_name = request.POST.get('restaurant_name')
        restaurant_area = request.POST.get('restaurant_area')
        delivery_price = request.POST.get('delivery_price') or None
        order_price = request.POST.get('order_price') or None
        notes = request.POST.get('notes') or None

        # السائق يتم تركه فارغًا (None) في البداية
        delivery_person = None
        delivery_person_id = request.POST.get('delivery_person')
        if delivery_person_id:
            delivery_person = get_object_or_404(DeliveryPerson, id=delivery_person_id)

        # إنشاء الطلب الجديد
        new_order = Order.objects.create(
            customer_name=customer_name,
            customer_area=customer_area,
            restaurant_name=restaurant_name,
            restaurant_area=restaurant_area,
            delivery_price=delivery_price,
            order_price=order_price,
            notes=notes,
            delivery_person=delivery_person,  # سائق غير محدد
            order_details=f"من {restaurant_name} إلى {customer_area} بسعر {delivery_price or 'غير محدد'}"
        )

        # توليد التفاصيل الجزئية والتفاصيل الكاملة
        partial_details = f"من {restaurant_name} إلى {customer_area} بسعر {delivery_price or 'غير محدد'}"
        full_details = f"الزبون: {customer_name}, منطقة الزبون: {customer_area}, المطعم: {restaurant_name}, منطقة المطعم: {restaurant_area}, " \
                       f"سعر التوصيل: {delivery_price or 'غير محدد'}, سعر الطلبية: {order_price or 'غير محدد'}, ملاحظات: {notes or 'لا توجد ملاحظات'}"

        # عرض رسالة تأكيد
        messages.success(request, 'تم إرسال الطلب بنجاح!')
        return redirect('order_details', order_id=new_order.id)

    # إذا كان الطلب GET، عرض صفحة الطلب
    drivers = DeliveryPerson.objects.all()
    pending_orders = Order.objects.filter(delivery_status='Pending')

    context = {
        'drivers': drivers,
        'pending_orders': pending_orders,
        'partial_details': partial_details,
        'full_details': full_details,
    }

    return render(request, 'otlop/new-order.html', context)

# تحديث حالة الطلب
def update_order_status(request, order_id, status):
    """
    تحديث حالة الطلب إلى "تم التسليم" أو "تم الإلغاء".
    """
    order = get_object_or_404(Order, id=order_id)

    if status == 'delivered':
        order.delivery_status = 'Delivered'
        messages.success(request, 'تم تحديث حالة الطلب إلى "تم التسليم".')
    elif status == 'cancelled':
        order.delivery_status = 'Cancelled'
        messages.success(request, 'تم تحديث حالة الطلب إلى "تم إلغاء الطلب".')
    else:
        messages.error(request, 'حالة الطلب غير معروفة.')

    order.save()

    return redirect('dashboard')
# عرض حسابات السائقين
def driver_accounts(request):
    """
    عرض حسابات السائقين مع عرض الإيرادات المدفوعة والمستحقة.
    """
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # جلب جميع الطلبات
    orders = Order.objects.all()

    # تصفية الطلبات حسب التواريخ إذا كانت محددة
    if start_date:
        start_date = parse_date(start_date)
        orders = orders.filter(created_at__date__gte=start_date)
    if end_date:
        end_date = parse_date(end_date)
        orders = orders.filter(created_at__date__lte=end_date)

    # جلب جميع السائقين
    drivers = DeliveryPerson.objects.all()

    driver_data = []
    total_due_amount = 0
    total_revenue = 0
    total_paid = 0
    total_orders_count = 0
    total_net_profit = 0

    for driver in drivers:
        # حساب الطلبات المرتبطة بالسائق
        driver_orders = orders.filter(delivery_person=driver, delivery_status='Delivered')

        # حساب إجمالي الإيرادات للسائق
        driver_revenue = driver_orders.aggregate(Sum('delivery_price'))['delivery_price__sum'] or 0

        # حساب إجمالي المدفوعات للسائق
        driver_paid = driver.payment_set.aggregate(Sum('amount'))['amount__sum'] or 0

        # حساب الرصيد المستحق من السائق للشركة
        company_share = (driver_revenue * (100 - driver.percentage)) / 100
        due_amount = company_share - driver_paid  # المبلغ الذي يدين به السائق للشركة

        # حساب صافي الربح من السائق
        driver_net_profit = company_share

        # تجميع البيانات في قائمة السائقين
        driver_data.append({
            'driver': driver,
            'total_orders': driver_orders.count(),
            'total_revenue': driver_revenue,
            'total_paid': driver_paid,
            'due_amount': due_amount,
            'percentage': driver.percentage,
            'company_percentage': 100 - driver.percentage,
            'net_profit': driver_net_profit,
        })

        # تحديث الإجماليات
        total_due_amount += due_amount
        total_revenue += driver_revenue
        total_paid += driver_paid
        total_orders_count += driver_orders.count()
        total_net_profit += driver_net_profit

    # حساب نسبة الشركة الإجمالية إذا كان هناك سائقون
    total_company_percentage = (
        100 - (sum([driver['percentage'] for driver in driver_data]) / len(driver_data))
    ) if driver_data else 0

    context = {
        'driver_data': driver_data,
        'total_due_amount': total_due_amount,
        'total_revenue': total_revenue,
        'total_paid': total_paid,
        'total_orders_count': total_orders_count,
        'total_net_profit': total_net_profit,
        'total_company_percentage': total_company_percentage,
        'start_date': start_date,
        'end_date': end_date,
    }

    return render(request, 'otlop/driver_accounts.html', context)

def edit_driver(request, driver_id):
    """
    تعديل بيانات السائق
    """
    driver = get_object_or_404(DeliveryPerson, id=driver_id)

    if request.method == 'POST':
        driver.name = request.POST.get('name')
        driver.phone_number = request.POST.get('phone_number')
        driver.vehicle_type = request.POST.get('vehicle_type')
        driver.license_number = request.POST.get('license_number')
        driver.percentage = request.POST.get('percentage')
        
        # التحقق من الرمز السري
        secret_code = request.POST.get('secret_code')
        if secret_code == '1234512345':  # استبدلها بالرمز الصحيح
            driver.save()
            messages.success(request, 'تم تحديث بيانات السائق بنجاح.')
            return redirect('drivers_list')
        else:
            messages.error(request, 'الرمز السري غير صحيح.')

    return render(request, 'otlop/edit-driver.html', {'driver': driver})
def delete_driver(request, driver_id):
    """
    حذف سائق بناءً على الرمز السري.
    """
    driver = get_object_or_404(DeliveryPerson, id=driver_id)

    if request.method == 'POST':
        secret_code = request.POST.get('secret_code')

        # تحقق من الرمز السري
        if secret_code == "1234512345":  # استبدل "admin123" بالرمز السري الحقيقي
            driver.delete()
            messages.success(request, f"تم حذف السائق {driver.name} بنجاح!")
            return redirect('drivers_list')
        else:
            messages.error(request, "الرمز السري غير صحيح. لا يمكنك حذف السائق!")

    return render(request, 'otlop/delete-driver.html', {'driver': driver})
# دالة التسجيل
def register(request):
    """
    إنشاء حساب مستخدم جديد.
    """
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(request.POST['password'])  # تأكد من حفظ كلمة المرور بشكل آمن
            user.save()
            messages.success(request, 'تم إنشاء الحساب بنجاح! يمكنك الآن تسجيل الدخول.')
            return redirect('login')  # إعادة التوجيه إلى صفحة تسجيل الدخول بعد التسجيل بنجاح
    else:
        form = CustomUserCreationForm()

    return render(request, 'otlop/register.html', {'form': form})

# دالة تسجيل الدخول

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, "تم تسجيل الدخول بنجاح!")
                return redirect('home')  # Redirect to the 'home' named URL
            else:
                messages.error(request, "اسم المستخدم أو كلمة المرور غير صحيحة.")
        else:
            messages.error(request, "يرجى إدخال بيانات صحيحة.")
    else:
        form = AuthenticationForm()
    return render(request, 'otlop/login.html', {'form': form})
# دالة إنشاء الحساب
def register_view(request):
    """
    إنشاء حساب مستخدم جديد باستخدام نموذج التسجيل الافتراضي.
    """
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # تسجيل الدخول مباشرة بعد إنشاء الحساب
            messages.success(request, "تم إنشاء الحساب بنجاح!")
            return redirect('home')  # تحويل المستخدم إلى الصفحة الرئيسية بعد التسجيل
        else:
            messages.error(request, "هناك خطأ في البيانات المدخلة.")
    else:
        form = UserCreationForm()

    return render(request, 'otlop/register.html', {'form': form})
# ملف views.py
def add_employee(request):
    if request.method == 'POST':
        # عملية إضافة الموظف
        name = request.POST['employee_name']
        position = request.POST['employee_position']
        salary = request.POST['employee_salary']
        phone = request.POST['employee_phone']

        # إنشاء الموظف
        employee = Employee.objects.create(
            name=name, 
            position=position, 
            salary=salary, 
            phone=phone
        )
        # التوجيه إلى قائمة الموظفين
        return redirect('employee_list')
    
    return render(request, 'otlop/add_employee.html')

def employee_list(request):
    employees = Employee.objects.all()
    for employee in employees:
        employee.salary_after_penalty = employee.calculate_salary_after_penalty()
    return render(request, 'otlop/employee_list.html', {'employees': employees})

def calculate_salary_after_penalty(self):
    # حساب الراتب بعد خصم التأخير أو السلفة أو الخصم العام
    return self.salary - self.calculate_penalty() - self.loan_taken - self.discount_amount
def edit_employee(request, id):
    employee = get_object_or_404(Employee, pk=id)

    if request.method == 'POST':
        employee.name = request.POST['employee_name']
        employee.position = request.POST['employee_position']
        employee.salary = request.POST['employee_salary']
        employee.phone = request.POST['employee_phone']
        employee.save()
        return redirect('employee_list')

    return render(request, 'otlop/edit_employee.html', {'employee': employee})

def delete_employee(request, id):
    employee = get_object_or_404(Employee, pk=id)
    
    if request.method == 'POST':
        employee.delete()
        return redirect('employee_list')
    
    return render(request, 'otlop/confirm_delete.html', {'employee': employee})

# عرض تفاصيل الموظف
def employee_detail(request, id):
    employee = get_object_or_404(Employee, pk=id)
    return render(request, 'otlop/employee_detail.html', {'employee': employee})


# دالة لإضافة إجراء مثل الخصم أو السلفة أو الدقائق المتأخرة



def add_employee_action(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id)
    
    if request.method == 'POST':
        # اجلب القيم من POST كـ string، واحرص على معالجة الفراغات
        discount_str = request.POST.get('discount_amount', '').strip()
        penalty_reason = request.POST.get('penalty_reason', '').strip()
        late_minutes_str = request.POST.get('late_minutes', '').strip()
        loan_str = request.POST.get('loan_taken', '').strip()

        # حوّل discount_amount إلى Decimal، وإذا كانت فارغة أو غير صالحة -> صفر
        try:
            discount_amount = Decimal(discount_str) if discount_str else Decimal('0')
        except InvalidOperation:
            discount_amount = Decimal('0')

        # حوّل loan_taken إلى Decimal، وإذا كانت فارغة أو غير صالحة -> صفر
        try:
            loan_taken = Decimal(loan_str) if loan_str else Decimal('0')
        except InvalidOperation:
            loan_taken = Decimal('0')

        # حوّل late_minutes إلى int، وإذا كانت فارغة أو غير صالحة -> صفر
        try:
            late_minutes = int(late_minutes_str) if late_minutes_str else 0
        except ValueError:
            late_minutes = 0

        # طبّق التحديثات على الموظف
        employee.late_minutes += late_minutes
        employee.loan_taken += loan_taken
        employee.penalty_reason = penalty_reason

        # إذا كان discount_amount أكبر من صفر، اطرح من salary
        employee.salary -= discount_amount

        # إعادة حساب الراتب بعد العقوبة/السلفة/الخصم
        employee.calculate_salary_after_penalty()
        employee.save()
        
        messages.success(request, 'تم تحديث بيانات الموظف بنجاح.')
        return redirect('employee_list')
    
    # إذا لم يكن الطلب POST فعُد إلى نفس الصفحة أو أي صفحة أخرى
    return render(request, 'otlop/employee_list.html', {"employee": employee})
def add_employee_discount(request, employee_id):
    employee = get_object_or_404(Employee, pk=employee_id)
    
    if request.method == 'POST':
        # الحصول على قيمة الخصم من النموذج
        discount_amount = float(request.POST.get('discount_amount', 0))
        penalty_reason = request.POST.get('penalty_reason', '')
        
        # تحديث المبلغ الذي سيتم خصمه
        employee.discount_amount += discount_amount
        employee.penalty_reason = penalty_reason
        
        # حساب الراتب بعد الخصم
        employee.salary_after_penalty = employee.calculate_salary_after_penalty()
        
        employee.save()  # حفظ التحديثات

        return redirect('employee_list')  # العودة إلى صفحة قائمة الموظفين

    return HttpResponse("فشل إضافة الخصم", status=400)

def edit_action(request, action_id):
    # الحصول على الإجراء المطلوب أو إرجاع 404 إذا لم يتم العثور عليه
    action = get_object_or_404(EmployeeAction, id=action_id)
    
    if request.method == 'POST':
        # إذا كانت الطريقة POST، قم بإنشاء نموذج مع البيانات المقدمة
        form = EmployeeActionForm(request.POST, instance=action)
        if form.is_valid():
            # حفظ النموذج إذا كان صالحًا
            form.save()
            # تحديث راتب الموظف بعد التعديل
            action.employee.calculate_salary_after_penalty()
            # إعادة التوجيه إلى صفحة تفاصيل الموظف
            return redirect('employee_detail', employee_id=action.employee.id)
    else:
        # إذا كانت الطريقة GET، قم بإنشاء نموذج مع بيانات الإجراء الحالي
        form = EmployeeActionForm(instance=action)
    
    # عرض صفحة التعديل مع النموذج والإجراء
    return render(request, 'otlop/edit_action.html', {'form': form, 'action': action})

def delete_action(request, action_id):
    # الحصول على الإجراء المطلوب أو إرجاع 404 إذا لم يتم العثور عليه
    action = get_object_or_404(EmployeeAction, id=action_id)
    employee_id = action.employee.id
    
    # حذف الإجراء
    action.delete()
    
    # تحديث راتب الموظف بعد الحذف
    action.employee.calculate_salary_after_penalty()
    
    # إعادة التوجيه إلى صفحة تفاصيل الموظف
    return redirect('employee_detail', id=employee_id)
