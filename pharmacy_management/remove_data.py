import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmacy_management.settings')
django.setup()

from django.contrib.auth.models import User
from mainapp.models import PrescriptionOrder, OrderItem, PharmacistMessage
from users.models import Order, UserOTP

def remove_data():
    print("Starting data removal process...")

    # 1. Remove Prescription Data and User Order Data
    order_count = PrescriptionOrder.objects.count()
    PrescriptionOrder.objects.all().delete()
    print(f"Removed {order_count} Prescription Orders (and associated Order Items).")

    # 2. Remove Message Data
    message_count = PharmacistMessage.objects.count()
    PharmacistMessage.objects.all().delete()
    print(f"Removed {message_count} Pharmacist Messages.")

    # 3. Remove Registered User Data (Non-staff/Non-superuser)
    # We filter to keep staff and superusers to ensure the system remains manageable.
    users_to_delete = User.objects.filter(is_staff=False, is_superuser=False)
    user_count = users_to_delete.count()
    users_to_delete.delete()
    print(f"Removed {user_count} Registered Users.")

    # 4. Remove any other related data
    otp_count = UserOTP.objects.count()
    UserOTP.objects.all().delete()
    print(f"Removed {otp_count} User OTPs.")

    users_app_order_count = Order.objects.count()
    Order.objects.all().delete()
    print(f"Removed {users_app_order_count} Users App Orders.")

    print("\nData removal complete.")

if __name__ == "__main__":
    remove_data()
