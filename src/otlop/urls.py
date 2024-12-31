from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),  # الصفحة الرئيسية
    path('dashboard/', views.dashboard, name='dashboard'),  # لوحة التحكم
    path('new-order/', views.new_order, name='new_order'),  # طلب جديد
    path('previous-orders/', views.previous_orders, name='previous_orders'),  # الطلبات السابقة
    path('order/<int:order_id>/', views.order_details, name='order_details'),  # تفاصيل الطلب
    path('order/<int:order_id>/update-status/<str:status>/', views.update_order_status, name='update_order_status'),  # تحديث حالة الطلب
    path('order/<int:order_id>/edit/', views.edit_order, name='edit_order'),  # تعديل الطلب
    path('driver-accounts/', views.driver_accounts, name='driver_accounts'),  # حسابات السائقين
    path('record-payment/<int:driver_id>/', views.record_payment, name='record_payment'),    path('drivers-list/', views.drivers_list, name='drivers_list'),
    path('register/', views.register, name='register'),  # رابط صفحة التسجيل
    path('login/', views.login_view, name='login'),      # رابط صفحة تسجيل الدخول 
    path('drivers-list/', views.drivers_list, name='drivers_list'),
]
