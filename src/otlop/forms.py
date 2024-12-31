from django import forms
from .models import Order, DeliveryPerson
from django.contrib.auth.models import User

class CustomUserCreationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'password', 'email']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['customer_name', 'customer_area', 'restaurant_name', 'restaurant_area', 
                  'delivery_price', 'order_price', 'notes', 'delivery_status', 'delivery_person']

    # تخصيص بعض الحقول
    customer_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'placeholder': 'اسم العميل'}))
    customer_area = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'placeholder': 'منطقة العميل'}))
    restaurant_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'placeholder': 'اسم المطعم'}))
    restaurant_area = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'placeholder': 'منطقة المطعم'}))
    delivery_price = forms.DecimalField(max_digits=10, decimal_places=2, widget=forms.NumberInput(attrs={'placeholder': 'سعر التوصيل'}))
    order_price = forms.DecimalField(max_digits=10, decimal_places=2, widget=forms.NumberInput(attrs={'placeholder': 'سعر الطلبية'}))
    notes = forms.CharField(widget=forms.Textarea(attrs={'placeholder': 'ملاحظات'}), required=False)
    
    # حقل السائق (delivery_person) يتم تحديده من خلال خيارات السائقين في النظام
    delivery_person = forms.ModelChoiceField(queryset=DeliveryPerson.objects.all(), required=False, empty_label="اختيار السائق")

    # حقل حالة الطلب (delivery_status) يمكن تخصيصه إذا لزم الأمر
    delivery_status = forms.ChoiceField(choices=Order.DELIVERY_STATUS_CHOICES, required=False, initial='Pending')