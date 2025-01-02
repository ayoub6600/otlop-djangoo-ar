from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils.dateparse import parse_date
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
import openpyxl
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import arabic_reshaper
from bidi.algorithm import get_display
import os

# استيراد النماذج
from .models import Order, DeliveryPerson, Payment

# استيراد النماذج والحقول المخصصة
from .forms import OrderForm, CustomUserCreationForm

# استيراد الأدوات الخاصة بالاستعلامات وحساب الإجماليات
from django.db.models import Sum, Count, Q
from django.db import models

# استيراد أدوات التعامل مع الأرقام العشرية
from decimal import Decimal, InvalidOperation

PASSWORD = "Ayoub@@1234"  # استبدل بكلمة المرور التي تريدها

# الصفحة الرئيسية
def home(request):
    """
    عرض الصفحة الرئيسية للموقع
    """
    return render(request, 'otlop/index.html', {'title': 'Home'})

# لوحة التحكم (Dashboard)
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
    """
    عرض قائمة بجميع الطلبات السابقة مع إمكانية تصفيتها حسب التواريخ.
    """
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    orders = Order.objects.all().order_by('-created_at')  # عرض الطلبات مرتبة تنازليًا حسب تاريخ الإنشاء
    if start_date:
        start_date = parse_date(start_date)
        orders = orders.filter(created_at__date__gte=start_date)  # تصفية الطلبات بتاريخ بدء أكبر
    if end_date:
        end_date = parse_date(end_date)
        orders = orders.filter(created_at__date__lte=end_date)  # تصفية الطلبات بتاريخ انتهاء أصغر

    context = {
        'orders': orders,
        'start_date': start_date,
        'end_date': end_date,
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
        driver.due_amount = driver.calculate_due_amount()  # استدعاء دالة لحساب المبالغ المستحقة
        driver.total_orders = driver.orders.count()  # حساب عدد الطلبات لكل سائق

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
    driver = get_object_or_404(DeliveryPerson, id=driver_id)
    
    # استرجاع جميع الطلبات المرتبطة بالسائق
    orders = driver.orders.all()
    
    # إجمالي الإيرادات (التوصيل)
    total_earnings = orders.aggregate(Sum('delivery_price'))['delivery_price__sum'] or 0
    
    # إجمالي المدفوعات
    payments = Payment.objects.filter(driver=driver)
    total_payments = payments.aggregate(Sum('amount'))['amount__sum'] or 0

    # حساب أرباح السائق بناءً على نسبة السائق
    driver_profit = total_earnings * driver.percentage / 100

    # حساب عدد الطلبات الموصلة
    delivered_orders_count = orders.filter(delivery_status='Delivered').count()

    # حساب إجمالي الطلبات الملغاة (لإضافة لمسة إضافية)
    cancelled_orders_count = orders.filter(delivery_status='Cancelled').count()

    # إرسال البيانات إلى القالب
    context = {
        'driver': driver,
        'orders': orders,
        'total_earnings': total_earnings,
        'payments': payments,
        'total_payments': total_payments,
        'driver_profit': driver_profit,  # إضافة أرباح السائق
        'delivered_orders_count': delivered_orders_count,  # عدد الطلبات الموصلة
        'cancelled_orders_count': cancelled_orders_count,  # عدد الطلبات الملغاة
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
        driver.total_paid,
        driver.due_amount
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
def export_driver_to_pdf(request, driver_id):
    # جلب تفاصيل السائق
    driver = get_object_or_404(DeliveryPerson, id=driver_id)
    orders = driver.orders.all()
    payments = Payment.objects.filter(driver=driver)

    # إعداد استجابة PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="driver_{driver_id}_details.pdf"'

    # تسجيل الخط
    FONT_PATH = "/Users/ayoubbelhaj/Documents/projects/otlopdelivery/src/otlop/static/otlop/fonts/Tajawal-ExtraLight.ttf"
    pdfmetrics.registerFont(TTFont('Tajawal', FONT_PATH))

    # إنشاء ملف PDF
    pdf_canvas = canvas.Canvas(response, pagesize=letter)
    pdf_canvas.setFont("Tajawal", 14)

    # كتابة تفاصيل السائق
    y_position = 750
    pdf_canvas.drawString(50, y_position, process_arabic_text(f"تفاصيل السائق: {driver.name}"))
    y_position -= 20
    pdf_canvas.drawString(50, y_position, process_arabic_text(f"رقم الهاتف: {driver.phone_number}"))
    y_position -= 20
    pdf_canvas.drawString(50, y_position, process_arabic_text(f"نوع المركبة: {driver.vehicle_type}"))
    y_position -= 40

    # كتابة تفاصيل الطلبات
    pdf_canvas.drawString(50, y_position, process_arabic_text("الطلبات:"))
    y_position -= 20

    if orders.exists():
        for idx, order in enumerate(orders, start=1):
            order_details = f"{idx}. {order.order_details} - {order.delivery_price or 'غير محدد'} دينار"
            pdf_canvas.drawString(50, y_position, process_arabic_text(order_details))
            y_position -= 20
            if y_position < 50:  # إذا انتهت الصفحة
                pdf_canvas.showPage()
                pdf_canvas.setFont("Tajawal", 14)
                y_position = 750
    else:
        pdf_canvas.drawString(50, y_position, process_arabic_text("لا توجد طلبات مسجلة لهذا السائق."))

    y_position -= 40
    pdf_canvas.drawString(50, y_position, process_arabic_text("المدفوعات:"))
    y_position -= 20

    if payments.exists():
        for idx, payment in enumerate(payments, start=1):
            payment_details = f"{idx}. {payment.amount} دينار - {payment.payment_method or 'غير محدد'}"
            pdf_canvas.drawString(50, y_position, process_arabic_text(payment_details))
            y_position -= 20
            if y_position < 50:  # إذا انتهت الصفحة
                pdf_canvas.showPage()
                pdf_canvas.setFont("Tajawal", 14)
                y_position = 750
    else:
        pdf_canvas.drawString(50, y_position, process_arabic_text("لا توجد مدفوعات مسجلة لهذا السائق."))

    # حفظ ملف PDF
    pdf_canvas.save()
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
        'full_details': f"تفاصيل كاملة: إلى الزبون {order.customer_name}, الطلب من {order.restaurant_area} إلى {order.customer_area} بسعر توصيل {order.delivery_price or 'غير محدد'} دينار."
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
            order_details=f"من {restaurant_name} إلى {customer_area} بسعر {order_price or 'غير محدد'}"
        )

        # عرض رسالة تأكيد
        messages.success(request, 'تم إرسال الطلب بنجاح!')
        return redirect('order_details', order_id=new_order.id)

    # إذا كان الطلب GET، عرض صفحة الطلب
    drivers = DeliveryPerson.objects.all()
    pending_orders = Order.objects.filter(delivery_status='Pending')

    context = {
        'drivers': drivers,
        'pending_orders': pending_orders,
    }

    return render(request, 'otlop/new-order.html', context)
    context = {
        'drivers': drivers,
        'pending_orders': pending_orders,
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
    total_percentage = 0
    total_company_percentage = 0

    for driver in drivers:
        # حساب الطلبات المرتبطة بالسائق
        driver_orders = orders.filter(delivery_person=driver)

        # حساب إجمالي الإيرادات للسائق
        driver_revenue = driver_orders.aggregate(Sum('delivery_price'))['delivery_price__sum'] or 0

        # حساب إجمالي المدفوعات للسائق
        driver_paid = driver.payment_set.aggregate(Sum('amount'))['amount__sum'] or 0

        # حساب الرصيد المستحق للسائق
        due_amount = driver_revenue - driver_paid

        # حساب صافي الربح من السائق
        driver_net_profit = (driver_revenue * (100 - driver.percentage)) / 100

        # حساب نسبة الشركة
        company_percentage = 100 - driver.percentage

        # تجميع البيانات في قائمة السائقين
        driver_data.append({
            'driver': driver,
            'total_orders': driver_orders.count(),
            'total_revenue': driver_revenue,
            'total_paid': driver_paid,
            'due_amount': due_amount,
            'percentage': driver.percentage,
            'company_percentage': company_percentage,
            'net_profit': driver_net_profit,
        })

        # تحديث الإجماليات
        total_due_amount += due_amount
        total_revenue += driver_revenue
        total_paid += driver_paid
        total_orders_count += driver_orders.count()
        total_net_profit += driver_net_profit
        total_percentage += driver.percentage
        total_company_percentage += company_percentage

    # حساب متوسط النسب
    average_percentage = total_percentage / len(drivers) if drivers else 0
    average_company_percentage = total_company_percentage / len(drivers) if drivers else 0

    context = {
        'driver_data': driver_data,
        'total_due_amount': total_due_amount,
        'total_revenue': total_revenue,
        'total_paid': total_paid,
        'total_orders_count': total_orders_count,
        'total_net_profit': total_net_profit,
        'average_percentage': average_percentage,
        'total_company_percentage': average_company_percentage,  # إرسال نسبة الشركة الإجمالية
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
    """
    تسجيل الدخول للمستخدم.
    """
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')

            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, "تم تسجيل الدخول بنجاح!")
                return redirect('home')  # توجيه المستخدم إلى الصفحة الرئيسية بعد تسجيل الدخول
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