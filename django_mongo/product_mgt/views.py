from django.shortcuts import render

# Create your views here.
def HomeProducts(request):
    return render(request , "products_mgt/HomeProducts.html")