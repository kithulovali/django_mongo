from mongoengine import Document, StringField, FloatField, IntField, BooleanField, DateTimeField
import datetime

class Product(Document):
    name = StringField(required=True, max_length=200)
    description = StringField()
    price = FloatField(required=True)
    quantity = IntField(default=0)
    category = StringField()
    is_available = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.datetime.utcnow)
