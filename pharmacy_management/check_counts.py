import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmacy_management.settings')
django.setup()

from django.contrib.auth.models import User
from mainapp.models import PrescriptionOrder, OrderItem, PharmacistMessage
from users.models import Order, UserOTP

def check_counts():
    print("Current Data Counts:")
    print(f"Total Users: {User.objects.count()}")
    print(f"Regular Users (Customers): {User.objects.filter(is_staff=False, is_superuser=False).count()}")
    print(f"Staff Users: {User.objects.filter(is_staff=True).count()}")
    print(f"Superusers: {User.objects.filter(is_superuser=True).count()}")
    print(f"Prescription Orders: {PrescriptionOrder.objects.count()}")
    print(f"Order Items: {OrderItem.objects.count()}")
    print(f"Pharmacist Messages: {PharmacistMessage.objects.count()}")
    print(f"Users App Orders: {Order.objects.count()}")
    print(f"User OTPs: {UserOTP.objects.count()}")

if __name__ == "__main__":
    check_counts()
