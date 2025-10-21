from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import Http404
from .models import Product, Order, Subscription
from .form import OrderForm, SubscriptionForm ,ProductForm 
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import user_passes_test

# -----------------------------------
# Superuser decorator
# -----------------------------------
def superuser_required(view_func):
    return user_passes_test(lambda u: u.is_superuser, login_url='login')(view_func)

# -----------------------------------
# Home & registration
# -----------------------------------
def HomeProducts(request):
    return render(request, "products_mgt/HomeProducts.html")

def registeruser(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("HomeProducts")
    else:
        form = UserCreationForm()
    return render(request, "products_mgt/sign_up.html", {"form": form})

# -----------------------------------
# Superuser: Product CRUD
# -----------------------------------
@superuser_required
def add_product(request):
    if request.method == "POST":
        form = ProductForm(request.POST)
        if form.is_valid():
            Product(**form.cleaned_data).save()
            return redirect("list_products")
    else:
        form = ProductForm()
    return render(request, "products_mgt/add_products.html", {"form": form})

@superuser_required
def list_products(request):
    products = Product.objects.all()
    return render(request, "products_mgt/list_products.html", {"products": products})

@superuser_required
def edit_product(request, product_id):
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        raise Http404("Product not found")

    if request.method == "POST":
        form = ProductForm(request.POST)
        if form.is_valid():
            for field, value in form.cleaned_data.items():
                setattr(product, field, value)
            product.save()
            return redirect("list_products")
    else:
        form = ProductForm(initial=product.to_mongo().to_dict())
    return render(request, "products_mgt/edit_product.html", {"form": form, "product": product})

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

# -----------------------------------
# Simple users: View products
# -----------------------------------
@login_required
def all_products(request):
    products = Product.objects.all()
    return render(request, "products_mgt/all_products.html", {"products": products})

# -----------------------------------
# Simple users: Place orders
# -----------------------------------
@login_required
def place_order(request, product_id):
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        raise Http404("Product not found")

    if request.method == "POST":
        form = OrderForm(request.POST)
        if form.is_valid():
            quantity = form.cleaned_data['quantity']

            # Check if enough stock
            if product.quantity < quantity:
                form.add_error(None, "Not enough stock available.")
            else:
                # Create order
                order = Order(
                    user_id=str(request.user.id),
                    product=product,
                    quantity=quantity
                )
                order.save()

                # Decrement stock
                product.quantity -= quantity
                product.save()

                # Redirect to receipt
                return redirect("order_receipt", order_id=str(order.id))
    else:
        form = OrderForm()

    return render(request, "products_mgt/place_order.html", {"form": form, "product": product})



@login_required
def cancel_order(request, order_id):
    try:
        order = Order.objects.get(id=order_id, user_id=str(request.user.id))
    except Order.DoesNotExist:
        raise Http404("Order not found")
    if request.method == "POST":
        order.delete()
        return redirect("my_orders")
    return render(request, "products_mgt/cancel_order.html", {"order": order})

# -----------------------------------
# Simple users: Subscribe / Unsubscribe
# -----------------------------------
@login_required
def subscribe_product(request, product_id):
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        raise Http404("Product not found")

    if request.method == "POST":
        form = SubscriptionForm(request.POST)
        if form.is_valid():
            
            sub = Subscription(user_id=str(request.user.id), product=product)
            sub.save()

            return redirect("subscription_receipt", sub_id=str(sub.id))
    else:
        form = SubscriptionForm()

    return render(request, "products_mgt/subscribe_product.html", {"form": form, "product": product})



@login_required
def unsubscribe_product(request, sub_id):
    try:
        sub = Subscription.objects.get(id=sub_id, user_id=str(request.user.id))
    except Subscription.DoesNotExist:
        raise Http404("Subscription not found")
    if request.method == "POST":
        sub.delete()
        return redirect("my_subscriptions")
    return render(request, "products_mgt/unsubscribe_product.html", {"subscription": sub})

# -----------------------------------
# Simple users: View their orders/subscriptions
# -----------------------------------
@login_required
def my_orders(request):
    orders = Order.objects(user_id=str(request.user.id))
    return render(request, "products_mgt/my_orders.html", {"orders": orders})

@login_required
def my_subscriptions(request):
    subs = Subscription.objects(user_id=str(request.user.id))
    return render(request, "products_mgt/my_subscriptions.html", {"subscriptions": subs})

# -----------------------------------
# Staff users: Accept/Reject Orders & Subscriptions
# -----------------------------------
@staff_member_required
def manage_orders(request):
    orders = Order.objects(status="pending")
    return render(request, "products_mgt/manage_orders.html", {"orders": orders})

@staff_member_required
def update_order_status(request, order_id, action):
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        raise Http404("Order not found")
    if action in ["accepted", "rejected"]:
        order.status = action
        order.save()
    return redirect("manage_orders")

@staff_member_required
def manage_subscriptions(request):
    subs = Subscription.objects(status="pending")
    return render(request, "products_mgt/manage_subscriptions.html", {"subscriptions": subs})

@staff_member_required
def update_subscription_status(request, sub_id, action):
    try:
        sub = Subscription.objects.get(id=sub_id)
    except Subscription.DoesNotExist:
        raise Http404("Subscription not found")
    if action in ["accepted", "rejected"]:
        sub.status = action
        sub.save()
    return redirect("manage_subscriptions")

@login_required
def order_receipt(request, order_id):
    try:
        order = Order.objects.get(id=order_id, user_id=str(request.user.id))
    except Order.DoesNotExist:
        raise Http404("Order not found")

    product = order.product
    total_price = order.quantity * product.price

    context = {
        "order": order,
        "product": product,
        "total_price": total_price
    }

    return render(request, "products_mgt/order_receipt.html", context)

@login_required
def subscription_receipt(request, sub_id):
    try:
        sub = Subscription.objects.get(id=sub_id, user_id=str(request.user.id))
    except Subscription.DoesNotExist:
        raise Http404("Subscription not found")

    product = sub.product

    context = {
        "subscription": sub,
        "product": product
    }

    return render(request, "products_mgt/subscription_receipt.html", context)

@login_required
def my_receipts(request):
    orders = Order.objects(user_id=str(request.user.id)).order_by('-created_at')
    subscriptions = Subscription.objects(user_id=str(request.user.id)).order_by('-created_at')

    return render(request, "products_mgt/my_receipts.html", {
        "orders": orders,
        "subscriptions": subscriptions
    })
