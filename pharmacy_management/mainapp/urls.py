from django.urls import path
from . import views

urlpatterns = [

    # ================== USER PAGES ==================
    path('', views.home, name='home'),
    path('admin/dashboard/', views.dashboard, name='admin_dashboard'),
    path('medicines/', views.medicines, name='medicines'),
    path('upload-prescription/', views.upload_prescription, name='upload_prescription'),
    path('payment/<int:order_id>/', views.payment, name='payment'),
    path('my-orders/', views.my_orders, name='my_orders'),
    path('order/<int:order_id>/', views.order_detail_user, name='order_detail_user'),
    path('prescription-confirmation/<int:order_id>/', views.prescription_confirmation, name='prescription_confirmation'),
    path('order-tracking/<int:order_id>/', 
     views.order_tracking, 
     name='order_tracking'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('order/<int:order_id>/bill/', views.bill_view, name='bill_view'),
    path('download-invoice/<int:order_id>/', views.download_invoice, name='download_invoice'),
    path('cancel-order/<int:order_id>/', views.cancel_order, name='cancel_order'),
    path("pay-online/<int:order_id>/", views.pay_online, name="pay_online"),
    path("select-cod/<int:order_id>/", views.select_cod, name="select_cod"),
    path("pay/<int:order_id>/", views.pay_with_razorpay, name="pay_with_razorpay"),
    path("payment-success/<int:order_id>/", views.payment_success, name="payment_success"),
    path("payment-successful/<int:order_id>/", views.payment_successful_view, name="payment_successful_view"),
    path("api/check-payment/<int:order_id>/", views.check_payment_status, name="check_payment_status"),
    path("send-message/", views.send_pharmacist_message, name="send_message"),
    path("my-messages/",
     views.user_messages,
     name="user_messages"),
    path("profile/", views.user_profile, name="user_profile"),

    # ================== ADMIN ORDERS ==================
    path('admin/orders/', views.admin_orders, name='admin_orders'),
    path('admin/manage-orders/', views.admin_orders, name='admin_manage_orders'),
    path('admin/walkin-order/', views.walkin_order, name='walkin_order'),

    path(
        'admin/update-order/<int:order_id>/',
        views.update_order_status,
        name='admin_order_update'
    ),

    path(
        'admin/generate-bill/<int:order_id>/',
        views.admin_generate_bill,
        name='admin_generate_bill'
    ),

    path(
        'admin/bill-success/<int:order_id>/',
        views.admin_bill_success,
        name='admin_bill_success'
    ),

    path(
        'admin/billing/<int:order_id>/',
        views.billing_preview,
        name='admin_billing'
    ),
    path(
        'admin/delete-order/<int:order_id>/',
        views.admin_delete_order,
        name='admin_delete_order'
    ),

    # ================== ADMIN MANAGEMENT ==================
    path('admin-medicines/', views.admin_medicines, name='admin_medicines'),
    path('admin-inventory/', views.admin_inventory, name='admin_inventory'),
    path('admin-inventory/update/<int:pk>/', views.admin_update_inventory, name='admin_update_inventory'),

    path('admin-reports/', views.admin_reports, name='admin_reports'),
    path('admin-reports/export/', views.export_report_pdf, name='export_report_pdf'),


# -------- ADMIN USER MANAGEMENT --------
path('admin/users/', views.admin_users, name='admin_users'),
path('admin/users/toggle/<int:user_id>/', views.admin_toggle_user, name='admin_toggle_user'),
path('admin/users/delete/<int:user_id>/', views.admin_delete_user, name='admin_delete_user'),

path(
    'admin/order-detail/<int:order_id>/',
    views.admin_order_detail,
    name='admin_order_detail'
),


path(
    'admin/delete-medicine/<int:medicine_id>/',
    views.delete_medicine,
    name='delete_medicine'
),

path(
    'admin/edit-medicine/<int:id>/',
    views.edit_medicine,
    name='edit_medicine'
),

path('admin-inventory/export/', views.export_inventory_pdf, name='export_inventory_pdf'),

path("admin/add-item/<int:order_id>/", views.add_order_item, name="add_order_item"),

path("admin-messages/", views.admin_messages, name="admin_messages"),
path("admin-delete-message/<int:message_id>/", views.admin_delete_message, name="admin_delete_message"),
path("admin-reply/<int:message_id>/",
     views.admin_reply_message,
     name="admin_reply_message"),




]
