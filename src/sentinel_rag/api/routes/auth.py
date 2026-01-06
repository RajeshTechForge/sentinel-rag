import os
import secrets
from datetime import datetime, timezone, timedelta
from typing import List
from fastapi import APIRouter, Request, HTTPException, Response
from fastapi.responses import RedirectResponse, JSONResponse
from authlib.jose import jwt
from pydantic import BaseModel, Field

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


# --- Registration Request Schema ---
class UserRegistrationRequest(BaseModel):
    """Request model for completing new user registration."""

    registration_token: str = Field(
        ..., description="Temporary token from OIDC callback"
    )
    role: str = Field(..., min_length=1, max_length=100, description="User's role")
    department: str = Field(
        ..., min_length=1, max_length=100, description="User's department"
    )


class RegistrationOptionsResponse(BaseModel):
    """Response model containing available roles and departments for registration."""

    departments: List[str]
    roles: List[dict]  # List of {role_name, department_name}


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
    # Validate OIDC configuration before attempting login
    oidc_config = given_tenant_config.get("oidc_config", {})
    missing_config = []

    if not given_tenant_config.get("tenant_id"):
        missing_config.append("TENANT_ID")
    if not oidc_config.get("client_id"):
        missing_config.append("OIDC_CLIENT_ID")
    if not oidc_config.get("client_secret"):
        missing_config.append("OIDC_CLIENT_SECRET")
    if not oidc_config.get("server_metadata_url"):
        missing_config.append("OIDC_SERVER_METADATA_URL")

    if missing_config:
        raise HTTPException(
            status_code=503,
            detail=f"OIDC not configured. Missing environment variables: {', '.join(missing_config)}",
        )

    try:
        client = register_tenant_client(given_tenant_config)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to initialize OIDC client: {str(e)}",
        )

    redirect_uri = str(request.url_for("auth_callback"))

    # Create secure state parameter
    state_data = {
        "tenant_id": given_tenant_config["tenant_id"],
        "nonce": secrets.token_urlsafe(32),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    state_token = jwt.encode({"alg": ALGORITHM}, state_data, SECRET_KEY).decode("utf-8")

    try:
        return await client.authorize_redirect(
            request,
            redirect_uri,
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
        full_name = user_info.get("name", "")

        # Check if user exists in the database
        user = db.get_user_by_email(email)

        if not user:
            # New user detected
            # create a temporary registration token and redirect to registration
            registration_data = {
                "email": email,
                "full_name": full_name,
                "tenant_id": tenant_id,
                "nonce": secrets.token_urlsafe(16),
                "exp": (datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp(),
            }
            registration_token = jwt.encode(
                {"alg": ALGORITHM}, registration_data, SECRET_KEY
            ).decode("utf-8")

            # Return registration required response with token
            return JSONResponse(
                status_code=202,
                content={
                    "status": "registration_required",
                    "message": "New user detected. Please complete registration.",
                    "registration_token": registration_token,
                    "registration_url": str(request.url_for("complete_registration")),
                    "options_url": str(request.url_for("get_registration_options")),
                },
            )

        # Existing user - get their role and department
        user_id = str(user["user_id"])
        role_dept_list = db.get_user_role_and_department(user_id)

        if not role_dept_list:
            raise HTTPException(
                status_code=403,
                detail="User has no assigned role. Please contact administrator.",
            )

        department, role = role_dept_list[0]

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "sub": email,
                "user_id": user_id,
                "tenant_id": tenant_id,
                "roles": role,
                "department": department,
            },
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


@router.get("/register/options", name="get_registration_options")
async def get_registration_options(db: DatabaseDep) -> RegistrationOptionsResponse:
    """
    Get available departments and roles for user registration.
    This endpoint provides the options for the registration form.
    """
    try:
        departments = db.get_all_departments()
        roles = db.get_all_roles()

        return RegistrationOptionsResponse(
            departments=departments,
            roles=roles,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch registration options: {str(e)}"
        )


@router.post("/register", name="complete_registration")
async def complete_registration(
    registration_request: UserRegistrationRequest,
    context: RequestContextDep,
    audit: AuditServiceDep,
    db: DatabaseDep,
):
    """
    Complete new user registration with role and department selection.

    This endpoint is called after OIDC authentication when a new user
    needs to provide their role and department information.
    """
    try:
        # Decode and validate registration token
        token_data = jwt.decode(registration_request.registration_token, SECRET_KEY)
        token_data.validate()

        # Check token expiration
        exp_timestamp = token_data.get("exp")
        if datetime.now(timezone.utc).timestamp() > exp_timestamp:
            raise HTTPException(status_code=400, detail="Registration token expired")

        email = token_data["email"]
        full_name = token_data.get("full_name", "")
        tenant_id = token_data["tenant_id"]

        # Validate department exists
        department_id = db.get_department_id_by_name(registration_request.department)
        if not department_id:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid department: {registration_request.department}",
            )

        # Validate role exists in the selected department
        available_roles = db.get_roles_by_department(registration_request.department)
        if registration_request.role not in available_roles:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid role '{registration_request.role}' for department '{registration_request.department}'",
            )

        # Check if user was already registered (race condition protection)
        existing_user = db.get_user_by_email(email)
        if existing_user:
            raise HTTPException(
                status_code=409, detail="User already registered. Please login again."
            )

        # Create the new user
        user_id = db.create_user(email=email, full_name=full_name)

        # Assign the selected role and department
        db.assign_role(
            user_id=user_id,
            role_name=registration_request.role,
            department_name=registration_request.department,
        )

        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "sub": email,
                "user_id": user_id,
                "tenant_id": tenant_id,
                "roles": registration_request.role,
                "department": registration_request.department,
            },
            expires_delta=access_token_expires,
        )

        # Log successful registration
        main_entry = AuditLogEntry(
            user_id=user_id,
            user_email=email,
            ip_address=context.client_ip,
            user_agent=context.user_agent,
            session_id=context.session_id,
            event_category=EventCategory.AUTHENTICATION,
            event_type="user_registration",
            action=Action.LOGIN,
            outcome=EventOutcome.SUCCESS,
        )
        log_id = await audit.log(main_entry)

        auth_entry = AuthAuditEntry(
            user_id=user_id,
            email=email,
            auth_method="oidc_registration",
            event_type="user_registration",
            ip_address=context.client_ip,
            user_agent=context.user_agent,
        )
        await audit.log_auth(log_id, auth_entry)

        # Set secure cookie and return
        response = JSONResponse(
            status_code=201,
            content={
                "status": "success",
                "message": "Registration completed successfully",
                "user": {
                    "user_id": user_id,
                    "email": email,
                    "full_name": full_name,
                    "role": registration_request.role,
                    "department": registration_request.department,
                },
            },
        )
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        # Log failed registration
        main_entry = AuditLogEntry(
            user_email=token_data.get("email") if "token_data" in dir() else None,
            ip_address=context.client_ip,
            user_agent=context.user_agent,
            event_category=EventCategory.AUTHENTICATION,
            event_type="registration_failure",
            action=Action.LOGIN,
            outcome=EventOutcome.FAILURE,
            error_message=f"Registration failed: {str(e)}",
        )
        log_id = await audit.log(main_entry)

        raise HTTPException(
            status_code=500, detail="Registration failed. Please try again."
        )


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
