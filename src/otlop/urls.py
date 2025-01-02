from django.urls import path
from . import views

urlpatterns = [
    # الصفحة الرئيسية ولوحة التحكم
    path('', views.home, name='home'),  # الصفحة الرئيسية
    path('dashboard/', views.dashboard, name='dashboard'),  # لوحة التحكم

    # البحث
    path('global-search/', views.global_search, name='global_search'),  # البحث الشامل

    # الطلبات
    path('new-order/', views.new_order, name='new_order'),  # إنشاء طلب جديد
    path('previous-orders/', views.previous_orders, name='previous_orders'),  # عرض الطلبات السابقة
    path('order/<int:order_id>/', views.order_details, name='order_details'),  # تفاصيل طلب
    path('order/<int:order_id>/update-status/<str:status>/', views.update_order_status, name='update_order_status'),  # تحديث حالة الطلب
    path('order/<int:order_id>/edit/', views.edit_order, name='edit_order'),  # تعديل الطلب
    path('order/<int:order_id>/assign-driver/', views.assign_driver, name='assign_driver'),  # تعيين السائق لطلب

    # السائقين
    path('drivers-list/', views.drivers_list, name='drivers_list'),  # عرض قائمة السائقين
    path('drivers/add/', views.add_driver, name='add_driver'),  # مسار إضافة سائق جديد
    path('driver/<int:driver_id>/edit/', views.edit_driver, name='edit_driver'),  # تعديل بيانات السائق
    path('driver/<int:driver_id>/delete/', views.delete_driver, name='delete_driver'),  # حذف السائق
    path('driver/<int:driver_id>/details/', views.driver_details, name='driver_details'),  # تفاصيل السائق
    path('driver/<int:driver_id>/export-to-excel/', views.export_driver_details_to_excel, name='export_driver_to_excel'),
    path('driver/<int:driver_id>/export-to-pdf/', views.export_driver_to_pdf, name='export_driver_to_pdf'),
    # المدفوعات
    path('driver-accounts/', views.driver_accounts, name='driver_accounts'),  # إدارة حسابات السائقين
    path('record-payment/<int:driver_id>/', views.record_payment, name='record_payment'),  # تسجيل دفعة للسائق

    # التسجيل وتسجيل الدخول
    path('register/', views.register, name='register'),  # صفحة التسجيل
    path('login/', views.login_view, name='login'),  # صفحة تسجيل الدخول
]