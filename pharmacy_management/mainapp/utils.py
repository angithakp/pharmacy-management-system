from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils import timezone
import random
import string
from decimal import Decimal
import qrcode
import base64
from io import BytesIO
from .models import OrderItem

def generate_qr_code_base64(data):
    """
    Generates a QR code for the given data and returns it as a base64 string.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"

def send_sms_console(mobile, message):
    print("\n" + "=" * 60)
    print("📨 SMS SENT (CONSOLE MODE)")
    print(f"📱 Mobile : {mobile}")
    print("💬 Message:")
    print(message)
    print("=" * 60 + "\n")

from email.mime.image import MIMEImage

def send_professional_email(subject, template_name, context, recipient_list):

    context.update({
        'subject': subject,
        'pharmacy_name': 'Pradhan Mantri Bharatiya Janaushadhi Kendra',
        'pharmacy_logo_url': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTJuQKniJmO5eQ79LsLtMCdZF11xZhx2C0SFQ&s',
        'contact_email': 'janaushadhikunhipally@gmail.com',
        'contact_phone': '+91 9207253986',
        'location': 'Royal Tower, Near Health Center, Chombala (po), Kunhipally, Kozhikode, 673308',
    })

    try:
        print("STEP 1")
        html_content = render_to_string(
            f'emails/{template_name}.html',
            context
        )

        print("STEP 2")
        text_content = strip_tags(html_content)

        print("STEP 3")
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=str(settings.DEFAULT_FROM_EMAIL),
            to=recipient_list
        )

        print("STEP 4")
        email.attach_alternative(html_content, "text/html")

        payment_qr_base64 = context.get('payment_qr')
        if payment_qr_base64 and "base64," in payment_qr_base64:
            try:
                header, qr_data = payment_qr_base64.split('base64,')
                qr_bytes = base64.b64decode(qr_data)

                image = MIMEImage(qr_bytes)
                image.add_header('Content-ID', '<payment_qr>')
                image.add_header('Content-Disposition', 'inline')
                email.attach(image)

            except Exception as qr_err:
                print("QR ERROR:", qr_err)

        print("EMAIL USER:", settings.EMAIL_HOST_USER)
        print("EMAIL HOST:", settings.EMAIL_HOST)
        print("EMAIL PORT:", settings.EMAIL_PORT)

        print("STEP 5")
        print("SENDING EMAIL TO:", recipient_list)
        print("HOST =", settings.EMAIL_HOST)
        print("PORT =", settings.EMAIL_PORT)
        print("TLS =", settings.EMAIL_USE_TLS)
        print("USER =", settings.EMAIL_HOST_USER)
        email.send(fail_silently=False)
        
        print("EMAIL SENT SUCCESSFULLY")

        print("STEP 6")
        return True

    except Exception as e:
        print("EMAIL ERROR:", e)
        return False


def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))

def send_registration_otp(user, otp):
    name = user.first_name or user.username
    subject = f"Welcome {name}! Your Jan Aushadhi OTP is {otp}"
    context = {
        'user': user,
        'patient_name': name,
        'otp': otp,
        'purpose': 'Registration'
    }
    return send_professional_email(subject, 'otp_verification', context, [user.email])

def send_password_reset_otp(user, otp):
    name = user.first_name or user.username
    subject = f"Jan Aushadhi: Security Code for {name} - {otp}"
    context = {
        'user': user,
        'patient_name': name,
        'otp': otp,
        'purpose': 'Password Reset'
    }
    return send_professional_email(subject, 'otp_verification', context, [user.email])

def send_order_confirmation(order, items):
    subject = f"Order Confirmed - {order.formatted_id} | Janaushadhi Kendra"
    track_url = f"http://127.0.0.1:8000/order-tracking/{order.id}/"
    context = {
        'order': order,
        'order_id': order.id,
        'patient_name': order.patient_name if order.patient_name else "Valued Patient",
        'status': order.get_status_display(),
        'order_date': order.created_at,
        'items': items,
        'pharmacy_name': 'Pradhan Mantri Bharatiya Janaushadhi Kendra',
        'location': 'Royal Tower, Near Health Center, Chombala (po), Kunhipally, Kozhikode, 673308',
        'track_url': track_url,
    }
    # Only send email if a user is associated
    if order.user:
        return send_professional_email(subject, 'order_placed', context, [order.user.email])
    return None

def send_status_update_email(order):
    status_display = order.get_status_display()
    subject = f"Jan Aushadhi: Update for {order.patient_name} - Order {order.formatted_id} [{status_display}]"
    
    # Base URL for the site (matching current local dev)
    SITE_URL = "http://127.0.0.1:8000"
    
    # Calculate billing details for the template if status is billed
    subtotal = 0
    gst = 0
    if order.status in ['billed', 'paid', 'delivered']:
        total_dec = Decimal(str(order.total_amount or 0))
        subtotal = total_dec / Decimal('1.05')
        gst = total_dec - subtotal

    # QR Code for payment if billed
    payment_qr = None
    items = OrderItem.objects.filter(order=order)

    # Automatically generate QR if status is billed and we have a link
    if order.status == 'billed' and order.payment_link:
        payment_qr = generate_qr_code_base64(order.payment_link)

    # Absolute URL for the local payment page (which has a clear QR code)
    local_payment_url = f"{SITE_URL}/pay/{order.id}/"
    track_url = f"{SITE_URL}/order-tracking/{order.id}/"

    delivery_date = timezone.now()
    
    context = {
        'order': order,
        'status': status_display,
        'patient_name': order.patient_name if order.patient_name else "Valued Patient",
        'pharmacy_name': 'Pradhan Mantri Bharatiya Janaushadhi Kendra',
        'rejection_reason': order.rejection_reason,
        'subtotal': round(subtotal, 2),
        'gst': round(gst, 2),
        'payment_qr': payment_qr,
        'items': items,
        'local_payment_url': local_payment_url,
        'track_url': track_url,
        'delivery_date': timezone.now(),
        'order_date': order.created_at,
        'order_id': order.id,
        'reason': order.rejection_reason,
    }
    
    template = 'status_update'
    if order.status == 'rejected':
        template = 'order_rejected'
    elif order.status == 'out_of_stock':
        template = 'out_of_stock'
    elif order.status == 'billed':
        template = 'bill_generated'
    elif order.status == 'pickup_only':
        template = 'pickup_ready'
    elif order.status == 'paid':
        template = 'payment_received'
    elif order.status == 'delivered':
        template = 'order_delivered'

    # Only send email if a user is associated
    if order.user:
        return send_professional_email(subject, template, context, [order.user.email])
    return None

def send_pharmacist_reply_email(msg):
    subject = f"Response from Jan Aushadhi Pharmacist - #{msg.id:04d}"
    context = {
        'name': msg.name,
        'message_text': msg.message,
        'reply_text': msg.reply,
        'created_at': msg.created_at,
    }
    # Send to the email provided in the message
    return send_professional_email(subject, 'pharmacist_reply', context, [msg.email])
