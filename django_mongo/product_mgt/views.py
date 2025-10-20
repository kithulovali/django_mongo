from django.shortcuts import render , redirect ,  get_object_or_404
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import login
from .models import Product
from .form import ProductForm
from django.http import Http404
# Create your views here.


def superuser_required(view_func):
    return user_passes_test(lambda u: u.is_superuser, login_url='login')(view_func)

def HomeProducts(request):
    return render(request , "products_mgt/HomeProducts.html")

def registeruser(request):
    if request.method =="POST":
        form = UserCreationForm(request.POST)
        if form.is_valid :
           user = form.save()
           login(request,user)
           return redirect("HomeProducts")
    
    else:
        form = UserCreationForm()
    return render(request,"products_mgt/sign_up.html", {"form":form}) 

# adding products
@superuser_required
def add_product(request):
    if request.method == "POST":
        form = ProductForm(request.POST)
        if form.is_valid():
            # Build Product safely
            product = Product(
                name=form.cleaned_data['name'],
                description=form.cleaned_data.get('description', ''),
                price=form.cleaned_data['price'],
                quantity=form.cleaned_data.get('quantity', 0),
                category=form.cleaned_data.get('category', ''),
                is_available=form.cleaned_data.get('is_available', True),
            )
            product.save()
            return redirect("list_products")
    else:
        form = ProductForm()
    return render(request, "products_mgt/add_products.html", {"form": form})

@superuser_required
def list_products(request):
    products = Product.objects.all()
    return render(request, "products_mgt/list_products.html", {"products": products})

# delete a product
@superuser_required
def delete_product(request, product_id):
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        raise Http404("Product not found")

    if request.method == "POST":
        product.delete()
        return redirect("list_products")

    return render(request, "products_mgt/delete_product.html", {"product": product})

# edit with contructor
@superuser_required
def edit_product(request, product_id):
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        raise Http404("Product not found")

    if request.method == "POST":
        form = ProductForm(request.POST)
        if form.is_valid():
            product.name = form.cleaned_data['name']
            product.description = form.cleaned_data.get('description', '')
            product.price = form.cleaned_data['price']
            product.quantity = form.cleaned_data.get('quantity', 0)
            product.category = form.cleaned_data.get('category', '')
            product.is_available = form.cleaned_data.get('is_available', True)
            product.save()
            return redirect("list_products")
    else:
        form = ProductForm(initial={
            "name": product.name,
            "description": product.description,
            "price": product.price,
            "quantity": product.quantity,
            "category": product.category,
            "is_available": product.is_available,
        })
    return render(request, "products_mgt/edit_product.html", {"form": form, "product": product})
