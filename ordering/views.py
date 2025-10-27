from django.shortcuts import render, redirect
from django.http import HttpResponse, Http404, JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login as auth_login
from bson import ObjectId
from mongoengine.queryset.visitor import Q

from .models import Product, Customer, Order, Receipt, Suggestion
from .forms import CheckoutForm, ProductForm, ProfileForm, SuggestionForm
from .utils import generate_order_number, generate_receipt_number, cart_total, start_order_automation
from .gemini_ai import KFCGeminiAI


def is_staff(user):
    return user.is_authenticated and user.is_staff


def _get_cart(request):
    cart = request.session.get('cart', {})
    return cart


def _key_email_for_user(user):
    return (user.email or (f"user-{getattr(user, 'id', '') or user.get_username()}@kfc.local")) if user else None


def _customers_for_user(user):
    if not user or not user.is_authenticated:
        return []
    key_email = _key_email_for_user(user)
    emails = set()
    if key_email:
        emails.add(key_email)
    if getattr(user, 'email', None):
        emails.add(user.email)
    # Find a primary customer to extract phone (if any)
    primary = Customer.objects(email__in=list(emails)).first()
    phone = primary.phone if primary and primary.phone else None
    uname = user.get_username() or None
    query = Q(email__in=list(emails))
    if phone:
        query = query | Q(phone=phone)
    if uname:
        query = query | Q(name__iexact=uname)
    return list(Customer.objects(query))


def _save_cart(request, cart):
    request.session['cart'] = cart
    request.session.modified = True


def menu(request):
    query = request.GET.get('q', '')
    category = request.GET.get('category')
    q = Q(is_available=True)
    if query:
        q &= (Q(name__icontains=query) | Q(description__icontains=query))
    if category:
        q &= Q(category=category)
    products = Product.objects(q).order_by('-created_at')
    categories = ['chicken', 'burgers', 'sides', 'drinks', 'desserts']
    return render(request, 'kfc/customers/menu.html', {
        'products': products,
        'query': query,
        'category': category,
        'categories': categories,
    })


def product_image(request, product_id):
    try:
        product = Product.objects.get(id=ObjectId(product_id))
    except Exception:
        raise Http404()
    if not product.image:
        raise Http404()
    gridout = product.image.get()
    content = gridout.read()
    content_type = getattr(gridout, 'content_type', 'application/octet-stream')
    return HttpResponse(content, content_type=content_type)

@require_POST
def add_to_cart(request, product_id):
    qty = max(1, int(request.POST.get('quantity', '1')))
    try:
        product = Product.objects.get(id=ObjectId(product_id))
    except Exception:
        raise Http404()
    # If out of stock or not available, ignore add
    if not product.is_available or int(product.stock_quantity or 0) <= 0:
        return redirect('view_cart')
    cart = _get_cart(request)
    pid = str(product.id)
    current_qty = int(cart.get(pid, {}).get('quantity', 0))
    max_addable = max(0, int(product.stock_quantity or 0) - current_qty)
    if max_addable <= 0:
        return redirect('view_cart')
    add_qty = min(qty, max_addable)
    item = cart.get(pid, {'name': product.name, 'price': float(product.price), 'quantity': 0})
    item['quantity'] = int(item['quantity']) + add_qty
    cart[pid] = item
    _save_cart(request, cart)
    return redirect('view_cart')


def view_cart(request):
    cart = _get_cart(request)
    items = []
    total = 0.0
    for pid, item in cart.items():
        subtotal = float(item['price']) * int(item['quantity'])
        total += subtotal
        items.append({
            'product_id': pid,
            'name': item['name'],
            'price': float(item['price']),
            'quantity': int(item['quantity']),
            'subtotal': subtotal,
        })
    return render(request, 'kfc/customers/cart.html', {'items': items, 'total': total})

@require_POST
def update_cart(request):
    cart = _get_cart(request)
    for pid, qty in request.POST.items():
        if not pid.startswith('qty_'):
            continue
        pid_real = pid.replace('qty_', '')
        try:
            qty_val = max(0, int(qty))
        except ValueError:
            qty_val = 0
        # Cap by stock if product exists
        try:
            prod = Product.objects.get(id=ObjectId(pid_real))
            if prod and prod.stock_quantity is not None:
                qty_val = min(qty_val, int(prod.stock_quantity))
        except Exception:
            pass
        if qty_val <= 0:
            cart.pop(pid_real, None)
        else:
            if pid_real in cart:
                cart[pid_real]['quantity'] = qty_val
    _save_cart(request, cart)
    return redirect('view_cart')


@login_required
def checkout(request):
    cart = _get_cart(request)
    if not cart:
        return redirect('menu')
    items = [{
        'product_id': pid,
        'name': item['name'],
        'quantity': item['quantity'],
        'price': item['price'],
    } for pid, item in cart.items()]
    total = cart_total(items)

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            # Determine customer identity
            user = request.user if hasattr(request, 'user') else None
            if user and user.is_authenticated and user.email:
                cust_email = user.email
                cust_name = user.get_username() or 'Customer'
            else:
                # Ensure session key exists
                if not request.session.session_key:
                    request.session.save()
                cust_email = f"guest-{request.session.session_key}@kfc.local"
                cust_name = 'Guest'

            customer = Customer.objects(email=cust_email).first()
            if not customer:
                customer = Customer(
                    name=cust_name,
                    email=cust_email,
                    phone=form.cleaned_data.get('phone', ''),
                    address=form.cleaned_data.get('address', ''),
                )
                customer.save()
            else:
                # Update latest phone/address
                customer.phone = form.cleaned_data.get('phone', customer.phone)
                # If name is missing or generic, set it to the authenticated username
                if user and user.is_authenticated:
                    nm = (customer.name or '').strip().lower()
                    if not nm or nm in ['guest', 'customer']:
                        customer.name = cust_name
                if form.cleaned_data.get('address'):
                    customer.address = form.cleaned_data.get('address')
                customer.save()
            # Stock validation and decrement
            insufficient = []
            products_to_update = []
            for it in items:
                try:
                    prod = Product.objects.get(id=ObjectId(it['product_id']))
                except Exception:
                    insufficient.append(f"Product not found: {it['name']}")
                    continue
                qty = int(it['quantity'])
                if prod.stock_quantity is not None and prod.stock_quantity < qty:
                    insufficient.append(f"Not enough stock for {prod.name} (have {prod.stock_quantity}, need {qty})")
                else:
                    products_to_update.append((prod, qty))
            if insufficient:
                # Show error on checkout page
                error_msg = "; ".join(insufficient)
                return render(request, 'kfc/customers/checkout.html', {
                    'form': form,
                    'items': items,
                    'total': total,
                    'error': error_msg,
                })

            # Decrement stock
            for prod, qty in products_to_update:
                try:
                    prod.stock_quantity = int(prod.stock_quantity or 0) - qty
                    if prod.stock_quantity <= 0:
                        prod.stock_quantity = 0
                        prod.is_available = False
                    prod.save()
                except Exception:
                    pass

            order = Order(
                order_number=generate_order_number(),
                customer=customer,
                items=items,
                total_amount=total,
                special_instructions='',
            )
            order.save()

            # AI analysis
            ai = KFCGeminiAI()
            analysis = ai.analyze_kfc_order({'items': items, 'total': total, 'customer': customer.email})
            order.gemini_analysis = analysis
            order.save()

            # Start background automation to move status from pending -> completed over time
            try:
                start_order_automation(order)
            except Exception:
                pass

            # Clear cart
            _save_cart(request, {})
            return redirect('order_success', order_number=order.order_number)
    else:
        # Prefill phone from profile if available
        initial = {}
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            key_email = _key_email_for_user(user)
            cust = Customer.objects(email=key_email).first()
            if cust and cust.phone:
                initial['phone'] = cust.phone
        form = CheckoutForm(initial=initial)

    return render(request, 'kfc/customers/checkout.html', {'form': form, 'items': items, 'total': total})


def order_success(request, order_number):
    order = Order.objects(order_number=order_number).first()
    if not order:
        raise Http404()
    return render(request, 'kfc/customers/order_success.html', {'order': order})


def order_history(request):
    email = request.GET.get('email')
    orders = []
    if email:
        cust = Customer.objects(email=email).first()
        if cust:
            orders = Order.objects(customer=cust).order_by('-created_at')
    return render(request, 'kfc/customers/order_history.html', {'orders': orders, 'email': email or ''})

@login_required
def my_orders(request):
    user = request.user
    customers = _customers_for_user(user)
    orders = Order.objects(customer__in=customers).order_by('-created_at') if customers else []
    return render(request, 'kfc/customers/order_history.html', {'orders': orders, 'email': user.email if user.email else ''})


def receipt_view(request, order_number):
    order = Order.objects(order_number=order_number).first()
    if not order:
        raise Http404()
    # Generate or fetch receipt
    receipt = Receipt.objects(order=order).first()
    if not receipt:
        ai = KFCGeminiAI()
        receipt_text = ai.generate_kfc_receipt({'order_number': order.order_number, 'total': order.total_amount, 'items': order.items})
        receipt = Receipt(order=order, receipt_number=generate_receipt_number(), receipt_data={'text': receipt_text})
        receipt.save()
    cust = order.customer
    avatar_url = 'https://via.placeholder.com/64x64?text=Me'
    if cust and getattr(cust, 'avatar', None):
        try:
            # Only use avatar URL if a file is stored
            grid_id = getattr(cust.avatar, 'grid_id', None)
            if grid_id:
                avatar_url = f"/avatar/{cust.id}/"
        except Exception:
            pass
    email_display = ''
    if cust and getattr(cust, 'email', None):
        email_display = '' if cust.email.endswith('@kfc.local') else cust.email
    phone_display = getattr(cust, 'phone', '') if cust else ''
    name_display = getattr(cust, 'name', 'Customer') if cust else 'Customer'
    return render(request, 'kfc/customers/receipt.html', {
        'order': order,
        'receipt': receipt,
        'customer_avatar_url': avatar_url,
        'customer_email_display': email_display,
        'customer_phone_display': phone_display,
        'customer_name_display': name_display,
    })


def order_status_api(request, order_number):
    order = Order.objects(order_number=order_number).first()
    if not order:
        return JsonResponse({'error': 'not_found'}, status=404)
    return JsonResponse({
        'order_number': order.order_number,
        'status': order.status,
        'updated_at': order.updated_at.isoformat() if order.updated_at else None,
    })

@login_required
def profile(request):
    user = request.user
    # Ensure a corresponding Customer exists
    key_email = _key_email_for_user(user)
    cust = Customer.objects(email=key_email).first()
    if not cust:
        cust = Customer(name=user.get_username() or 'Customer', email=key_email)
        cust.save()
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES)
        if form.is_valid() and cust:
            phone = form.cleaned_data.get('phone')
            if phone is not None:
                cust.phone = phone
            avatar = request.FILES.get('avatar')
            if avatar:
                # Replace existing avatar
                if cust.avatar:
                    try:
                        cust.avatar.delete()
                    except Exception:
                        pass
                cust.avatar.put(avatar, content_type=avatar.content_type, filename=avatar.name)
            cust.save()
            return redirect('profile')
    else:
        initial = {'phone': cust.phone if cust else ''}
        form = ProfileForm(initial=initial)
    # Stats across all linked customers (email/synthetic/phone)
    customers = _customers_for_user(user)
    if cust and cust not in customers:
        customers.append(cust)
    orders_qs = Order.objects(customer__in=customers) if customers else Order.objects.none()
    completed_count = orders_qs.filter(status='completed').count() if customers else 0
    in_progress_count = orders_qs.filter(status__in=['pending','confirmed','preparing','ready']).count() if customers else 0
    total_spent = sum(o.total_amount for o in orders_qs) if customers else 0
    return render(request, 'kfc/customers/profile.html', {
        'form': form,
        'customer': cust,
        'completed_count': completed_count,
        'in_progress_count': in_progress_count,
        'total_spent': total_spent,
    })

def customer_avatar(request, customer_id):
    try:
        c = Customer.objects.get(id=ObjectId(customer_id))
    except Exception:
        raise Http404()
    if not c.avatar:
        raise Http404()
    gridout = c.avatar.get()
    return HttpResponse(gridout.read(), content_type=getattr(gridout, 'content_type', 'image/jpeg'))


def suggest_product(request):
    initial = {}
    if request.user.is_authenticated:
        initial['submitted_by'] = request.user.email or request.user.get_username()
    if request.method == 'POST':
        form = SuggestionForm(request.POST, request.FILES)
        if form.is_valid():
            s = Suggestion(
                name=form.cleaned_data['name'],
                description=form.cleaned_data.get('description', ''),
                category=form.cleaned_data.get('category') or None,
                price_suggestion=float(form.cleaned_data['price_suggestion']) if form.cleaned_data.get('price_suggestion') is not None else None,
                submitted_by=(request.user.email if request.user.is_authenticated else 'guest'),
            )
            img = request.FILES.get('image')
            if img:
                s.image.put(img, content_type=img.content_type, filename=img.name)
            s.save()
            return render(request, 'kfc/customers/suggest_success.html', {'suggestion': s})
    else:
        form = SuggestionForm()
    return render(request, 'kfc/customers/suggest.html', {'form': form})


@login_required
@user_passes_test(is_staff)
def admin_suggestions(request):
    # Handle approve/reject actions
    if request.method == 'POST':
        sid = request.POST.get('sid')
        action = request.POST.get('action')
        s = Suggestion.objects(id=sid).first()
        if s and action in ['approve', 'reject']:
            if action == 'approve':
                # create a basic Product from suggestion
                p = Product(
                    name=s.name,
                    description=s.description or '',
                    price=float(s.price_suggestion or 0.0),
                    category=s.category or 'sides',
                    stock_quantity=0,
                    is_available=True,
                )
                if s.image:
                    try:
                        grid = s.image.get()
                        p.image.put(grid.read(), content_type=getattr(grid, 'content_type', 'image/jpeg'), filename=getattr(grid, 'filename', 'suggestion.jpg'))
                    except Exception:
                        pass
                p.save()
                s.status = 'approved'
            else:
                s.status = 'rejected'
            s.save()
    suggestions = Suggestion.objects().order_by('-created_at')
    return render(request, 'kfc/admin/suggestions.html', {'suggestions': suggestions})


@login_required
def my_receipts(request):
    user = request.user
    key_email = user.email or (f"user-{getattr(user, 'id', '') or user.get_username()}@kfc.local")
    cust = Customer.objects(email=key_email).first()
    orders = Order.objects(customer=cust) if cust else []
    receipts = Receipt.objects(order__in=list(orders)).order_by('-generated_at') if orders else []
    return render(request, 'kfc/customers/receipts_list.html', {
        'receipts': receipts,
    })

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            if user.is_staff:
                return redirect('admin_dashboard')
            return redirect('menu')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})

# Admin views
@login_required
@user_passes_test(is_staff)
def admin_dashboard(request):
    total_orders = Order.objects.count()
    completed = Order.objects(status='completed').count()
    pending = Order.objects(status='pending').count()
    revenue = sum(o.total_amount for o in Order.objects())
    return render(request, 'kfc/admin/dashboard.html', {
        'total_orders': total_orders,
        'completed': completed,
        'pending': pending,
        'revenue': revenue,
    })

@login_required
@user_passes_test(is_staff)
def admin_products(request):
    products = Product.objects().order_by('-created_at')
    return render(request, 'kfc/admin/products.html', {'products': products})

@login_required
@user_passes_test(is_staff)
def admin_upload_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            p = Product(
                name=form.cleaned_data['name'],
                description=form.cleaned_data.get('description', ''),
                price=float(form.cleaned_data['price']),
                category=form.cleaned_data['category'],
                stock_quantity=form.cleaned_data['stock_quantity'],
                is_available=form.cleaned_data.get('is_available', False),
            )
            file = request.FILES.get('image')
            if file:
                # store in GridFS
                p.image.put(file, content_type=file.content_type, filename=file.name)
            p.save()
            return redirect('admin_products')
    else:
        form = ProductForm()
    return render(request, 'kfc/admin/upload_product.html', {'form': form})


@login_required
@user_passes_test(is_staff)
def admin_edit_product(request, product_id):
    try:
        p = Product.objects.get(id=ObjectId(product_id))
    except Exception:
        raise Http404()
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            p.name = form.cleaned_data['name']
            p.description = form.cleaned_data.get('description', '')
            p.price = float(form.cleaned_data['price'])
            p.category = form.cleaned_data['category']
            p.stock_quantity = form.cleaned_data['stock_quantity']
            p.is_available = form.cleaned_data.get('is_available', False)
            file = request.FILES.get('image')
            if file:
                if p.image:
                    try:
                        p.image.delete()
                    except Exception:
                        pass
                p.image.put(file, content_type=file.content_type, filename=file.name)
            # Auto-toggle availability when stock zero
            if p.stock_quantity <= 0:
                p.is_available = False
            p.save()
            return redirect('admin_products')
    else:
        initial = {
            'name': p.name,
            'description': p.description,
            'price': p.price,
            'category': p.category,
            'stock_quantity': p.stock_quantity,
            'is_available': p.is_available,
        }
        form = ProductForm(initial=initial)
    return render(request, 'kfc/admin/edit_product.html', {'form': form, 'product': p})


@login_required
@user_passes_test(is_staff)
def admin_delete_product(request, product_id):
    if request.method != 'POST':
        raise Http404()
    try:
        p = Product.objects.get(id=ObjectId(product_id))
    except Exception:
        raise Http404()
    try:
        if p.image:
            p.image.delete()
    except Exception:
        pass
    p.delete()
    return redirect('admin_products')

@login_required
@user_passes_test(is_staff)
def admin_orders(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'backfill_names':
            # Heuristic backfill: set customer.name if placeholder
            customers = Customer.objects()
            # Build phone->best_name map from customers with real names
            phone_name = {}
            for c in customers:
                nm = (getattr(c, 'name', '') or '').strip()
                if nm and nm.lower() not in ['guest', 'customer'] and getattr(c, 'phone', None):
                    phone_name[c.phone] = nm
            for c in customers:
                try:
                    nm = (getattr(c, 'name', '') or '').strip().lower()
                    if nm and nm not in ['guest', 'customer']:
                        continue
                    email = (getattr(c, 'email', '') or '').strip()
                    new_name = None
                    # If real email, take local-part
                    if email and not email.endswith('@kfc.local') and '@' in email:
                        new_name = email.split('@', 1)[0]
                    # Else if phone matches a known named customer, copy
                    if not new_name and getattr(c, 'phone', None) and c.phone in phone_name:
                        new_name = phone_name[c.phone]
                    if new_name:
                        c.name = new_name
                        c.save()
                except Exception:
                    pass
        else:
            order_id = request.POST.get('order_id')
            status = request.POST.get('status')
            order = Order.objects(id=order_id).first()
            if order and status in ['pending','confirmed','preparing','ready','completed','cancelled']:
                order.status = status
                order.save()
    orders = Order.objects().order_by('-created_at')
    def _display_name(cust):
        try:
            name = (getattr(cust, 'name', '') or '').strip()
            email = (getattr(cust, 'email', '') or '').strip()
            # Prefer a real name if it's not a generic placeholder
            if name and name.lower() not in ['guest', 'customer']:
                return name
            # If email looks real (not kfc.local), use local-part as username
            if email and not email.endswith('@kfc.local') and '@' in email:
                return email.split('@', 1)[0]
            # Otherwise fallback to name or 'Customer'
            return name or 'Customer'
        except Exception:
            return 'Customer'
    # Attach display_name for template use without changing DB
    for o in orders:
        try:
            o.display_name = _display_name(o.customer)
        except Exception:
            o.display_name = 'Customer'
    status_list = ['pending','confirmed','preparing','ready','completed','cancelled']
    return render(request, 'kfc/admin/orders.html', {'orders': orders, 'status_list': status_list})

@login_required
@user_passes_test(is_staff)
def admin_analytics(request):
    ai = KFCGeminiAI()
    sales_data = [{
        'order_number': o.order_number,
        'total': o.total_amount,
        'status': o.status,
        'created_at': o.created_at.isoformat(),
    } for o in Order.objects()]
    period = request.GET.get('period', 'weekly')
    report = ai.generate_kfc_business_report(sales_data, period=period)
    period_list = ['daily', 'weekly', 'monthly', 'quarterly']
    return render(request, 'kfc/admin/analytics.html', {'report': report, 'period_list': period_list, 'period': period})
