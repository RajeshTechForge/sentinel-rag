"""
This module defines the authentication routes for FastAPI.

- Includes endpoints for user login, OIDC callback handling and logout.
- Audit logging is integrated

"""

import secrets
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Request, HTTPException, Response
from fastapi.responses import RedirectResponse
from authlib.jose import jwt

from sentinel_rag.api.dependencies import (
    DatabaseDep,
    RequestContextDep,
    AuditServiceDep,
    SettingsDep,
)
from sentinel_rag.services.auth import (
    TenantConfig,
    register_tenant_client,
    create_access_token,
)
from sentinel_rag.services.audit import (
    AuditLogEntry,
    AuthAuditEntry,
    EventCategory,
    EventOutcome,
    Action,
)


router = APIRouter()


def _build_tenant_config(settings: SettingsDep) -> TenantConfig:
    """Build TenantConfig from AppSettings."""
    return TenantConfig(
        tenant_id=settings.tenant.tenant_id,
        domain=settings.tenant.domain,
        oidc_config={
            "client_id": settings.oidc.client_id,
            "client_secret": settings.oidc.client_secret,
            "server_metadata_url": settings.oidc.server_metadata_url,
        },
    )


@router.get("/login")
async def login(request: Request, settings: SettingsDep):
    """
    The login endpoint initiates the OIDC authentication flow by redirecting the user
    to the identity provider's authorization URL.
    """
    # Build tenant config from settings
    tenant_config = _build_tenant_config(settings)
    missing_config = []

    if not tenant_config.tenant_id:
        missing_config.append("TENANT_ID")
    if not tenant_config.oidc_config.client_id:
        missing_config.append("OIDC_CLIENT_ID")
    if not tenant_config.oidc_config.client_secret:
        missing_config.append("OIDC_CLIENT_SECRET")
    if not tenant_config.oidc_config.server_metadata_url:
        missing_config.append("OIDC_SERVER_METADATA_URL")

    if missing_config:
        raise HTTPException(
            status_code=503,
            detail=f"OIDC not configured. Missing environment variables: {', '.join(missing_config)}",
        )

    try:
        client = register_tenant_client(tenant_config)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to initialize OIDC client: {str(e)}",
        )

    callback_uri = str(request.url_for("auth_callback"))

    # Create secure state parameter with optional frontend redirect
    state_data = {
        "tenant_id": tenant_config.tenant_id,
        "nonce": secrets.token_urlsafe(32),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    frontend_redirect = request.query_params.get("redirect_uri")

    if frontend_redirect:
        state_data["frontend_redirect"] = frontend_redirect

    state_token = jwt.encode(
        {"alg": settings.security.algorithm}, state_data, settings.security.secret_key
    ).decode("utf-8")

    try:
        return await client.authorize_redirect(
            request,
            callback_uri,
            state=state_token,
        )
    except Exception as e:
        error_msg = str(e)
        if (
            "Name or service not known" in error_msg
            or "ConnectError" in type(e).__name__
        ):
            raise HTTPException(
                status_code=503,
                detail="Cannot reach OIDC provider. Please verify OIDC_SERVER_METADATA_URL is correct and the server is accessible.",
            )
        raise HTTPException(
            status_code=500,
            detail=f"OIDC authorization failed: {error_msg}",
        )


@router.get("/callback", name="auth_callback")
async def auth_callback(
    request: Request,
    context: RequestContextDep,
    audit: AuditServiceDep,
    db: DatabaseDep,
    settings: SettingsDep,
):
    """
    The authentication callback endpoint processes the response from the identity provider.
    It validates the state parameter, exchanges the authorization code for tokens,
    creates an access token, sets a secure cookie, and logs the authentication event.
    """
    try:
        state_token = request.query_params.get("state")

        if not state_token:
            raise HTTPException(status_code=400, detail="Missing state parameter")

        # Decode and validate state token
        state_data = jwt.decode(state_token, settings.security.secret_key)

        if not state_data:
            raise HTTPException(status_code=400, detail="Invalid state parameter")

        state_data.validate()
        state_time = datetime.fromisoformat(state_data["timestamp"])

        if (datetime.now(timezone.utc) - state_time).seconds > 600:  # 10 min
            raise HTTPException(status_code=400, detail="State expired")

        # Proceed with token exchange
        tenant_id = state_data["tenant_id"]
        tenant_config = _build_tenant_config(settings)

        # Exchange code for tokens
        client = register_tenant_client(tenant_config)
        token = await client.authorize_access_token(request)

        if not token:
            raise HTTPException(status_code=400, detail="Failed to obtain access token")

        user_info = token.get("userinfo")
        if not user_info:
            user_info = await client.userinfo(token=token)

        email = user_info.get("email")
        user = db.get_user_by_email(email)

        if not user:
            raise HTTPException(
                status_code=403,
                detail="Access denied. User account not found. Please contact your administrator to create an account.",
            )

        user_id = str(user["user_id"])
        role_dept_list = db.get_user_role_and_department(user_id)

        if not role_dept_list:
            raise HTTPException(
                status_code=403,
                detail="User has no assigned role. Please contact administrator.",
            )

        department, role = role_dept_list[0]

        access_token_expires = timedelta(
            minutes=settings.security.access_token_expire_minutes
        )
        access_token = create_access_token(
            data={
                "sub": email,
                "user_id": user_id,
                "tenant_id": tenant_id,
                "role": role,
                "department": department,
            },
            settings=settings,
            expires_delta=access_token_expires,
        )

        # Log successful login
        main_entry = AuditLogEntry(
            user_id=user_id,
            user_email=email,
            ip_address=context.client_ip,
            user_agent=context.user_agent,
            session_id=context.session_id,
            event_category=EventCategory.AUTHENTICATION,
            event_type="login_success",
            action=Action.LOGIN,
            outcome=EventOutcome.SUCCESS,
        )
        log_id = await audit.log(main_entry)

        auth_entry = AuthAuditEntry(
            user_id=user_id,
            email=email,
            auth_method="email_only",
            event_type="login_success",
            ip_address=context.client_ip,
            user_agent=context.user_agent,
        )
        await audit.log_auth(log_id, auth_entry)

        frontend_redirect = state_data.get("frontend_redirect")

        if frontend_redirect:
            separator = "&" if "?" in frontend_redirect else "?"
            response = RedirectResponse(
                url=f"{frontend_redirect}{separator}access_token={access_token}"
            )
        else:
            response = RedirectResponse(url="/")
            response.set_cookie(
                key="access_token",
                value=access_token,
                httponly=True,
                secure=True,
                samesite="lax",
                max_age=settings.security.access_token_expire_minutes * 60,
            )

        return response

    except (HTTPException, Exception) as e:
        if HTTPException:
            error_msg = f"Authentication failed: {e}"
        else:
            error_msg = "Authentication failed: Internal error"

        # Log failed login
        main_entry = AuditLogEntry(
            user_email=email,
            ip_address=context.client_ip,
            user_agent=context.user_agent,
            event_category=EventCategory.AUTHENTICATION,
            event_type="login_failure",
            action=Action.LOGIN,
            outcome=EventOutcome.FAILURE,
            error_message=f"Authentication failed: {str(error_msg)}",
        )
        log_id = await audit.log(main_entry)

        auth_entry = AuthAuditEntry(
            email=email,
            auth_method="email_only",
            event_type="login_failure",
            ip_address=context.client_ip,
            user_agent=context.user_agent,
            failed_attempts_count=1,
        )
        await audit.log_auth(log_id, auth_entry)

        if HTTPException:
            raise
        else:
            raise HTTPException(status_code=500, detail="Authentication failed")


@router.post("/logout")
async def logout(
    response: Response, context: RequestContextDep, audit: AuditServiceDep
):
    try:
        response.delete_cookie("access_token")

        # Log logout event
        main_entry = AuditLogEntry(
            user_email=None,
            ip_address=context.client_ip,
            user_agent=context.user_agent,
            event_category=EventCategory.AUTHENTICATION,
            event_type="logout",
            action=Action.LOGOUT,
            outcome=EventOutcome.SUCCESS,
        )
        log_id = await audit.log(main_entry)
        auth_entry = AuthAuditEntry(
            email=None,
            auth_method="email_only",
            event_type="logout",
            ip_address=context.client_ip,
            user_agent=context.user_agent,
        )
        await audit.log_auth(log_id, auth_entry)
        return {"message": "Logged out successfully"}

    except Exception as e:
        main_entry = AuditLogEntry(
            user_email=None,
            ip_address=context.client_ip,
            user_agent=context.user_agent,
            event_category=EventCategory.AUTHENTICATION,
            event_type="logout_failure",
            action=Action.LOGOUT,
            outcome=EventOutcome.FAILURE,
            error_message=f"Logout failed: {str(e)}",
        )
        log_id = await audit.log(main_entry)

        auth_entry = AuthAuditEntry(
            email=None,
            auth_method="email_only",
            event_type="logout_failure",
            ip_address=context.client_ip,
            user_agent=context.user_agent,
            failed_attempts_count=1,
        )
        await audit.log_auth(log_id, auth_entry)

        raise HTTPException(status_code=500, detail="Logout failed")
