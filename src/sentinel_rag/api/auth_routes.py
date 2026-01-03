from fastapi import APIRouter, Request, HTTPException, Response, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from sentinel_rag.auth.tenant_config import get_tenant_config_by_domain, get_tenant_config_by_id
from sentinel_rag.auth.oidc import (
    oauth, 
    register_tenant_client, 
    map_idp_groups_to_roles, 
    create_access_token, 
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from sentinel_rag.auth.models import UserContext
from datetime import timedelta
import os

router = APIRouter()

@router.get("/login")
async def login(request: Request, email: str):
    """
    Initiates the OIDC flow.
    1. Extracts domain from email.
    2. Finds Tenant Config.
    3. Registers Client.
    4. Redirects to IdP.
    """
    if "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email format")
    
    domain = email.split("@")[1]
    tenant_config = get_tenant_config_by_domain(domain)
    
    if not tenant_config:
        raise HTTPException(status_code=404, detail=f"No tenant configuration found for domain {domain}")
    
    # Register the client dynamically
    client = register_tenant_client(tenant_config)
    
    # Store tenant_id in session to retrieve it in callback
    request.session["tenant_id"] = tenant_config.tenant_id
    
    # Build callback URL
    # In production, this should be an env var or constructed properly
    redirect_uri = request.url_for('auth_callback')
    
    return await client.authorize_redirect(request, redirect_uri)

@router.get("/auth/callback", name="auth_callback")
async def auth_callback(request: Request):
    """
    Handles OIDC callback.
    1. Retrieves tenant_id from session.
    2. Exchanges code for token.
    3. Gets user info.
    4. Maps roles.
    5. Issues internal JWT.
    """
    tenant_id = request.session.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Session expired or invalid")
    
    tenant_config = get_tenant_config_by_id(tenant_id)
    if not tenant_config:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    # Re-register/Get client to ensure it exists in this worker process
    client = register_tenant_client(tenant_config)
    
    try:
        token = await client.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OIDC Error: {str(e)}")
        
    user_info = token.get('userinfo')
    if not user_info:
        # Sometimes userinfo is a separate call
        user_info = await client.userinfo(token=token)
        
    # Extract info
    email = user_info.get("email")
    # 'groups' claim depends on IdP configuration. 
    # Okta/Auth0 often need specific scopes or rules to include groups.
    # We assume it's present for this exercise.
    groups = user_info.get("groups", []) 
    
    # Map Roles
    roles = map_idp_groups_to_roles(tenant_id, groups)
    
    # Create Internal User Context (could also sync to DB here)
    # For this exercise, we'll just create the JWT
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": email,
            "user_id": email, # Using email as user_id for simplicity if sub is opaque
            "tenant_id": tenant_id,
            "roles": roles,
            "department": "engineering" # Mock department or extract from claims
        },
        expires_delta=access_token_expires
    )
    
    response = RedirectResponse(url="/") # Redirect to frontend/home
    
    # Set HTTP-only cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True, # Should be True in prod
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    
    return response

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "Logged out successfully"}
