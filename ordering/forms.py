from django import forms

CATEGORY_CHOICES = [
    ('chicken', 'Chicken'),
    ('burgers', 'Burgers'),
    ('sides', 'Sides'),
    ('drinks', 'Drinks'),
    ('desserts', 'Desserts'),
]

class CheckoutForm(forms.Form):
    phone = forms.CharField(max_length=20, required=True)
    address = forms.CharField(widget=forms.HiddenInput, required=False)

class ProductForm(forms.Form):
    name = forms.CharField(max_length=200)
    description = forms.CharField(widget=forms.Textarea, required=False)
    price = forms.DecimalField(max_digits=8, decimal_places=2)
    category = forms.ChoiceField(choices=CATEGORY_CHOICES)
    stock_quantity = forms.IntegerField(min_value=0)
    image = forms.FileField(required=False)
    is_available = forms.BooleanField(required=False)


class ProfileForm(forms.Form):
    phone = forms.CharField(max_length=20, required=False)
    avatar = forms.FileField(required=False)


class SuggestionForm(forms.Form):
    name = forms.CharField(max_length=200)
    description = forms.CharField(widget=forms.Textarea, required=False)
    category = forms.ChoiceField(choices=CATEGORY_CHOICES, required=False)
    price_suggestion = forms.DecimalField(max_digits=8, decimal_places=2, required=False)
    image = forms.FileField(required=False)
