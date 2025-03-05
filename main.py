import hashlib
import logging
import random
from urllib.parse import urlencode

import pyotp
from fastapi import FastAPI, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from tortoise.contrib.fastapi import register_tortoise

from models import User
from templates import templates
from utils import (
    generate_qr_code_base64,
    get_auth_user,
    is_guest,
    is_totp_mfa_not_enabled,
    is_eotp_mfa_not_enabled,
    send_otp_email,
)

logging.getLogger("uvicorn").propagate = False

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

register_tortoise(
    app,
    db_url="sqlite://db.sqlite3",
    modules={"models": ["models"]},
    generate_schemas=True,
    add_exception_handlers=True,
)


@app.get("/")
def home_page(request: Request, user: User = Depends(get_auth_user)):
    email_encoded = user.email.lower().encode("utf-8")
    email_hash = hashlib.sha256(email_encoded).hexdigest()
    query_params = urlencode({"d": "identicon", "s": str(300)})
    gravatar_query = f"{email_hash}?{query_params}"

    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={"user": user, "gravatar_query": gravatar_query},
    )


@app.get("/signin", response_class=HTMLResponse, dependencies=[Depends(is_guest)])
async def signin_page(request: Request):
    return templates.TemplateResponse(request=request, name="signin.html")


@app.post("/signin", response_class=HTMLResponse, dependencies=[Depends(is_guest)])
async def signin_action(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    otp_code: str = Form(None),
    email_mfa: bool = Form(False),
):
    user = await User.get_or_none(email=email, password=password)
    if not user:
        return templates.TemplateResponse(
            request=request,
            name="signin.html",
            context={"error": "Invalid email or password", "email": email},
            status_code=422,
        )

    if user.authenticator_mfa_enabled or user.email_mfa_enabled:
        if user.authenticator_mfa_enabled and not email_mfa:
            challenge = "Open Authenticator&nbsp;application to&nbsp;get the Code"
        else:
            challenge = "Check your email for&nbsp;the&nbsp;Code"

        if not otp_code:
            if user.email_mfa_enabled or email_mfa:
                user.code = str(random.randint(100000, 999999))
                await send_otp_email(user.email, user.code, request)
                await user.save()

            return templates.TemplateResponse(
                request=request,
                name="mfa.html",
                context={
                    "challenge": challenge,
                    "email": email,
                    "password": password,
                    "email_mfa": email_mfa,
                    "has_email_mfa": user.email_mfa_enabled,
                    "has_authenticator_mfa": user.authenticator_mfa_enabled,
                },
                status_code=302,
            )

        if user.authenticator_mfa_enabled and not email_mfa:
            totp = pyotp.TOTP(user.key)
            if not totp.verify(otp_code):
                return templates.TemplateResponse(
                    request=request,
                    name="mfa.html",
                    context={
                        "challenge": challenge,
                        "email": email,
                        "password": password,
                        "error": "Invalid OTP code",
                        "email_mfa": email_mfa,
                        "has_email_mfa": user.email_mfa_enabled,
                        "has_authenticator_mfa": user.authenticator_mfa_enabled,
                    },
                    status_code=422,
                )
        elif user.email_mfa_enabled:
            if otp_code != user.code:
                return templates.TemplateResponse(
                    request=request,
                    name="mfa.html",
                    context={
                        "challenge": challenge,
                        "email": email,
                        "password": password,
                        "error": "Invalid OTP code",
                        "email_mfa": email_mfa,
                    },
                    status_code=422,
                )

    email_md5 = hashlib.md5(email.encode("utf-8")).hexdigest()
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(key="Session", value=email_md5)
    return response


@app.get("/signup", response_class=HTMLResponse, dependencies=[Depends(is_guest)])
async def signup_page(request: Request):
    return templates.TemplateResponse(request=request, name="signup.html")


@app.post("/signup", response_class=HTMLResponse, dependencies=[Depends(is_guest)])
async def signup_action(
    name: str = Form(...), email: str = Form(...), password: str = Form(...)
):
    user = User(name=name, email=email, password=password)
    await user.save()

    email_md5 = hashlib.md5(email.encode("utf-8")).hexdigest()
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(key="Session", value=email_md5)
    return response


@app.post(
    "/signout", response_class=HTMLResponse, dependencies=[Depends(get_auth_user)]
)
async def signout_action():
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie(key="Session")
    return response


@app.get("/mfa/totp/activate", dependencies=[Depends(is_totp_mfa_not_enabled)])
async def totp_activate_page(request: Request, user: User = Depends(get_auth_user)):
    otp_key = pyotp.random_base32()
    qr_code_base64 = await generate_qr_code_base64(otp_key, user.email)
    return templates.TemplateResponse(
        request=request,
        name="totp.html",
        context={"data": qr_code_base64, "otp_key": otp_key},
    )


@app.post("/mfa/totp/activate", dependencies=[Depends(is_totp_mfa_not_enabled)])
async def totp_activate_action(
    request: Request,
    otp_key: str = Form(...),
    otp_code: str = Form(...),
    user: User = Depends(get_auth_user),
):
    totp = pyotp.TOTP(otp_key)
    if totp.verify(otp_code):
        user.key = otp_key
        user.authenticator_mfa_enabled = True
        await user.save()
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="totp.html",
        context={
            "error": "Invalid OTP code",
            "data": await generate_qr_code_base64(otp_key, user.email),
            "otp_key": otp_key,
        },
    )


@app.get("/mfa/eotp/activate", dependencies=[Depends(is_eotp_mfa_not_enabled)])
async def eotp_activate_page(request: Request, user: User = Depends(get_auth_user)):
    user.code = str(random.randint(100000, 999999))
    await send_otp_email(user.email, user.code, request)
    await user.save()
    return templates.TemplateResponse(request=request, name="eotp.html")


@app.post("/mfa/eotp/activate", dependencies=[Depends(is_eotp_mfa_not_enabled)])
async def eotp_activate_action(
    request: Request, otp_code: str = Form(...), user: User = Depends(get_auth_user)
):
    if otp_code == user.code:
        user.email_mfa_enabled = True
        await user.save()
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(
        request=request, name="eotp.html", context={"error": "Invalid OTP code"}
    )


@app.exception_handler(404)
async def not_found_page(request: Request, exception):
    return templates.TemplateResponse(request=request, name="404.html", status_code=404)
