import datetime
from mongoengine import Document, StringField, IntField, FloatField, DateTimeField, ListField, DictField, FileField, BooleanField, ReferenceField

class Product(Document):
    name = StringField(max_length=200, required=True)
    description = StringField()
    price = FloatField(required=True)
    category = StringField(max_length=100, choices=['chicken', 'burgers', 'sides', 'drinks', 'desserts'])
    stock_quantity = IntField(default=0)
    image = FileField()  # GridFS storage
    is_available = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.datetime.now)

    meta = {'collection': 'kfc_products', 'indexes': ['category', 'name']}

class Customer(Document):
    name = StringField(max_length=100, required=True)
    email = StringField(max_length=150, required=True, unique=True)
    phone = StringField(max_length=20)
    address = StringField()
    avatar = FileField()  # GridFS avatar
    created_at = DateTimeField(default=datetime.datetime.now)

    meta = {'collection': 'kfc_customers'}

class Order(Document):
    ORDER_STATUS = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready for Pickup'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    )

    order_number = StringField(max_length=20, unique=True, required=True)
    customer = ReferenceField(Customer, required=True)
    items = ListField(DictField(), required=True)  # [{product_id, name, quantity, price, image_url}]
    total_amount = FloatField(required=True)
    status = StringField(max_length=20, choices=[s[0] for s in ORDER_STATUS], default='pending')
    special_instructions = StringField()
    created_at = DateTimeField(default=datetime.datetime.now)
    updated_at = DateTimeField(default=datetime.datetime.now)

    gemini_analysis = StringField()
    business_insights = StringField()
    automation_started = BooleanField(default=False)

    meta = {'collection': 'kfc_orders', 'indexes': ['order_number', 'customer', 'status', 'created_at']}

class Receipt(Document):
    order = ReferenceField(Order, required=True)
    receipt_number = StringField(max_length=20, unique=True, required=True)
    receipt_data = DictField(required=True)
    generated_at = DateTimeField(default=datetime.datetime.now)
    is_printed = BooleanField(default=False)

    meta = {'collection': 'kfc_receipts'}


class Suggestion(Document):
    STATUS = (
        ('new', 'New'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    name = StringField(max_length=200, required=True)
    description = StringField()
    category = StringField(max_length=100, choices=['chicken', 'burgers', 'sides', 'drinks', 'desserts'])
    price_suggestion = FloatField()
    image = FileField()  # optional illustrative image
    submitted_by = StringField(max_length=150)  # email or username
    status = StringField(max_length=20, choices=[s[0] for s in STATUS], default='new')
    created_at = DateTimeField(default=datetime.datetime.now)

    meta = {'collection': 'kfc_suggestions', 'indexes': ['status', 'category', 'name']}
