from django.contrib import admin
from .models import Medicine
from .models import PrescriptionOrder


@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'stock', 'minimum_stock', 'expiry_date')
    search_fields = ('name', 'batch_number')




@admin.register(PrescriptionOrder)
class PrescriptionOrderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'patient_name',
        'mobile',
        'status',
        'total_amount',
        'created_at'
    )
    list_filter = ('status',)
    search_fields = ('patient_name', 'mobile')



