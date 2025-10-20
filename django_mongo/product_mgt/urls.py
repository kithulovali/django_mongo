from django.urls import path 
from . import views
urlpatterns = [
    
    path("",views.HomeProducts, name="HomeProducts"),
    path("register/",views.registeruser,name="register"),
    path('add/', views.add_product, name='add_product'),
    path('list/', views.list_products, name='list_products'),
    path('edit/<str:product_id>/', views.edit_product, name='edit_product'),
    path('delete/<str:product_id>/', views.delete_product, name='delete_product'),
]
