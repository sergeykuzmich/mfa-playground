import base64
import datetime
import hashlib
import logging
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from io import BytesIO

import aiosmtplib
import pyotp
import qrcode
from fastapi import Request, HTTPException, Depends

from models import User
from templates import templates


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
    smtp_server = os.getenv("SMTP_SERVER", "smtp.mailgun.org")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_username = os.getenv("SMTP_USERNAME", None)
    smtp_password = os.getenv("SMTP_PASSWORD", None)
    send_from = os.getenv("SMTP_SEND_FROM", smtp_username)

    if not all([send_from, smtp_server, smtp_port, smtp_username, smtp_password]):
        logging.warning("SMTP credentials are not fully provided.")
        return

    msg = MIMEMultipart()
    msg["From"] = send_from
    msg["To"] = email
    msg["Subject"] = subject

    msg.attach(MIMEText(content, "html"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=smtp_server,
            port=smtp_port,
            use_tls=True,
            username=smtp_username,
            password=smtp_password,
        )
    except Exception as e:
        logging.warning(f"Failed to send email: {e}")


async def send_otp_email(email: str, code: str, request: Request):
    context = {
        "url": f"{request.url.scheme}://{request.url.hostname}{'' if request.url.port in [80, 443, None] else f':{request.url.port}'}",
        "code": code,
        "current_year": str(datetime.datetime.now().year),
    }
    content = templates.TemplateResponse(
        request=request, name="email-otp.html", context=context
    ).body.decode("utf-8")
    await send_email(email, "Your One Time Password", content)
