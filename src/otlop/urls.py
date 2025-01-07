from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # صفحة تسجيل الدخول
    path('login/', views.login_view, name='login'),  # صفحة تسجيل الدخول
    path('register/', views.register, name='register'),  # صفحة التسجيل

    # الموظفين
    path('add-employee/', views.add_employee, name='add_employee'),
    path('employee-list/', views.employee_list, name='employee_list'),
    path('edit-employee/<int:id>/', views.edit_employee, name='edit_employee'),
    path('delete-employee/<int:id>/', views.delete_employee, name='delete_employee'),
    path('employee-detail/<int:id>/', views.employee_detail, name='employee_detail'),  # صفحة التفاصيل
    path('add-employee-action/<int:employee_id>/', views.add_employee_action, name='add_employee_action'),
    path('add-discount/<int:employee_id>/', views.add_employee_discount, name='add_employee_discount'),
    path('edit-action/<int:action_id>/', views.edit_action, name='edit_action'),
    path('delete-action/<int:action_id>/', views.delete_action, name='delete_action'),

    # بعد تسجيل الدخول يجب أن يتم إعادة التوجيه إلى الصفحة الرئيسية
    path('', views.home, name='home'),  # الصفحة الرئيسية بعد تسجيل الدخول
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
    path('driver/<int:driver_id>/export-to-pdf/', views.export_driver_to_image, name='export_driver_to_pdf'),    # المدفوعات
    path('driver-accounts/', views.driver_accounts, name='driver_accounts'),  # إدارة حسابات السائقين
    path('record-payment/<int:driver_id>/', views.record_payment, name='record_payment'),  # تسجيل دفعة للسائق
]