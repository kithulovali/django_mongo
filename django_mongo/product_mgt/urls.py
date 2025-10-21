from django.urls import path
from . import views

urlpatterns = [
    # -------------------------
    # Home & Registration
    # -------------------------
    path('', views.HomeProducts, name='home'),
    path('register/', views.registeruser, name='register'),

    # -------------------------
    # Superuser: Product CRUD
    # -------------------------
    path('products/add/', views.add_product, name='add_product'),
    path('products/', views.list_products, name='list_products'),
    path('products/edit/<str:product_id>/', views.edit_product, name='edit_product'),
    path('products/delete/<str:product_id>/', views.delete_product, name='delete_product'),

    # -------------------------
    # Simple Users: View Products & Orders
    # -------------------------
    path('products/all/', views.all_products, name='all_products'),
    path('products/order/<str:product_id>/', views.place_order, name='place_order'),
    path('orders/cancel/<str:order_id>/', views.cancel_order, name='cancel_order'),
    path('products/subscribe/<str:product_id>/', views.subscribe_product, name='subscribe_product'),
    path('subscriptions/unsubscribe/<str:sub_id>/', views.unsubscribe_product, name='unsubscribe_product'),
    path("order/receipt/<str:order_id>/", views.order_receipt, name="order_receipt"),
    path('my/orders/', views.my_orders, name='my_orders'),
    path('my/subscriptions/', views.my_subscriptions, name='my_subscriptions'),
    path("order/receipt/<str:order_id>/", views.order_receipt, name="order_receipt"),
    path("subscription/receipt/<str:sub_id>/", views.subscription_receipt, name="subscription_receipt"),
    path("my_receipts/", views.my_receipts, name="my_receipts"),


    # -------------------------
    # Staff: Manage Orders & Subscriptions
    # -------------------------
    path('staff/orders/', views.manage_orders, name='manage_orders'),
    path('staff/orders/<str:order_id>/<str:action>/', views.update_order_status, name='update_order_status'),

    path('staff/subscriptions/', views.manage_subscriptions, name='manage_subscriptions'),
    path('staff/subscriptions/<str:sub_id>/<str:action>/', views.update_subscription_status, name='update_subscription_status'),
]
