from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta



class Medicine(models.Model):

    CATEGORY_CHOICES = [
        ('Tablets', 'Tablets'),
        ('Syrups', 'Syrups'),
        ('Injections', 'Injections'),
        ('Medical Devices', 'Medical Devices'),
        ('Personal Care', 'Personal Care'),
        ('Other', 'Other'),
    ]

    name = models.CharField(max_length=100)
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default='Other'
    )
    price = models.DecimalField(max_digits=8, decimal_places=2)

    stock = models.IntegerField(default=0)
    minimum_stock = models.IntegerField(default=20)

    batch_number = models.CharField(max_length=50, blank=True, null=True)
    expiry_date = models.DateField(blank=True, null=True)

    prescription_required = models.BooleanField(default=False)
    store_pickup_only = models.BooleanField(default=False)

    def __str__(self):
        return self.name




class PrescriptionOrder(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    patient_name = models.CharField(max_length=100)
    doctor_name = models.CharField(max_length=100, blank=True, null=True)
    mobile = models.CharField(max_length=15)
    prescription_file = models.FileField(upload_to='prescriptions/', blank=True, null=True)
    address = models.TextField()
    pincode = models.CharField(max_length=10)

    status = models.CharField(
        max_length=20,
        choices=[
            ('submitted', 'Prescription Submitted'),
            ('verified', 'Verified'),
            ('pickup_only', 'Store Pickup Only'),
            ('rejected', 'Rejected'),
            ('billed', 'Bill Generated'),
            ('cod_selected', 'Cash on Delivery Selected'),
            ('paid', 'Payment Completed'),
            ('delivered', 'Delivered'),
            ('cancelled', 'Cancelled'),
            ('out_of_stock', 'Out of Stock'),
        ],
        default='submitted'
    )

    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    payment_date = models.DateTimeField(null=True, blank=True)

    rejection_reason = models.TextField(null=True, blank=True)

    payment_link = models.URLField(max_length=500, null=True, blank=True)
    razorpay_order_id = models.CharField(max_length=100, null=True, blank=True)

    is_stock_deducted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def formatted_id(self):
        return f"PHAR-{self.id:04d}"


class OrderItem(models.Model):
    order = models.ForeignKey(PrescriptionOrder, on_delete=models.CASCADE)
    medicine = models.ForeignKey(Medicine, on_delete=models.SET_NULL, null=True, blank=True)
    medicine_name = models.CharField(max_length=200)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def subtotal(self):
        from decimal import Decimal
        return round(Decimal(str(self.quantity)) * Decimal(str(self.price)), 2)



class PharmacistMessage(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    email = models.EmailField()

    message = models.TextField()

    reply = models.TextField(blank=True, null=True)   # ADD THIS

    is_read_by_user = models.BooleanField(default=True)
    is_read_by_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    




class PurchaseEntry(models.Model):
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    batch_number = models.CharField(max_length=50)
    expiry_date = models.DateField()
    quantity_received = models.IntegerField()
    purchase_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.medicine.name} - {self.batch_number} ({self.quantity_received})"
