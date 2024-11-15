# auth_app/utils.py
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .models import OTP
from django.contrib.auth.models import User

def send_otp_email(user: User):
    otp = OTP.generate_otp()
    expires_at = timezone.now() + timedelta(minutes=5) 

    otp_record = OTP.objects.create(
        user=user,
        otp=otp,
        expires_at=expires_at
    )

    send_mail(
        'Your OTP Code',
        f'Your OTP code is {otp}. It will expire in 5 minutes.',
        settings.EMAIL_HOST_USER,
        [user.email],
        fail_silently=False,
    )
    return otp_record
