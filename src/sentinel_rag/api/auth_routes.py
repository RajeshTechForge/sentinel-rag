import os
import secrets
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Request, HTTPException, Response
from fastapi.responses import RedirectResponse
from authlib.jose import jwt

from sentinel_rag.api.dependencies import (
    DatabaseDep,
    RequestContextDep,
    AuditServiceDep,
)
from sentinel_rag import (
    TenantConfig,
    register_tenant_client,
    create_access_token,
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from sentinel_rag import (
    AuditLogEntry,
    AuthAuditEntry,
    EventCategory,
    EventOutcome,
    Action,
)


given_tenant_config: TenantConfig = {
    "tenant_id": os.getenv("TENANT_ID"),
    "domain": os.getenv("TENANT_DOMAIN"),
    "oidc_config": {
        "client_id": os.getenv("OIDC_CLIENT_ID"),
        "client_secret": os.getenv("OIDC_CLIENT_SECRET"),
        "server_metadata_url": os.getenv("OIDC_SERVER_METADATA_URL"),
    },
}


router = APIRouter()


@router.get("/login")
async def login(request: Request):
    """
    The login endpoint initiates the OIDC authentication flow by redirecting the user
    to the identity provider's authorization URL.
    """
    client = register_tenant_client(given_tenant_config)
    redirect_uri = str(request.url_for("auth_callback"))

    # Create secure state parameter
    state_data = {
        "tenant_id": given_tenant_config["tenant_id"],
        "nonce": secrets.token_urlsafe(32),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    state_token = jwt.encode({"alg": ALGORITHM}, state_data, SECRET_KEY).decode("utf-8")
    return await client.authorize_redirect(
        request,
        redirect_uri,
        state=state_token,
    )


@router.get("/auth/callback", name="auth_callback")
async def auth_callback(
    request: Request,
    context: RequestContextDep,
    audit: AuditServiceDep,
    db: DatabaseDep,
):
    """
    The authentication callback endpoint processes the response from the identity provider.
    It validates the state parameter, exchanges the authorization code for tokens,
    creates an access token, sets a secure cookie, and logs the authentication event.
    """
    try:
        # Verify state parameter
        state_token = request.query_params.get("state")

        if not state_token:
            raise HTTPException(status_code=400, detail="Missing state parameter")

        # Decode and validate state token
        state_data = jwt.decode(state_token, SECRET_KEY)

        if not state_data:
            raise HTTPException(status_code=400, detail="Invalid state parameter")

        state_data.validate()
        state_time = datetime.fromisoformat(state_data["timestamp"])

        if (datetime.now(timezone.utc) - state_time).seconds > 600:  # 10 min
            raise HTTPException(status_code=400, detail="State expired")

        # Proceed with token exchange
        tenant_id = state_data["tenant_id"]
        tenant_config = (
            given_tenant_config
            if tenant_id == given_tenant_config["tenant_id"]
            else None
        )

        if not tenant_config:
            raise HTTPException(status_code=404, detail="Tenant not found")

        # Exchange code for tokens
        client = register_tenant_client(tenant_config)
        token = await client.authorize_access_token(request)

        if not token:
            raise HTTPException(status_code=400, detail="Failed to obtain access token")

        user_info = token.get("userinfo")
        if not user_info:
            user_info = await client.userinfo(token=token)

        email = user_info.get("email")
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "sub": email,
                "user_id": "sample_user_id",  # Mock user_id
                "tenant_id": tenant_id,
                "roles": "sample_role",  # Mock role
                "department": "sample_department",  # Mock department
            },
            expires_delta=access_token_expires,
        )

        # Log successful login
        main_entry = AuditLogEntry(
            user_id="sample_user_id",
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
            user_id="sample_user_id",
            email=email,
            auth_method="email_only",
            event_type="login_success",
            ip_address=context.client_ip,
            user_agent=context.user_agent,
        )
        await audit.log_auth(log_id, auth_entry)

        # Set secure cookie and redirect
        response = RedirectResponse(url="/")
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

        return response

    except (HTTPException, Exception) as e:
        # Error message
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
