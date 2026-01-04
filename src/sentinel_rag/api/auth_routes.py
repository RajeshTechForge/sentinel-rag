import os
import secrets
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Request, HTTPException, Response
from fastapi.responses import RedirectResponse
from authlib.jose import jwt
from authlib.jose.errors import JoseError

from sentinel_rag import (
    TenantConfig,
    register_tenant_client,
    create_access_token,
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
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
    client = register_tenant_client(given_tenant_config)
    redirect_uri = str(request.url_for("auth_callback"))

    # Create secure state parameter
    state_data = {
        "tenant_id": given_tenant_config["tenant_id"],
        "nonce": secrets.token_urlsafe(32),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    state_token = jwt.encode({"alg": ALGORITHM}, state_data, SECRET_KEY).decode("utf-8")
    print(redirect_uri, state_token)
    return await client.authorize_redirect(
        request,
        redirect_uri,
        state=state_token,
    )


@router.get("/auth/callback", name="auth_callback")
async def auth_callback(request: Request):
    # Verify state parameter
    state_token = request.query_params.get("state")
    if not state_token:
        raise HTTPException(status_code=400, detail="Missing state parameter")

    try:
        state_data = jwt.decode(state_token, SECRET_KEY)
        state_data.validate()
        state_time = datetime.fromisoformat(state_data["timestamp"])

        if (datetime.now(timezone.utc) - state_time).seconds > 600:  # 10 min
            raise HTTPException(status_code=400, detail="State expired")

        tenant_id = state_data["tenant_id"]

    except HTTPException:
        raise
    except JoseError:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    tenant_config = (
        given_tenant_config if tenant_id == given_tenant_config["tenant_id"] else None
    )
    if not tenant_config:
        raise HTTPException(status_code=404, detail="Tenant not found")

    client = register_tenant_client(tenant_config)

    try:
        token = await client.authorize_access_token(request)
    except Exception:
        raise HTTPException(status_code=400, detail="Authentication failed")

    user_info = token.get("userinfo")
    if not user_info:
        user_info = await client.userinfo(token=token)

    email = user_info.get("email")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": email,
            "user_id": "user_id",  # Mock user_id
            "tenant_id": tenant_id,
            "roles": "sample_role",  # Mock role
            "department": "sample_deparment",  # Mock department
        },
        expires_delta=access_token_expires,
    )

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


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "Logged out successfully"}
