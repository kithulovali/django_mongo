from django import forms

class ProductForm(forms.Form):
    name = forms.CharField(max_length=200)
    description = forms.CharField(widget=forms.Textarea, required=False)
    price = forms.FloatField()
    quantity = forms.IntegerField(required=False, initial=0)
    category = forms.CharField(required=False)
    is_available = forms.BooleanField(required=False, initial=True)

class OrderForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, initial=1)


class SubscriptionForm(forms.Form):
    # no extra fields, just confirm subscription
    confirm = forms.BooleanField(label="Subscribe to this product?", required=True)