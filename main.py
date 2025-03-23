import hashlib
import logging
import random
from urllib.parse import urlencode

import pyotp
from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from tortoise.contrib.fastapi import register_tortoise

from models import User
from templates import templates
from utils import (
    generate_qr_code_base64,
    get_auth_user,
    is_eotp_mfa_not_enabled,
    is_guest,
    is_totp_mfa_not_enabled,
    normalize_email,
    render_mfa_template,
    send_email_mfa_code,
    send_otp_email,
    verify_mfa,
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
async def home_page(request: Request, user: User = Depends(get_auth_user)):
    email_md5 = hashlib.md5(user.email.lower().encode("utf-8")).hexdigest()
    query_params = urlencode({"d": "identicon", "s": "300"})
    gravatar_query = f"{email_md5}?{query_params}"

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
    use_email_mfa: bool = Form(False),
):
    normalized_email = normalize_email(email)
    user = await User.get_or_none(email=normalized_email, password=password)
    if not user:
        return templates.TemplateResponse(
            request=request,
            name="signin.html",
            context={"error": "Invalid email or password", "email": email},
            status_code=422,
        )

    if user.authenticator_mfa_enabled or user.email_mfa_enabled:
        challenge = (
            "Open your Authenticator application to get the Code"
            if user.authenticator_mfa_enabled and not use_email_mfa
            else "Check your email for the Code"
        )

        if not otp_code:
            if user.email_mfa_enabled or use_email_mfa:
                await send_email_mfa_code(user, request)
            return render_mfa_template(
                request=request,
                challenge=challenge,
                use_email_mfa=use_email_mfa,
                user=user,
            )

        valid, error_message = await verify_mfa(user, otp_code, use_email_mfa)
        if not valid:
            return render_mfa_template(
                request=request,
                challenge=challenge,
                use_email_mfa=use_email_mfa,
                user=user,
                error=error_message,
            )

    session_cookie = hashlib.md5(email.encode("utf-8")).hexdigest()
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(key="Session", value=session_cookie)
    return response


@app.get("/signup", response_class=HTMLResponse, dependencies=[Depends(is_guest)])
async def signup_page(request: Request):
    return templates.TemplateResponse(request=request, name="signup.html")


@app.post("/signup", response_class=HTMLResponse, dependencies=[Depends(is_guest)])
async def signup_action(
    name: str = Form(...), email: str = Form(...), password: str = Form(...)
):
    normalized_email = normalize_email(email)
    user = User(name=name, email=normalized_email, password=password)
    await user.save()
    session_cookie = hashlib.md5(email.encode("utf-8")).hexdigest()
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(key="Session", value=session_cookie)
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
    # Re-render the totp activation page with an error if verification fails.
    return templates.TemplateResponse(
        request=request,
        name="totp.html",
        context={
            "error": "Invalid OTP code",
            "data": await generate_qr_code_base64(otp_key, user.email),
            "otp_key": otp_key,
        },
        status_code=422,
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
        request=request,
        name="eotp.html",
        context={"error": "Invalid OTP code"},
        status_code=422,
    )


@app.exception_handler(404)
async def not_found_page(request: Request, exception):
    return templates.TemplateResponse(request=request, name="404.html", status_code=404)
