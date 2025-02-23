import base64
import hashlib
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from io import BytesIO

import pyotp
import qrcode
from fastapi import Request, HTTPException, Depends

from models import User


async def is_guest(request: Request):
    session_id = request.cookies.get("Authorization")
    if session_id is None:
        return True
    raise HTTPException(status_code=303, headers={"Location": "/"})


async def get_auth_user(request: Request):
    session = request.cookies.get("Session")
    if session is None:
        raise HTTPException(status_code=303, headers={"Location": "/signin"})

    users = await User.all()
    user = next(
        (
            u
            for u in users
            if hashlib.md5(u.email.encode("utf-8")).hexdigest() == session
        ),
        None,
    )
    if not user:
        raise HTTPException(status_code=303, headers={"Location": "/signin"})

    return user


def is_totp_mfa_not_enabled(user: User = Depends(get_auth_user)):
    if user.authenticator_mfa_enabled:
        raise HTTPException(status_code=303, headers={"Location": "/"})
    return True


def is_eotp_mfa_not_enabled(user: User = Depends(get_auth_user)):
    if user.email_mfa_enabled:
        raise HTTPException(status_code=303, headers={"Location": "/"})
    return True


async def generate_qr_code_base64(otp_key: str, email: str) -> str:
    otp_uri = pyotp.totp.TOTP(otp_key).provisioning_uri(
        name=email, issuer_name="Cypress MFA"
    )
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(otp_uri)
    qr.make(fit=True)
    img = qr.make_image(fill="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return img_base64


async def send_email(email: str, subject: str, content: str):
    msg = MIMEMultipart()
    msg["From"] = "your-mailgun-email@example.com"
    msg["To"] = email
    msg["Subject"] = subject

    msg.attach(MIMEText(content, "plain"))

    async with smtplib.SMTP("smtp.mailgun.org", 587) as server:
        await server.starttls()
        await server.login("your-mailgun-username", "your-mailgun-password")
        await server.send_message(msg)
