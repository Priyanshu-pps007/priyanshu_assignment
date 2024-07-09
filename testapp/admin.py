from django.contrib import admin
from .models import *

admin.site.register(Vendor)
admin.site.register(Purchase_order)
admin.site.register(Historical_performance)

# Register your models here.
