from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from mainapp.models import Medicine
from .models import UserOTP
from mainapp.utils import generate_otp, send_registration_otp, send_password_reset_otp
from django.http import HttpResponse
from django.core.mail import send_mail
from django.http import HttpResponse
from mainapp.utils import send_brevo_email

def test_brevo(request):
    success = send_brevo_email(
        "Brevo API Test",
        "<h1>Hello from Pharmacy Project</h1>",
        "angithavalsan@gmail.com"
    )

    return HttpResponse(f"Success = {success}")


# ---------------- HOME ----------------
def home(request):
    medicines = Medicine.objects.all()
    return render(request, 'pharmacy/home.html', {'medicines': medicines})


# ---------------- USER SIGNUP ----------------
def user_signup(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        full_name = request.POST.get('full_name')
        email = str(request.POST.get('email', '')).strip()
        password = request.POST.get('password')

        if not username or not password or not email or not full_name:
            messages.error(request, "Please fill all required fields")
            return redirect('user_signup')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect('user_signup')
        
        existing_user = User.objects.filter(email=email).first()
        if existing_user:
            if not existing_user.is_active:
                # User exists but not verified, update name in case it changed
                existing_user.first_name = full_name
                existing_user.save()
                
                # ... send OTP logic ...
                otp_code = generate_otp()
                UserOTP.objects.create(user=existing_user, otp=otp_code, purpose='registration')
                print(f"Resending OTP to unverified user: {email}")
                if send_registration_otp(existing_user, otp_code):
                    messages.info(request, f"Welcome back {existing_user.first_name}! This email is already registered but not verified. A new code has been sent to {email}.")
                    request.session['verification_user_id'] = existing_user.id
                    return redirect('verify_otp')
            
            messages.error(request, "Email already registered")
            return redirect('user_signup')

        # Create inactive user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_active=False
        )
        user.first_name = full_name
        user.save()

        # Generate and Send OTP
        otp_code = generate_otp()
        UserOTP.objects.create(user=user, otp=otp_code, purpose='registration')

        if send_registration_otp(user, otp_code):
            messages.info(request, f"Welcome {user.first_name}! A verification code has been sent to {email}. Please verify to activate your account.")
            request.session['verification_user_id'] = user.id
            return redirect('verify_otp')
        else:
            user.delete()
            messages.error(request, f"Sorry {user.first_name}, there was an error sending the verification email. Please try again.")
            return redirect('user_signup')

    return render(request, 'users/signup.html')

# ---------------- VERIFY OTP ----------------
def verify_otp(request):
    user_id = request.session.get('verification_user_id')
    if not user_id:
        return redirect('user_signup')
    
    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        otp_entered = request.POST.get('otp')
        otp_obj = UserOTP.objects.filter(user=user, otp=otp_entered, purpose='registration', is_verified=False).last()

        if otp_obj and not otp_obj.is_expired():
            otp_obj.is_verified = True
            otp_obj.save()
            user.is_active = True
            user.save()
            messages.success(request, f"Congratulations {user.first_name}! Your email has been verified successfully. You can now login.")
            del request.session['verification_user_id']
            return redirect('user_login')
        else:
            messages.error(request, "Invalid or expired OTP code.")

    return render(request, 'users/verify_otp.html', {'email': user.email})

# ---------------- PASSWORD RESET REQUEST ----------------
def password_reset_request(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        user = User.objects.filter(email=email).first()
        
        if user:
            otp_code = generate_otp()
            UserOTP.objects.create(user=user, otp=otp_code, purpose='password_reset')
            if send_password_reset_otp(user, otp_code):
                request.session['reset_user_id'] = user.id
                messages.info(request, "Password reset OTP sent to your email.")
                return redirect('password_reset_confirm')
        
        messages.error(request, "Email not found in our records.")

    return render(request, 'users/password_reset_request.html')

# ---------------- PASSWORD RESET CONFIRM ----------------
def password_reset_confirm(request):
    user_id = request.session.get('reset_user_id')
    if not user_id:
        return redirect('password_reset_request')
    
    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        otp_entered = request.POST.get('otp')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('password_reset_confirm')

        otp_obj = UserOTP.objects.filter(user=user, otp=otp_entered, purpose='password_reset', is_verified=False).last()

        if otp_obj and not otp_obj.is_expired():
            otp_obj.is_verified = True
            otp_obj.save()
            user.set_password(new_password)
            user.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Password reset successful! You can now login.")
            del request.session['reset_user_id']
            return redirect('user_login')
        else:
            messages.error(request, "Invalid or expired OTP.")

    return render(request, 'users/password_reset_confirm.html', {'email': user.email})


# ---------------- USER LOGIN ----------------
def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        print("LOGIN USERNAME:", username)
        print("LOGIN PASSWORD:", password)

        user = authenticate(request, username=username, password=password)
        print("AUTH RESULT:", user)

        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect('home')
        
        # Check if user exists but is inactive
        checking_user = User.objects.filter(username=username).first()
        if checking_user and not checking_user.is_active:
            if checking_user.check_password(password):
                messages.warning(request, "Your account is not verified. Please check your email for the verification code.")
                request.session['verification_user_id'] = checking_user.id
                return redirect('verify_otp')

        messages.error(request, "Invalid credentials. Please try again.")
        return redirect('user_login')

    return render(request, 'users/login.html')


# ---------------- ADMIN LOGIN ----------------
def admin_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None and user.is_staff:
            login(request, user)
            messages.success(request, "Administrator session initialized.")
            return redirect('admin_dashboard')

        messages.error(request, "Access denied. Invalid administrator credentials.")
        return redirect('admin_login')

    return render(request, 'users/admin_login.html')





# ---------------- LOGOUT ----------------
def logout_view(request):
    logout(request)
    return redirect('user_login')


def test_email(request):
    try:
        result = send_mail(
            "SMTP Test",
            "Hello from Render",
            "angithavalsan@gmail.com",
            ["angithavalsan@gmail.com"],
            fail_silently=False,
        )
        return HttpResponse(f"SUCCESS: {result}")
    except Exception as e:
        return HttpResponse(f"ERROR: {str(e)}")
