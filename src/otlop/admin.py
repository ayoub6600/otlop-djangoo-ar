from django.contrib import admin
from .models import Order, DeliveryPerson

admin.site.register(Order)
admin.site.register(DeliveryPerson)