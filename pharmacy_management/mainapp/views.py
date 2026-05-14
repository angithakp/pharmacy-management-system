
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Medicine
from .models import PrescriptionOrder, OrderItem, PurchaseEntry
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import user_passes_test
from decimal import Decimal
from twilio.rest import Client
from django.conf import settings
from .utils import send_sms_console
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from datetime import timedelta
from django.db.models import F
from django.db.models import Count
from django.db.models import Q
from .utils import (
    send_professional_email, generate_otp, send_order_confirmation, 
    send_status_update_email, send_registration_otp, send_pharmacist_reply_email
)
from django.http import HttpResponse
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Frame, KeepInFrame, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import A4
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER
from io import BytesIO
import razorpay
from django.db.models import Sum
from django.db.models.functions import TruncMonth, Coalesce
from .models import PharmacistMessage










def home(request):
    categories = [
        'Tablets', 'Syrups', 'Injections', 'Medical Devices', 
        'Personal Care', 'Other'
    ]
    return render(request, 'pharmacy/home.html', {'categories': categories})




@login_required
def dashboard(request):

    total_medicines = Medicine.objects.count()
    total_users = User.objects.filter(is_staff=False).count()
    total_orders = PrescriptionOrder.objects.count()

    pending_orders = PrescriptionOrder.objects.filter(
        status__in=["submitted", "verified"]
    ).count()

    # ✅ LOW STOCK LOGIC
    low_stock_count = Medicine.objects.filter(
        stock__lte=F('minimum_stock')
    ).count()

    # ✅ NEAR EXPIRY LOGIC
    near_expiry_count = Medicine.objects.filter(
        expiry_date__lte=timezone.now().date() + timedelta(days=30)
    ).count()

    context = {
        "total_medicines": total_medicines,
        "total_users": total_users,
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "low_stock_count": low_stock_count,
        "near_expiry_count": near_expiry_count,
    }

    return render(request, "admin/dashboard.html", context)





def medicines(request):
    query = request.GET.get('q')
    category = request.GET.get('category')
    medicines = Medicine.objects.all()

    if query:
        medicines = medicines.filter(
            Q(name__icontains=query) |
            Q(category__icontains=query)
        )
    
    if category and category != 'All':
        medicines = medicines.filter(category=category)

    return render(request, 'pharmacy/medicines.html', {
        'medicines': medicines,
        'categories': ['Tablets', 'Syrups', 'Injections', 'Medical Devices', 'Personal Care', 'Other']
    })





def about(request):
    return render(request, 'pharmacy/about.html')

def contact(request):
    return render(request, 'pharmacy/contact.html')

@staff_member_required
def admin_medicines(request):
    if request.method == "POST":
        name = request.POST.get("name")
        category = request.POST.get("category")
        price = request.POST.get("price")
        batch_number = request.POST.get("batch_number")
        expiry_date = request.POST.get("expiry_date")
        stock = request.POST.get("stock")
        prescription_required = request.POST.get("prescription_required") == "True"

        if name and category and price:
            Medicine.objects.create(
                name=name,
                category=category,
                price=price,
                batch_number=batch_number,
                expiry_date=expiry_date,
                stock=stock,
                prescription_required=prescription_required
            )
            messages.success(request, f"Medicine '{name}' added successfully!")
        else:
            messages.error(request, "Please fill in all required fields.")
        
        return redirect("admin_medicines")

    query = request.GET.get('q')
    medicines = Medicine.objects.all().order_by('-id')

    if query:
        medicines = medicines.filter(
            Q(name__icontains=query) |
            Q(category__icontains=query) |
            Q(batch_number__icontains=query)
        )

    total_medicines = Medicine.objects.count()
    prescription_required_count = Medicine.objects.filter(prescription_required=True).count()
    available_stock_count = Medicine.objects.filter(stock__gt=0).count()

    context = {
        "medicines": medicines,
        "total_medicines": total_medicines,
        "prescription_required_count": prescription_required_count,
        "available_stock_count": available_stock_count,
    }

    return render(request, "admin/medicines.html", context)

@staff_member_required
def delete_medicine(request, medicine_id):
    medicine = get_object_or_404(Medicine, id=medicine_id)
    medicine.delete()
    return redirect("admin_medicines")  


@staff_member_required
def edit_medicine(request, id):
    medicine = get_object_or_404(Medicine, id=id)

    if request.method == "POST":
        medicine.name = request.POST.get("name")
        medicine.category = request.POST.get("category")
        medicine.price = request.POST.get("price")
        medicine.batch_number = request.POST.get("batch_number")
        medicine.expiry_date = request.POST.get("expiry_date")
        medicine.stock = request.POST.get("stock")
        medicine.prescription_required = request.POST.get("prescription_required") == "True"

        medicine.save()
        return redirect("admin_medicines")

    return render(request, "admin/edit_medicine.html", {
        "medicine": medicine
    })  



@staff_member_required
def admin_inventory(request):
    today = timezone.now().date()
    today_plus_30 = today + timedelta(days=30)
    
    if request.method == "POST" and "add_purchase" in request.POST:
        medicine_id = request.POST.get("medicine_id")
        batch_number = request.POST.get("batch_number")
        expiry_date = request.POST.get("expiry_date")
        quantity = int(request.POST.get("quantity", 0))

        medicine = get_object_or_404(Medicine, id=medicine_id)
        
        if medicine.batch_number != batch_number:
            new_batch = Medicine.objects.create(
                name=medicine.name,
                category=medicine.category,
                price=medicine.price,
                batch_number=batch_number,
                expiry_date=expiry_date,
                stock=quantity,
                minimum_stock=medicine.minimum_stock,
                prescription_required=medicine.prescription_required,
                store_pickup_only=medicine.store_pickup_only
            )
            PurchaseEntry.objects.create(
                medicine=new_batch,
                batch_number=batch_number,
                expiry_date=expiry_date,
                quantity_received=quantity
            )
            messages.success(request, f"New batch {batch_number} added for {medicine.name}.")
        else:
            medicine.stock += quantity
            medicine.save()
            PurchaseEntry.objects.create(
                medicine=medicine,
                batch_number=batch_number,
                expiry_date=expiry_date,
                quantity_received=quantity
            )
            messages.success(request, f"Stock updated for {medicine.name} (Batch: {batch_number}).")
        
        return redirect("admin_inventory")

    # Base queryset
    all_medicines = Medicine.objects.all().order_by('name', 'expiry_date')
    
    # Filter logic
    query = request.GET.get('q')
    status_filter = request.GET.get('status')
    
    medicines = all_medicines
    if query:
        medicines = medicines.filter(
            Q(name__icontains=query) |
            Q(batch_number__icontains=query) |
            Q(category__icontains=query)
        )
    
    if status_filter == 'low_stock':
        medicines = medicines.filter(stock__lte=F('minimum_stock'))
    elif status_filter == 'expiring':
        medicines = medicines.filter(expiry_date__lte=today_plus_30, expiry_date__gte=today)

    total_medicines = all_medicines.count()
    low_stock_count = all_medicines.filter(stock__lte=F('minimum_stock')).count()
    near_expiry_count = all_medicines.filter(expiry_date__lte=today_plus_30, expiry_date__gte=today).count()

    context = {
        "medicines": medicines,
        "total_medicines": total_medicines,
        "low_stock_count": low_stock_count,
        "near_expiry_count": near_expiry_count,
        "expiry_limit": today_plus_30,
        "current_query": query,
        "current_status": status_filter,
    }

    return render(request, "admin/inventory.html", context)


def deduct_stock_for_order(order):
    """
    Automatically reduce stock quantity based on the ordered medicines.
    Follows FIFO logic (First In First Out) based on expiry date for batches.
    """
    if order.is_stock_deducted:
        return

    items = OrderItem.objects.filter(order=order)
    for item in items:
        qty_to_deduct = item.quantity
        
        # If we have a specific medicine link (batch), use it
        if item.medicine:
            if item.medicine.stock >= qty_to_deduct:
                item.medicine.stock -= qty_to_deduct
                item.medicine.save()
                qty_to_deduct = 0
            else:
                qty_to_deduct -= item.medicine.stock
                item.medicine.stock = 0
                item.medicine.save()

        # If still need to deduct (or no link), search by name using FIFO (expiry date)
        if qty_to_deduct > 0:
            batches = Medicine.objects.filter(name=item.medicine_name, stock__gt=0).order_by('expiry_date')
            for batch in batches:
                if batch.stock >= qty_to_deduct:
                    batch.stock -= qty_to_deduct
                    batch.save()
                    qty_to_deduct = 0
                    break
                else:
                    qty_to_deduct -= batch.stock
                    batch.stock = 0
                    batch.save()
        
    order.is_stock_deducted = True
    order.save()


@staff_member_required
def admin_update_inventory(request, pk):
    if request.method == "POST":
        medicine = get_object_or_404(Medicine, pk=pk)
        
        batch_number = request.POST.get("batch_number")
        expiry_date = request.POST.get("expiry_date")
        stock_change = int(request.POST.get("stock", 0))
        
        if batch_number:
            medicine.batch_number = batch_number
        if expiry_date:
            medicine.expiry_date = expiry_date
        
        # Log as purchase if stock is increased
        if stock_change > medicine.stock:
            PurchaseEntry.objects.create(
                medicine=medicine,
                batch_number=medicine.batch_number,
                expiry_date=medicine.expiry_date,
                quantity_received=stock_change - medicine.stock
            )
            
        medicine.stock = stock_change
        medicine.save()
        messages.success(request, f"Inventory for {medicine.name} updated successfully!")
        
    return redirect("admin_inventory")











# 1️⃣ Upload Prescription / Direct Order
@login_required
def upload_prescription(request):
    medicine_id = request.GET.get('medicine_id')
    medicine = None
    if medicine_id:
        medicine = get_object_or_404(Medicine, id=medicine_id)

    if request.method == 'POST':
        patient_name = request.POST.get('patient_name', '')
        doctor_name = request.POST.get('doctor_name', '')
        mobile = request.POST.get('mobile', '')
        address = request.POST.get('address', '')
        pincode = request.POST.get('pincode', '')
        prescription_file = request.FILES.get('prescription_file')
        # Capture quantity with robust fallback
        raw_quantity = request.POST.get('quantity', '1')
        quantity = int(raw_quantity) if raw_quantity and str(raw_quantity).isdigit() else 1

        # Logic: If item is selected and it doesn't require prescription, we allow null presc
        # If it's a general upload or medicine requires it, we should ideally check (but let's keep it flexible)
        
        order = PrescriptionOrder.objects.create(
            user=request.user,
            patient_name=patient_name,
            doctor_name=doctor_name if doctor_name else "Self",
            mobile=mobile,
            prescription_file=prescription_file,
            address=address,
            pincode=pincode,
        )

        # If a specific medicine was ordered, add it to the order items immediately
        if medicine:
            OrderItem.objects.create(
                order=order,
                medicine=medicine,
                medicine_name=medicine.name,
                quantity=quantity,
                price=medicine.price
            )
            # Automatically verify and bill if no prescription is required
            if not medicine.prescription_required:
                order.status = 'billed'
                # Final safeguard for total amount calculation
                unit_price = Decimal(str(medicine.price))
                order.total_amount = round(unit_price * quantity, 2)
                order.save()
        
        # Send Confirmation Email
        items = OrderItem.objects.filter(order=order)
        send_order_confirmation(order, items)

        if medicine and not medicine.prescription_required:
            return redirect('payment', order_id=order.id)

        return redirect('prescription_confirmation', order_id=order.id)

    return render(request, 'pharmacy/upload_prescription.html', {
        'medicine': medicine
    })


# 2️⃣ Payment Page
@login_required
def payment(request, order_id):
    order = get_object_or_404(PrescriptionOrder, id=order_id, user=request.user)
    
    order_items = OrderItem.objects.filter(order=order)
    
    # Recalculate total for display safety
    total = round(sum(Decimal(str(item.price)) * item.quantity for item in order_items), 2)
    if not order.total_amount or order.total_amount != total:
        order.total_amount = total
        order.save()

    return render(request, 'pharmacy/payment.html', {
        'order': order,
        'order_items': order_items
    })


# 3️⃣ My Orders Page
@login_required
def my_orders(request):
    orders = PrescriptionOrder.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'pharmacy/my_orders.html', {'orders': orders})

@staff_member_required
def admin_orders(request):
    orders = PrescriptionOrder.objects.all().order_by("-created_at")
    return render(request, "admin/admin_orders.html", {"orders": orders})




@staff_member_required
def admin_bill_success(request, order_id):
    order = get_object_or_404(PrescriptionOrder, id=order_id)
    return render(request, "admin/admin_bill_success.html", {
        "order": order
    })



@staff_member_required
def update_order_status(request, order_id):
    order = get_object_or_404(PrescriptionOrder, id=order_id)

    if request.method == "POST":
        new_status = request.POST.get("status")

        if not new_status:
            messages.error(request, "Please select a status.")
            return redirect("update_order_status", order_id=order.id)

        order.status = new_status

        if new_status == "rejected":
            rejection_reason = request.POST.get("rejection_reason", "").strip()
            if rejection_reason:
                order.rejection_reason = rejection_reason
            else:
                # Set a generic reason if skipped by admin but status is rejected
                order.rejection_reason = "The prescription uploaded was either unclear, expired, or invalid."
        else:
            # Clear reason if no longer rejected
            order.rejection_reason = None

        if new_status in ["paid", "delivered"]:
            if not order.payment_date:
                order.payment_date = timezone.now()
            # Deduct stock when order is paid/delivered
            deduct_stock_for_order(order)

        order.save()

        # Send Status Update Email
        send_status_update_email(order)

        return redirect("admin_orders")

    return render(request, "admin/admin_order_update.html", {"order": order})






@staff_member_required
def admin_generate_bill(request, order_id):
    order = get_object_or_404(PrescriptionOrder, id=order_id)
    order_items = OrderItem.objects.filter(order=order)

    if not order_items.exists():
        messages.error(request, "Please add medicines before generating bill.")
        return redirect("admin_order_detail", order_id=order.id)

    from decimal import Decimal
    subtotal = round(sum(Decimal(str(item.subtotal)) for item in order_items), 2)
    total = subtotal

    if request.method == "POST":
        # Razorpay Integration
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        amount_paise = int(total * 100)
        
        try:
            # Determine customer email
            customer_email = order.user.email if order.user else "janaushadhikunhipally@gmail.com"
            
            payment_link_response = client.payment_link.create({
                "amount": amount_paise,
                "currency": "INR",
                "accept_partial": False,
                "description": f"Bill for Order {order.formatted_id} - {order.patient_name}",
                "customer": {
                    "name": order.patient_name,
                    "email": customer_email,
                    "contact": order.mobile[:10] if order.mobile else "0000000000"
                },
                "notify": {"sms": False, "email": False},
                "reminder_enable": True,
                "notes": {"order_id": str(order.id)},
                "callback_url": f"http://127.0.0.1:8000/order/{order.id}/",
                "callback_method": "get"
            })
            
            order.payment_link = payment_link_response.get('short_url')
            # Removed: order.razorpay_order_id = payment_link_response.get('id')
        except Exception as e:
            print(f"Razorpay Error: {e}")
            
        order.total_amount = total
        order.status = "billed"
        order.save()

        send_status_update_email(order)
        return redirect("admin_bill_success", order_id=order.id)

    return render(request, "admin/admin_generate_bill.html", {
        "order": order,
        "order_items": order_items,
        "total": total
    })












@staff_member_required
def billing_preview(request, order_id):
    order = get_object_or_404(PrescriptionOrder, id=order_id)
    order_items = OrderItem.objects.filter(order=order)

    from decimal import Decimal
    # Re-calculate to ensure accuracy
    subtotal = round(sum(Decimal(str(item.subtotal)) for item in order_items), 2)
    total = subtotal

    return render(request, "admin/billing.html", {
        "order": order,
        "order_items": order_items,
        "total": total
    })


@staff_member_required
def admin_users(request):
    from django.utils import timezone
    from datetime import timedelta

    # ✅ Show only normal signup users
    base_query = User.objects.filter(is_superuser=False, is_staff=False)
    users = base_query.order_by("-date_joined")

    total_users = base_query.count()
    active_users = base_query.filter(is_active=True).count()
    
    thirty_days_ago = timezone.now() - timedelta(days=30)
    new_users = base_query.filter(date_joined__gte=thirty_days_ago).count()

    return render(request, "admin/admin_users.html", {
        "users": users,
        "total_users": total_users,
        "active_users": active_users,
        "new_users": new_users
    })


@staff_member_required
def admin_delete_message(request, message_id):
    msg = get_object_or_404(PharmacistMessage, id=message_id)
    msg.delete()
    messages.success(request, f"Message from {msg.name} has been deleted.")
    return redirect('admin_messages')


@staff_member_required
def admin_delete_order(request, order_id):
    order = get_object_or_404(PrescriptionOrder, id=order_id)
    order.delete()
    messages.success(request, f"Order PHAR-{order_id:04d} has been deleted.")
    return redirect('admin_orders')

@staff_member_required
def admin_toggle_user(request, user_id):
    user = get_object_or_404(User, id=user_id)

    if user != request.user:   # prevent self-disable
        user.is_active = not user.is_active
        user.save()

    return redirect('admin_users')

@staff_member_required
def admin_delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)

    if user != request.user:   # prevent deleting self
        user.delete()

    return redirect('admin_users')


@staff_member_required
def admin_order_detail(request, order_id):
    order = get_object_or_404(PrescriptionOrder, id=order_id)
    order_items = OrderItem.objects.filter(order=order)

    return render(request, "admin/admin_order_detail.html", {
        "order": order,
        "order_items": order_items
    })


@login_required
def order_detail_user(request, order_id):
    order = get_object_or_404(
        PrescriptionOrder,
        id=order_id,
        user=request.user
    )

    order_items = OrderItem.objects.filter(order=order)

    return render(request, "pharmacy/order_detail_user.html", {
        "order": order,
        "order_items": order_items
    })

@login_required
def order_tracking(request, order_id):
    order = get_object_or_404(PrescriptionOrder, id=order_id, user=request.user)

    status_progress = {
        "submitted": 20,
        "verified": 40,
        "billed": 60,
        "cod_selected": 80,
        "paid": 80,
        "delivered": 100,
    }

    progress = status_progress.get(order.status, 0)

    return render(request, "pharmacy/order_tracking.html", {
        "order": order,
        "progress": progress,
    })

    

def bill_view(request, order_id):
    """
    Standard bill view for users to see their order details and invoice.
    Can be accessed by both users (their own) and staff.
    """
    if request.user.is_staff:
        order = get_object_or_404(PrescriptionOrder, id=order_id)
    else:
        order = get_object_or_404(PrescriptionOrder, id=order_id, user=request.user)

    order_items = OrderItem.objects.filter(order=order)

    subtotal = sum(item.subtotal for item in order_items)
    total = subtotal

    from .utils import generate_qr_code_base64
    payment_qr = None
    if order.status == "billed" and order.payment_link:
        payment_qr = generate_qr_code_base64(order.payment_link)

    context = {
        'order': order,
        'order_items': order_items,
        'total': total,
        'payment_qr': payment_qr,
    }

    return render(request, 'pharmacy/order_bill.html', context)




def download_invoice(request, order_id):
    order = get_object_or_404(PrescriptionOrder, id=order_id)
    order_items = OrderItem.objects.filter(order=order)

    buffer = BytesIO()
    # A4 Page setup
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
    elements = []

    styles = getSampleStyleSheet()
    
    # Custom Styles
    style_header = ParagraphStyle('Header', fontSize=22, fontName='Helvetica-Bold', alignment=TA_CENTER, leading=26)
    style_motto = ParagraphStyle('Motto', fontSize=12, fontName='Helvetica-Bold', alignment=TA_CENTER, leading=16)
    style_address = ParagraphStyle('Address', fontSize=10, fontName='Helvetica', alignment=TA_CENTER, leading=14)
    style_normal = ParagraphStyle('Normal', fontSize=11, fontName='Helvetica', leading=15)
    style_right = ParagraphStyle('Right', fontSize=11, fontName='Helvetica', leading=15, alignment=TA_RIGHT)
    style_bold = ParagraphStyle('Bold', fontSize=11, fontName='Helvetica-Bold', leading=15, alignment=TA_CENTER)
    style_footer = ParagraphStyle('Footer', fontSize=8, fontName='Helvetica', alignment=TA_CENTER, leading=10, textColor=colors.grey)

    # --- 1. PHARMACY HEADER (Centered) ---
    elements.append(Paragraph("PRADHAN MANTRI BHARATIYA JANAUSHADHI KENDRA", style_header))
    elements.append(Paragraph("QUALITY GENERIC MEDICINES AT AFFORDABLE PRICES", style_motto))
    elements.append(Paragraph("Royal Tower, Chombala (po), Kunhipally, Kozhikode, 673308", style_address))
    elements.append(Paragraph("Contact: +91 9207253986 | Email: janaushadhikunhipally@gmail.com", style_address))
    elements.append(Spacer(1, 15))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.black, spaceBefore=5, spaceAfter=20))

    # --- 2. BILL META INFO (Grid) ---
    meta_data = [
        [Paragraph(f"<b>Patient :</b> {order.patient_name.upper()}", style_normal), Paragraph(f"<b>Bill No :</b> {order.formatted_id}", style_right)],
        [Paragraph(f"<b>Mobile :</b> +91 {order.mobile}", style_normal), Paragraph(f"<b>Date :</b> {order.created_at.strftime('%d/%m/%Y')}", style_right)]
    ]
    meta_table = Table(meta_data, colWidths=[3.5*inch, 3.5*inch])
    meta_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 15))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey, spaceBefore=5, spaceAfter=25))

    # --- 3. MEDICINE TABLE ---
    table_data = [["SL.", "MEDICINE NAME", "QTY", "MRP", "AMOUNT"]]
    
    subtotal = 0
    for i, item in enumerate(order_items, 1):
        med_name_para = Paragraph(item.medicine_name, style_normal)
        table_data.append([
            str(i),
            med_name_para,
            str(item.quantity),
            f"{item.price:.2f}",
            f"{item.subtotal:.2f}"
        ])
        subtotal += item.subtotal

    total = subtotal

    med_table = Table(table_data, colWidths=[0.5*inch, 3.2*inch, 0.6*inch, 1.0*inch, 1.2*inch])
    med_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 12),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 1.5, colors.black),
        ('ALIGN', (0,0), (0,-1), 'CENTER'),
        ('ALIGN', (2,0), (2,-1), 'CENTER'),
        ('ALIGN', (3,0), (-1,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
        ('TOPPADDING', (0,0), (-1,-1), 12),
        ('BOTTOMPADDING', (0,0), (-1,-1), 12),
    ]))
    elements.append(med_table)

    # --- 4. TOTALS ---
    totals_data = [
        ["GRAND TOTAL", f"Rs. {total:.2f}"]
    ]
    totals_table = Table(totals_data, colWidths=[5.3*inch, 1.2*inch])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (0,-1), 'RIGHT'),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 15),
        ('TOPPADDING', (0,0), (-1,-1), 15),
        ('BOTTOMPADDING', (0,0), (-1,-1), 15),
        ('RIGHTPADDING', (0,-1), (-1,-1), 12),
    ]))
    elements.append(totals_table)
    elements.append(Spacer(1, 40))

    # --- 5. FOOTER ---
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey, spaceBefore=5, spaceAfter=10))
    elements.append(Paragraph("<b>TERMS & CONDITIONS:</b> Medicines once sold will not be exchanged. Always consult your doctor before use.", style_footer))
    elements.append(Spacer(1, 15))
    elements.append(Paragraph("*** THANK YOU FOR CHOOSING JAN AUSHADHI ***", style_bold))
    elements.append(Paragraph("Quality Medicines at Genuine Rate", style_footer))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("<em>This is a system generated document. No physical signature required.</em>", style_footer))

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="JanAushadhi_Bill_{order.formatted_id}.pdf"'
    response.write(pdf)
    return response





def cancel_order(request, order_id):
    order = get_object_or_404(PrescriptionOrder, id=order_id)

    # Allow cancel only before billing
    if order.status in ['submitted', 'verified']:
        order.status = 'cancelled'
        order.save()
        
        # Send Notification
        send_status_update_email(order)
        
        messages.success(request, "Order cancelled successfully.")
    else:
        messages.error(request, "This order cannot be cancelled.")

    return redirect('my_orders')


@staff_member_required
def add_order_item(request, order_id):
    order = get_object_or_404(PrescriptionOrder, id=order_id)

    if request.method == "POST":
        medicine_id = request.POST.get("medicine_id")
        quantity = request.POST.get("quantity")

        if medicine_id and quantity:
            medicine = get_object_or_404(Medicine, id=medicine_id)

            OrderItem.objects.create(
                order=order,
                medicine=medicine,
                medicine_name=medicine.name,
                quantity=int(quantity),
                price=medicine.price
            )

        return redirect("add_order_item", order_id=order.id)

    medicines = Medicine.objects.all()
    order_items = OrderItem.objects.filter(order=order)

    return render(request, "admin/add_order_item.html", {
        "order": order,
        "medicines": medicines,
        "order_items": order_items
    })


@login_required
def pay_online(request, order_id):
    order = get_object_or_404(PrescriptionOrder, id=order_id, user=request.user)

    order.status = "paid"
    order.payment_date = timezone.now()
    if not order.razorpay_order_id:
        import uuid
        order.razorpay_order_id = f"UPI-{uuid.uuid4().hex[:10].upper()}"
    order.save()

    messages.success(request, "Payment successful!")

    return redirect("order_detail_user", order_id=order.id)


@login_required
def select_cod(request, order_id):
    order = get_object_or_404(PrescriptionOrder, id=order_id, user=request.user)

    order.status = "cod_selected"
    order.payment_link = None
    order.razorpay_order_id = None
    order.save()

    # Send Notification
    send_status_update_email(order)

    messages.success(request, "Cash on Delivery selected.")

    return redirect("order_detail_user", order_id=order.id)




@login_required
def pay_with_razorpay(request, order_id):
    order = get_object_or_404(PrescriptionOrder, id=order_id, user=request.user)

    if order.status != "billed":
        return redirect("order_detail_user", order_id=order.id)

    from .utils import generate_qr_code_base64
    import urllib.parse
    
    # Precise UPI Configuration for App intents
    upi_vpa = "9539043253@upi"  # The requested pharmacy UPI ID
    payee_name = urllib.parse.quote("Jan Aushadhi Pharmacy")
    
    # Recalculate from items just in case
    order_items = OrderItem.objects.filter(order=order)
    calculated_total = sum(Decimal(str(item.price)) * item.quantity for item in order_items)
    amount_str = f"{calculated_total:.2f}"
    order_id_note = urllib.parse.quote(f"Bill for Order {order.formatted_id}")
    
    # Base connection string
    base_payload = f"?pa={upi_vpa}&pn={payee_name}&am={amount_str}&cu=INR&tn={order_id_note}"

    # Construct Universal & Specific App Intents
    upi_intent_generic = f"upi://pay{base_payload}"
    gpay_intent = f"tez://upi/pay{base_payload}"
    phonepe_intent = f"phonepe://pay{base_payload}"
    paytm_intent = f"paytmmp://pay{base_payload}"
    
    upi_qr = generate_qr_code_base64(upi_intent_generic)

    context = {
        "order": order,
        "upi_qr": upi_qr,
        "upi_id": upi_vpa,
        "amount": amount_str,
        "gpay_intent": gpay_intent,
        "phonepe_intent": phonepe_intent,
        "paytm_intent": paytm_intent,
        "generic_intent": upi_intent_generic,
    }

    return render(request, "pharmacy/razorpay_payment.html", context)




@login_required
def prescription_confirmation(request, order_id):
    order = get_object_or_404(PrescriptionOrder, id=order_id, user=request.user)
    return render(request, "pharmacy/prescription_confirmation.html", {"order": order})

@login_required
def payment_success(request, order_id):
    order = get_object_or_404(PrescriptionOrder, id=order_id, user=request.user)

    # Automatic detection logic: Mark as paid when user lands here
    if order.status == 'billed':
        order.status = 'paid'
        if not order.payment_date:
            order.payment_date = timezone.now()
        
        # Ensure a transaction ID exists for the receipt display
        if not order.razorpay_order_id:
            import uuid
            order.razorpay_order_id = f"TRX{uuid.uuid4().hex[:10].upper()}"
        
        order.save()

    return render(request, "pharmacy/payment_successful.html", {"order": order})

@login_required
def payment_successful_view(request, order_id):
    order = get_object_or_404(PrescriptionOrder, id=order_id, user=request.user)
    return render(request, "pharmacy/payment_successful.html", {"order": order})

from django.http import JsonResponse

@login_required
def check_payment_status(request, order_id):
    order = get_object_or_404(PrescriptionOrder, id=order_id, user=request.user)
    # Detection for real-time success page showing
    return JsonResponse({
        'status': order.status,
        'is_paid': order.status in ['paid', 'delivered'],
        'has_date': order.payment_date is not None
    })




@staff_member_required
def admin_reports(request):

    today = timezone.now().date()

    # =========================
    # 💰 TOTAL & TODAY REVENUE
    # =========================
    
    # Precise query sets for settlement categories
    # 1. Walk-in: Any anonymous order (User is None) that is explicitly Paid or Delivered
    walkin_settled_qs = PrescriptionOrder.objects.filter(
        user__isnull=True,
        status__in=["delivered", "paid"]
    ).annotate(effective_date=Coalesce('payment_date', 'created_at'))
    
    # 2. Digital: Registered user, explicitly paid online (status='paid') 
    # or delivered with a verified transaction ID (TRX, UPI, or FIX)
    digital_settled_qs = PrescriptionOrder.objects.filter(
        user__isnull=False
    ).filter(
        Q(status="paid") | 
        Q(status="delivered", razorpay_order_id__startswith="TRX") |
        Q(status="delivered", razorpay_order_id__startswith="UPI") |
        Q(status="delivered", razorpay_order_id__startswith="FIX")
    ).annotate(effective_date=Coalesce('payment_date', 'created_at'))
    
    # 3. COD: Registered user, delivered successfully, but doesn't have a digital transaction ID
    cod_settled_qs = PrescriptionOrder.objects.filter(
        user__isnull=False,
        status="delivered"
    ).exclude(
        id__in=digital_settled_qs.values_list('id', flat=True)
    ).annotate(effective_date=Coalesce('payment_date', 'created_at'))

    # Annotate with effective_date for unified timeline reporting
    orders_qs = PrescriptionOrder.objects.annotate(
        effective_date=Coalesce('payment_date', 'created_at')
    )
    
    # =========================
    # 📅 DATE RANGE FILTERING
    # =========================
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    is_filtered = False

    if start_date and end_date:
        is_filtered = True
        orders_qs = orders_qs.filter(effective_date__date__range=[start_date, end_date])
        walkin_settled_qs = walkin_settled_qs.filter(effective_date__date__range=[start_date, end_date])
        digital_settled_qs = digital_settled_qs.filter(effective_date__date__range=[start_date, end_date])
        cod_settled_qs = cod_settled_qs.filter(effective_date__date__range=[start_date, end_date])

    # Synchronize top-level statistics with strictly settled orders
    settled_ids = (
        list(walkin_settled_qs.values_list('id', flat=True)) +
        list(digital_settled_qs.values_list('id', flat=True)) +
        list(cod_settled_qs.values_list('id', flat=True))
    )
    
    settled_qs = orders_qs.filter(id__in=settled_ids)
    
    total_revenue = settled_qs.aggregate(Sum("total_amount"))["total_amount__sum"] or 0

    if is_filtered:
        # If filtered, "today_revenue" becomes "period_revenue"
        today_revenue = total_revenue
    else:
        today_revenue = settled_qs.filter(
            effective_date__date=today
        ).aggregate(Sum("total_amount"))["total_amount__sum"] or 0

    total_paid_orders = settled_qs.count()

    # =========================
    # 📅 MONTHLY REVENUE
    # =========================
    monthly_data = (
        settled_qs
        .annotate(month=TruncMonth("effective_date"))
        .values("month")
        .annotate(
            total_revenue=Sum("total_amount"),
            total_orders=Count("id")
        )
        .order_by("month")
    )

    # =========================
    # 🔥 TOP SELLING MEDICINES (ONLY SETTLED)
    # =========================
    top_medicines = (
        OrderItem.objects.filter(order__in=settled_qs)
        .values("medicine_name")
        .annotate(total_sold=Sum("quantity"))
        .order_by("-total_sold")[:5]
    )

    # =========================
    # 💳 PAYMENT METHOD SUMMARY
    # =========================
    razorpay_count = digital_settled_qs.count()
    razorpay_revenue = digital_settled_qs.aggregate(Sum("total_amount"))["total_amount__sum"] or 0
    
    cod_settled_count = cod_settled_qs.count()
    cod_revenue = cod_settled_qs.aggregate(Sum("total_amount"))["total_amount__sum"] or 0
    
    walkin_count = walkin_settled_qs.count()
    walkin_revenue = walkin_settled_qs.aggregate(Sum("total_amount"))["total_amount__sum"] or 0
    
    cod_pending_count = PrescriptionOrder.objects.filter(status="cod_selected").count()

    total_settled = razorpay_count + cod_settled_count + walkin_count
    razorpay_perc = round((float(razorpay_revenue) / float(total_revenue) * 100), 1) if total_revenue > 0 else 0
    cod_perc = round((float(cod_revenue) / float(total_revenue) * 100), 1) if total_revenue > 0 else 0
    walkin_perc = round((float(walkin_revenue) / float(total_revenue) * 100), 1) if total_revenue > 0 else 0

    # =========================
    # 📦 STOCK DATA
    # =========================
    total_medicines = Medicine.objects.count()

    low_stock = Medicine.objects.filter(stock__lte=10)
    low_stock_count = low_stock.count()

    # =========================
    # ⏰ EXPIRY DATA
    # =========================
    next_30_days = today + timedelta(days=30)

    near_expiry = Medicine.objects.filter(
        expiry_date__lte=next_30_days,
        expiry_date__gte=today
    )

    expired = Medicine.objects.filter(
        expiry_date__lt=today
    )

    context = {
        "total_revenue": total_revenue,
        "today_revenue": today_revenue,
        "total_paid_orders": total_paid_orders,
        "total_medicines": total_medicines,
        "monthly_data": monthly_data,
        "top_medicines": top_medicines,
        "razorpay_count": razorpay_count,
        "razorpay_revenue": razorpay_revenue,
        "cod_settled_count": cod_settled_count,
        "cod_revenue": cod_revenue,
        "cod_pending_count": cod_pending_count,
        "razorpay_perc": razorpay_perc,
        "cod_perc": cod_perc,
        "walkin_count": walkin_count,
        "walkin_revenue": walkin_revenue,
        "walkin_perc": walkin_perc,
        "low_stock": low_stock,
        "low_stock_count": low_stock_count,
        "near_expiry": near_expiry,
        "expired": expired,
        "start_date": start_date,
        "end_date": end_date,
        "is_filtered": is_filtered,
    }

    return render(request, "admin/reports.html", context)




def send_pharmacist_message(request):
    if request.method == "POST":

        name = request.POST.get("name")
        email = request.POST.get("email")
        message = request.POST.get("message")

        PharmacistMessage.objects.create(
            user=request.user,
            name=name,
            email=email,
            message=message
        )

    return redirect("home")




@staff_member_required
def admin_messages(request):

    pharmacist_messages = PharmacistMessage.objects.all().order_by("-created_at")

    return render(request, "admin/messages.html", {
        "pharmacist_messages": pharmacist_messages
    })



@staff_member_required
def admin_reply_message(request, message_id):

    msg = get_object_or_404(PharmacistMessage, id=message_id)
    
    # Mark as read when admin opens the thread
    if not msg.is_read_by_admin:
        msg.is_read_by_admin = True
        msg.save()

    if request.method == "POST":
        reply = request.POST.get("reply")

        msg.reply = reply
        msg.is_read_by_user = False
        msg.save()

        # Send Email Notification
        send_pharmacist_reply_email(msg)

        return redirect("admin_messages")

    return render(request, "admin/reply_message.html", {"msg": msg})




@login_required
def user_messages(request):

    user_messages_list = PharmacistMessage.objects.filter(user=request.user).order_by('-created_at')
    unread_msgs = user_messages_list.filter(is_read_by_user=False)
    if unread_msgs.exists():
        unread_msgs.update(is_read_by_user=True)

    return render(request,
                  "pharmacy/my_messages.html",
                  {"user_messages_list": user_messages_list})




@login_required
def user_profile(request):
    user = request.user
    
    if request.method == 'POST':
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.save()
        messages.success(request, 'Your profile has been updated successfully!')
        return redirect('user_profile')

    total_orders = PrescriptionOrder.objects.filter(user=user).count()

    total_spent = PrescriptionOrder.objects.filter(
        user=user,
        status__in=["paid", "delivered"]
    ).aggregate(Sum("total_amount"))["total_amount__sum"] or 0

    total_messages = PharmacistMessage.objects.filter(
        user=user
    ).count()
    
    recent_orders = PrescriptionOrder.objects.filter(user=user).order_by('-created_at')[:5]

    context = {
        "total_orders": total_orders,
        "total_spent": total_spent,
        "total_messages": total_messages,
        "recent_orders": recent_orders,
    }

    return render(request, "pharmacy/profile.html", context)
























@staff_member_required
def walkin_order(request):
    if request.method == "POST":
        patient_name = request.POST.get("patient_name")
        mobile = request.POST.get("mobile")
        doctor_name = request.POST.get("doctor_name", "Walk-in")
        address = request.POST.get("address", "Walk-in Customer")
        
        # Create the order
        order = PrescriptionOrder.objects.create(
            user=None,  # No linked user account
            patient_name=patient_name,
            mobile=mobile,
            doctor_name=doctor_name,
            address=address,
            pincode="000000",
            status='billed'  # Direct orders are immediately billed
        )
        
        # Get medicine data from the form
        medicine_ids = request.POST.getlist("medicine_id[]")
        quantities = request.POST.getlist("quantity[]")
        
        total_amount = Decimal('0.00')
        
        for med_id, qty in zip(medicine_ids, quantities):
            if med_id and qty:
                medicine = get_object_or_404(Medicine, id=med_id)
                qty = int(qty)
                
                item_price = Decimal(str(medicine.price))
                subtotal = item_price * qty
                total_amount += subtotal
                
                OrderItem.objects.create(
                    order=order,
                    medicine=medicine,
                    medicine_name=medicine.name,
                    quantity=qty,
                    price=float(item_price)
                )
        
        # Set total amount without GST
        order.total_amount = total_amount
        # Automatically deduct stock for walk-in order
        deduct_stock_for_order(order)
        order.save()
        
        messages.success(request, f"Walk-in order {order.formatted_id} for {patient_name} created successfully!")
        return redirect('admin_bill_success', order_id=order.id)

    medicines = Medicine.objects.filter(stock__gt=0).order_by('name')
    return render(request, "admin/walkin_order.html", {"medicines": medicines})


@staff_member_required
def export_report_pdf(request):
    """
    Generates a professional PDF report for Financial Intelligence.
    Reusable logic from admin_reports view.
    """
    today = timezone.now().date()
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    is_filtered = False

    # 1. Base query sets for settlement categories
    walkin_settled_qs = PrescriptionOrder.objects.filter(
        user__isnull=True,
        status__in=["delivered", "paid"]
    ).annotate(effective_date=Coalesce('payment_date', 'created_at'))
    
    digital_settled_qs = PrescriptionOrder.objects.filter(
        user__isnull=False
    ).filter(
        Q(status="paid") | 
        Q(status="delivered", razorpay_order_id__startswith="TRX") |
        Q(status="delivered", razorpay_order_id__startswith="UPI") |
        Q(status="delivered", razorpay_order_id__startswith="FIX")
    ).annotate(effective_date=Coalesce('payment_date', 'created_at'))
    
    cod_settled_qs = PrescriptionOrder.objects.filter(
        user__isnull=False,
        status="delivered"
    ).exclude(
        id__in=digital_settled_qs.values_list('id', flat=True)
    ).annotate(effective_date=Coalesce('payment_date', 'created_at'))

    orders_qs = PrescriptionOrder.objects.annotate(
        effective_date=Coalesce('payment_date', 'created_at')
    )
    
    # 2. Apply Date Filtering
    if start_date and end_date:
        is_filtered = True
        orders_qs = orders_qs.filter(effective_date__date__range=[start_date, end_date])
        walkin_settled_qs = walkin_settled_qs.filter(effective_date__date__range=[start_date, end_date])
        digital_settled_qs = digital_settled_qs.filter(effective_date__date__range=[start_date, end_date])
        cod_settled_qs = cod_settled_qs.filter(effective_date__date__range=[start_date, end_date])

    # 3. Synchronize statistics
    settled_ids = (
        list(walkin_settled_qs.values_list('id', flat=True)) +
        list(digital_settled_qs.values_list('id', flat=True)) +
        list(cod_settled_qs.values_list('id', flat=True))
    )
    settled_qs = orders_qs.filter(id__in=settled_ids)
    
    total_revenue = settled_qs.aggregate(Sum("total_amount"))["total_amount__sum"] or 0
    total_paid_orders = settled_qs.count()
    total_medicines = Medicine.objects.count()

    if is_filtered:
        today_revenue = total_revenue
        net_label = "PERIOD REVENUE"
    else:
        today_revenue = settled_qs.filter(
            effective_date__date=today
        ).aggregate(Sum("total_amount"))["total_amount__sum"] or 0
        net_label = "NET (TODAY)"

    # Monthly Lifecycle
    monthly_data = (
        settled_qs
        .annotate(month=TruncMonth("effective_date"))
        .values("month")
        .annotate(
            total_revenue=Sum("total_amount"),
            total_orders=Count("id")
        )
        .order_by("-month")
    )

    # Detailed Revenue Splitting
    razorpay_revenue = digital_settled_qs.aggregate(Sum("total_amount"))["total_amount__sum"] or 0
    cod_revenue = cod_settled_qs.aggregate(Sum("total_amount"))["total_amount__sum"] or 0
    walkin_revenue = walkin_settled_qs.aggregate(Sum("total_amount"))["total_amount__sum"] or 0

    # 4. Generate PDF using ReportLab
    buffer = BytesIO()
    # A4 Page proportions with generous margins
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4, 
        rightMargin=40, 
        leftMargin=40, 
        topMargin=40, 
        bottomMargin=40
    )
    elements = []
    styles = getSampleStyleSheet()

    # Custom Professional Styling
    style_header = ParagraphStyle('Header', fontSize=18, fontName='Helvetica-Bold', alignment=TA_CENTER, leading=22, spaceAfter=2)
    style_sub_header = ParagraphStyle('SubHeader', fontSize=10, fontName='Helvetica', alignment=TA_CENTER, leading=14, spaceAfter=10)
    style_title = ParagraphStyle('Title', fontSize=14, fontName='Helvetica-Bold', alignment=TA_LEFT, leading=18, spaceAfter=10, textColor=colors.HexColor("#333333"))
    style_normal = ParagraphStyle('Normal', fontSize=10, fontName='Helvetica', leading=14)
    style_bold = ParagraphStyle('Bold', fontSize=11, fontName='Helvetica-Bold', leading=14)
    style_stat_label = ParagraphStyle('StatLabel', fontSize=9, fontName='Helvetica', textColor=colors.grey, leading=12)
    style_stat_val = ParagraphStyle('StatVal', fontSize=12, fontName='Helvetica-Bold', leading=16, textColor=colors.HexColor("#0d6efd"))

    # --- A. PHARMACY BRANDING ---
    elements.append(Paragraph("PRADHAN MANTRI BHARATIYA JANAUSHADHI KENDRA", style_header))
    elements.append(Paragraph("KUNJIPALLY, KOZHIKODE, KERALA - 673308", style_sub_header))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0d6efd"), spaceBefore=5, spaceAfter=15))

    # --- B. REPORT METADATA ---
    report_title = "ADMINISTRATIVE FINANCIAL INTELLIGENCE REPORT"
    elements.append(Paragraph(report_title, style_title))
    
    time_ctx = f"PERIOD: {start_date} to {end_date}" if is_filtered else f"CUMULATIVE LIFETIME REPORT (As of {today.strftime('%d %b %Y')})"
    elements.append(Paragraph(time_ctx, style_normal))
    elements.append(Spacer(1, 20))

    # --- C. KEY PERFORMANCE INDICATORS (Grid) ---
    kpi_data = [
        [
            Paragraph("GROSS REVENUE", style_stat_label), 
            Paragraph(net_label, style_stat_label), 
            Paragraph("SETTLED ORDERS", style_stat_label), 
            Paragraph("ACTIVE SKUs", style_stat_label)
        ],
        [
            Paragraph(f"INR {total_revenue:,.2f}", style_stat_val), 
            Paragraph(f"INR {today_revenue:,.2f}", style_stat_val), 
            Paragraph(f"{total_paid_orders}", style_stat_val), 
            Paragraph(f"{total_medicines}", style_stat_val)
        ]
    ]
    kpi_table = Table(kpi_data, colWidths=[1.65*inch, 1.65*inch, 1.65*inch, 1.65*inch])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 12),
        ('BOTTOMPADDING', (0,0), (-1,-1), 12),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 30))

    # --- D. SETTLEMENT SPLIT (DETAILED) ---
    elements.append(Paragraph("CHANNEL-WISE SETTLEMENT SUMMARY", style_bold))
    elements.append(Spacer(1, 8))
    settlement_data = [
        ["Payment Channel", "Volume", "Settled Amount (INR)"],
        ["Digital (Online Payments)", f"{digital_settled_qs.count()}", f"{razorpay_revenue:,.2f}"],
        ["Offline (Cash on Delivery)", f"{cod_settled_qs.count()}", f"{cod_revenue:,.2f}"],
        ["Direct (Pharmacy Walk-in)", f"{walkin_settled_qs.count()}", f"{walkin_revenue:,.2f}"],
        [Paragraph("<b>TOTALS</b>", style_bold), Paragraph(f"<b>{total_paid_orders}</b>", style_bold), Paragraph(f"<b>INR {total_revenue:,.2f}</b>", style_bold)]
    ]
    settlement_table = Table(settlement_data, colWidths=[2.8*inch, 1.2*inch, 2.6*inch])
    settlement_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f1f3f5")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
        ('ALIGN', (0,0), (0,-1), 'LEFT'),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('LINEBELOW', (0, -2), (-1, -2), 1, colors.black), # Line above totals
    ]))
    elements.append(settlement_table)
    elements.append(Spacer(1, 30))

    # --- E. REVENUE LIFECYCLE (Timeline) ---
    elements.append(Paragraph("MONTHLY REVENUE CYCLES", style_bold))
    elements.append(Spacer(1, 8))
    lifecycle_data = [["Billing Month", "Transactions", "Revenue Value (INR)"]]
    for data in monthly_data:
        lifecycle_data.append([
            data['month'].strftime("%B %Y"),
            str(data['total_orders']),
            f"{data['total_revenue']:,.2f}"
        ])
    
    if not monthly_data:
        lifecycle_data.append(["No historical cycles found", "-", "-"])

    lifecycle_table = Table(lifecycle_data, colWidths=[2.8*inch, 1.2*inch, 2.6*inch])
    lifecycle_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f1f3f5")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
        ('ALIGN', (0,0), (0,-1), 'LEFT'),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(lifecycle_table)

    # --- F. FOOTER & SIGN-OFF ---
    elements.append(Spacer(1, 50))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("Report generated automatically by PMBJK Kunjipally IMS Management Suite.", ParagraphStyle('F', fontSize=8, alignment=TA_CENTER, textColor=colors.grey)))
    elements.append(Paragraph(f"Timestamp: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}", ParagraphStyle('F', fontSize=7, alignment=TA_CENTER, textColor=colors.silver)))

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type='application/pdf')
    filename = f"Financial_Intelligence_{today}.pdf"
    if is_filtered:
        filename = f"Financial_Report_{start_date}_to_{end_date}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write(pdf)
    return response


@staff_member_required
def export_inventory_pdf(request):
    """
    Generates a high-quality pharmaceutical inventory report.
    """
    today = timezone.now().date()
    expiry_limit = today + timedelta(days=30)
    
    # Apply same filtering logic as admin_inventory
    query = request.GET.get('q')
    status_filter = request.GET.get('status')
    
    medicines = Medicine.objects.all().order_by('name', 'expiry_date')
    
    if query:
        medicines = medicines.filter(
            Q(name__icontains=query) |
            Q(batch_number__icontains=query) |
            Q(category__icontains=query)
        )
    
    if status_filter == 'low_stock':
        medicines = medicines.filter(stock__lte=F('minimum_stock'))
    elif status_filter == 'expiring':
        medicines = medicines.filter(expiry_date__lte=expiry_limit, expiry_date__gte=today)

    # PAGE SETUP
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    elements = []
    styles = getSampleStyleSheet()

    # Custom Styling
    style_header = ParagraphStyle('Header', fontSize=20, fontName='Helvetica-Bold', alignment=TA_CENTER, leading=24, spaceAfter=2)
    style_sub_header = ParagraphStyle('SubHeader', fontSize=10, fontName='Helvetica', alignment=TA_CENTER, leading=14, spaceAfter=15)
    style_title = ParagraphStyle('Title', fontSize=14, fontName='Helvetica-Bold', alignment=TA_LEFT, leading=18, spaceAfter=12, textColor=colors.HexColor("#111111"))
    style_normal = ParagraphStyle('Normal', fontSize=9, fontName='Helvetica', leading=12)
    style_bold_table = ParagraphStyle('BoldTable', fontSize=9, fontName='Helvetica-Bold', leading=12)

    # --- 1. BRANDING ---
    elements.append(Paragraph("PRADHAN MANTRI BHARATIYA JANAUSHADHI KENDRA", style_header))
    elements.append(Paragraph("KUNJIPALLY, KOZHIKODE, KERALA | QUALITY GENERIC MEDICINES", style_sub_header))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.black, spaceBefore=0, spaceAfter=10))

    # --- 2. METADATA ---
    elements.append(Paragraph("PHARMACEUTICAL INVENTORY LEDGER REPORT", style_title))
    elements.append(Paragraph(f"Generated on: {today.strftime('%d %b %Y')} | Records: {medicines.count()}", style_normal))
    if status_filter:
        elements.append(Paragraph(f"Filter: {status_filter.replace('_', ' ').upper()}", style_normal))
    elements.append(Spacer(1, 20))

    # --- 3. TABLE ---
    table_data = [["MEDICINE NAME", "CATEGORY", "BATCH", "EXPIRY", "STOCK", "PRICE", "STATUS"]]
    for med in medicines:
        # Determine status text
        status_text = "OPTIMAL"
        if med.stock <= med.minimum_stock:
            status_text = "LOW STOCK"
        if med.expiry_date and med.expiry_date <= expiry_limit:
            status_text = "EXPIRING"

        table_data.append([
            Paragraph(f"<b>{med.name}</b>", style_normal),
            med.category,
            med.batch_number if med.batch_number else "-",
            med.expiry_date.strftime("%d/%m/%Y") if med.expiry_date else "-",
            str(med.stock),
            f"{med.price:.2f}",
            status_text
        ])

    inventory_table = Table(table_data, colWidths=[2.2*inch, 0.8*inch, 1.0*inch, 1.0*inch, 0.5*inch, 0.7*inch, 1.0*inch])
    inventory_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (3,-1), 'LEFT'),  # Left align name, cat, batch, expiry
        ('ALIGN', (4,0), (6,-1), 'CENTER'), # Center stock, price, status
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(inventory_table)

    # --- 4. SIGN-OFF ---
    elements.append(Spacer(1, 40))
    elements.append(Paragraph("End of Inventory Report", ParagraphStyle('End', alignment=TA_CENTER, fontSize=8, textColor=colors.grey)))
    
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Inventory_Report_{today}.pdf"'
    response.write(pdf)
    return response
