from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm
from .models import Order, DeliveryPerson, Payment
from .forms import OrderForm, CustomUserCreationForm  # تأكد من أنك أضفت نموذج التسجيل المخصص
from django.contrib.auth.forms import UserCreationForm
from django.utils.dateparse import parse_date
from django.db.models import Sum, Count


PASSWORD = "Ayoub@@1234"  # استبدل بكلمة المرور التي تريدها

# الصفحة الرئيسية
def home(request):
    return render(request, 'otlop/index.html', {'title': 'Home'})

# لوحة التحكم
def dashboard(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    orders = Order.objects.all()
    if start_date:
        start_date = parse_date(start_date)
        orders = orders.filter(created_at__date__gte=start_date)
    if end_date:
        end_date = parse_date(end_date)
        orders = orders.filter(created_at__date__lte=end_date)

    pending_orders = orders.filter(delivery_status='Pending')
    delivered_orders = orders.filter(delivery_status='Delivered')
    cancelled_orders = orders.filter(delivery_status='Cancelled')

    total_revenue = delivered_orders.aggregate(Sum('delivery_price'))['delivery_price__sum'] or 0
    total_orders = orders.count()
    total_pending = pending_orders.count()
    profit_percentage = 30
    net_profit = (total_revenue * profit_percentage) / 100

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
            show_sensitive_data = True
        else:
            messages.error(request, "كلمة المرور غير صحيحة.")

    context = {
        'pending_orders': pending_orders,
        'delivered_orders': delivered_orders,
        'cancelled_orders': cancelled_orders,
        'total_orders': total_orders if show_sensitive_data else "****",
        'total_pending': total_pending,
        'total_revenue': total_revenue if show_sensitive_data else "****",
        'net_profit': net_profit if show_sensitive_data else "****",
        'most_requested_restaurants': most_requested_restaurants,
        'most_active_drivers': most_active_drivers,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'otlop/dashboard.html', context)

# عرض الطلبات السابقة
def previous_orders(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    orders = Order.objects.all().order_by('-created_at')
    if start_date:
        start_date = parse_date(start_date)
        orders = orders.filter(created_at__date__gte=start_date)
    if end_date:
        end_date = parse_date(end_date)
        orders = orders.filter(created_at__date__lte=end_date)

    context = {
        'orders': orders,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'otlop/previous-orders.html', context)

# تعديل الطلب
def edit_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if request.method == "POST":
        order.customer_name = request.POST.get('customer_name')
        order.customer_area = request.POST.get('customer_area')
        order.restaurant_name = request.POST.get('restaurant_name')
        order.restaurant_area = request.POST.get('restaurant_area')
        order.delivery_price = request.POST.get('delivery_price')
        order.order_price = request.POST.get('order_price')
        order.notes = request.POST.get('notes')
        order.save()

        messages.success(request, "تم تعديل الطلب بنجاح!")
        return redirect('previous_orders')

    context = {
        'order': order,
    }
    return render(request, 'otlop/edit-order.html', context)

# عرض قائمة السائقين
def drivers_list(request):
    drivers = DeliveryPerson.objects.all()
    for driver in drivers:
        driver.due_amount = driver.calculate_due_amount()

    context = {
        'drivers': drivers,
    }
    return render(request, 'otlop/drivers_list.html', context)

# إضافة دفعة لسائق
def add_payment(request, driver_id):
    driver = get_object_or_404(DeliveryPerson, id=driver_id)
    if request.method == 'POST':
        amount = request.POST.get('amount')
        notes = request.POST.get('notes', '')
        Payment.objects.create(driver=driver, amount=amount, notes=notes)
        driver.total_paid += float(amount)
        driver.save()
        messages.success(request, 'تم إضافة الدفعة بنجاح!')
        return redirect('drivers_list')
    return render(request, 'otlop/add_payment.html', {'driver': driver})

# تسجيل دفعة لسائق
def record_payment(request, driver_id):
    driver = get_object_or_404(DeliveryPerson, id=driver_id)
    if request.method == 'POST':
        amount = request.POST.get('amount')
        notes = request.POST.get('notes', '')
        Payment.objects.create(driver=driver, amount=amount, notes=notes)
        driver.total_paid += float(amount)
        driver.save()
        messages.success(request, f'تم تسجيل دفعة بقيمة {amount} للسائق {driver.name} بنجاح.')
        return redirect('drivers_list')

    context = {
        'driver': driver,
    }
    return render(request, 'otlop/record_payment.html', context)

# تفاصيل السائق
def order_details(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    context = {
        'order': order,
        'partial_details': f"من {order.restaurant_area} إلى {order.customer_area} - سعر التوصيل ({order.delivery_price or 'غير محدد'} دينار) - سعر الطلبية: ({order.order_price or 'غير محدد'} دينار).",
        'full_details': f"تفاصيل كاملة: إلى الزبون {order.customer_name}, الطلب من {order.restaurant_area} إلى {order.customer_area} بسعر توصيل {order.delivery_price or 'غير محدد'} دينار."
    }
    return render(request, 'otlop/order_details.html', context)

# طلب جديد
def new_order(request):
    if request.method == 'POST':
        customer_name = request.POST.get('customer_name')
        customer_area = request.POST.get('customer_area')
        restaurant_name = request.POST.get('restaurant_name')
        restaurant_area = request.POST.get('restaurant_area')
        delivery_price = request.POST.get('delivery_price') or None
        order_price = request.POST.get('order_price') or None
        notes = request.POST.get('notes') or None
        delivery_person_id = request.POST.get('delivery_person')

        delivery_person = None
        if delivery_person_id:
            delivery_person = get_object_or_404(DeliveryPerson, id=delivery_person_id)

        new_order = Order.objects.create(
            customer_name=customer_name,
            customer_area=customer_area,
            restaurant_name=restaurant_name,
            restaurant_area=restaurant_area,
            delivery_price=delivery_price,
            order_price=order_price,
            notes=notes,
            delivery_person=delivery_person,
            order_details=f"من {restaurant_name} إلى {customer_area} بسعر {order_price or 'غير محدد'}"
        )

        messages.success(request, 'تم إرسال الطلب بنجاح!')
        return redirect('order_details', order_id=new_order.id)

    # جلب جميع السائقين
    drivers = DeliveryPerson.objects.all()

    # جلب الطلبات المعلقة
    pending_orders = Order.objects.filter(delivery_status='Pending')

    # تمرير السائقين والطلبات المعلقة إلى القالب
    context = {
        'drivers': drivers,
        'pending_orders': pending_orders,
    }

    return render(request, 'otlop/new-order.html', context)

# تحديث حالة الطلب
def update_order_status(request, order_id, status):
    # الحصول على الطلب المحدد
    order = get_object_or_404(Order, id=order_id)
    
    # تحديث حالة الطلب بناءً على الحالة الجديدة
    if status == 'delivered':
        order.delivery_status = 'Delivered'
        messages.success(request, 'تم تحديث حالة الطلب إلى "تم التسليم".')
    elif status == 'cancelled':
        order.delivery_status = 'Cancelled'
        messages.success(request, 'تم تحديث حالة الطلب إلى "تم إلغاء الطلب".')
    else:
        messages.error(request, 'حالة الطلب غير معروفة.')

    # حفظ التغييرات
    order.save()
    
    # إعادة التوجيه إلى لوحة التحكم أو الصفحة المناسبة
    return redirect('dashboard')  # يمكنك تغيير الهدف إلى صفحة أخرى إذا لزم الأمر

# عرض حسابات السائقين
def driver_accounts(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    orders = Order.objects.all()
    
    # تصفية الطلبات حسب التاريخ إذا كانت موجودة
    if start_date:
        start_date = parse_date(start_date)
        orders = orders.filter(created_at__date__gte=start_date)
    if end_date:
        end_date = parse_date(end_date)
        orders = orders.filter(created_at__date__lte=end_date)

    # جلب السائقين
    drivers = DeliveryPerson.objects.all()

    driver_data = []
    for driver in drivers:
        driver_orders = orders.filter(delivery_person=driver)
        total_revenue = driver_orders.aggregate(Sum('delivery_price'))['delivery_price__sum'] or 0
        total_paid = driver.payment_set.aggregate(Sum('amount'))['amount__sum'] or 0
        due_amount = total_revenue - total_paid

        driver_data.append({
            'driver': driver,
            'total_orders': driver_orders.count(),
            'total_revenue': total_revenue,
            'total_paid': total_paid,
            'due_amount': due_amount,
        })

    # تمرير البيانات إلى القالب
    context = {
        'driver_data': driver_data,
    }

    # إرجاع الاستجابة الصحيحة
    return render(request, 'otlop/driver_accounts.html', context)

# دالة التسجيل
def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            # حفظ كلمة المرور بشكل آمن
            user.set_password(request.POST['password'])
            user.save()
            # عرض رسالة نجاح
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
    