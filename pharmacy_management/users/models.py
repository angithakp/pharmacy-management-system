from django.db import models
from django.contrib.auth.models import User
import random
from django.utils import timezone

class Medicine(models.Model):
    name = models.CharField(max_length=100)
    price = models.FloatField()
    stock = models.IntegerField()
    description = models.TextField()

    def __str__(self):
        return self.name


class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    address = models.TextField()
    status = models.CharField(max_length=30, default="Ordered")

    def __str__(self):
        return f"{self.user.username} - {self.medicine.name}"

class UserOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=[('registration', 'Registration'), ('password_reset', 'Password Reset')])
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)

    def is_expired(self):
        # OTP valid for 10 minutes
        return timezone.now() > self.created_at + timezone.timedelta(minutes=10)

    def __str__(self):
        return f"{self.user.username} - {self.purpose} - {self.otp}"
