from django.contrib import admin
from mptt.admin import MPTTModelAdmin
from .models import Category, Product, Order, OrderItem, Customer

admin.site.register(Category, MPTTModelAdmin)
admin.site.register(Product)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Customer)
