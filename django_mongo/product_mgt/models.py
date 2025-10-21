from mongoengine import Document, StringField, FloatField, IntField, BooleanField, ReferenceField, DateTimeField
import datetime

# Products
class Product(Document):
    name = StringField(required=True, max_length=200)
    description = StringField()
    price = FloatField(required=True)
    quantity = IntField(default=0)
    category = StringField()
    is_available = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.datetime.now)  

# Orders placed by normal users
class Order(Document):
    user_id = StringField(required=True)
    product = ReferenceField(Product, required=True)
    quantity = IntField(default=1)
    status = StringField(choices=['pending','accepted','rejected'], default='pending')
    created_at = DateTimeField(default=datetime.datetime.now)  

# Subscriptions for products
class Subscription(Document):
    user_id = StringField(required=True)
    product = ReferenceField(Product, required=True)
    status = StringField(choices=['pending','accepted','rejected'], default='pending')
    created_at = DateTimeField(default=datetime.datetime.now)  
