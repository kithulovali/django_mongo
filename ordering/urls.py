from django.urls import path
from . import views

urlpatterns = [
    path('', views.menu, name='menu'),
    path('image/<str:product_id>/', views.product_image, name='product_image'),
    path('cart/add/<str:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.view_cart, name='view_cart'),
    path('cart/update/', views.update_cart, name='update_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('order/success/<str:order_number>/', views.order_success, name='order_success'),
    path('order/status/<str:order_number>/', views.order_status_api, name='order_status_api'),
    path('orders/history/', views.order_history, name='order_history'),
    path('orders/mine/', views.my_orders, name='my_orders'),
    path('receipts/mine/', views.my_receipts, name='my_receipts'),
    path('receipt/<str:order_number>/', views.receipt_view, name='receipt'),
    path('accounts/signup/', views.signup, name='signup'),
    path('profile/', views.profile, name='profile'),
    path('avatar/<str:customer_id>/', views.customer_avatar, name='customer_avatar'),
    path('suggest/', views.suggest_product, name='suggest_product'),

    # Admin
    path('kfc-admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('kfc-admin/products/', views.admin_products, name='admin_products'),
    path('kfc-admin/products/upload/', views.admin_upload_product, name='admin_upload_product'),
    path('kfc-admin/products/<str:product_id>/edit/', views.admin_edit_product, name='admin_edit_product'),
    path('kfc-admin/products/<str:product_id>/delete/', views.admin_delete_product, name='admin_delete_product'),
    path('kfc-admin/orders/', views.admin_orders, name='admin_orders'),
    path('kfc-admin/analytics/', views.admin_analytics, name='admin_analytics'),
    path('kfc-admin/suggestions/', views.admin_suggestions, name='admin_suggestions'),
]
