"""
Keycloak authentication router for FastAPI backend.
"""
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.auth.keycloak import get_current_user, get_keycloak_auth, KeycloakUser


router = APIRouter(prefix="/api/auth", tags=["auth"])


class UserInfoResponse(BaseModel):
    """User information response."""
    user_id: str
    email: str
    username: str
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    name: Optional[str] = None
    roles: list[str] = []
    groups: list[str] = []


class TokenInfoResponse(BaseModel):
    """Token information response."""
    active: bool
    exp: Optional[int] = None
    iat: Optional[int] = None
    sub: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    client_id: Optional[str] = None


@router.get("/me", response_model=UserInfoResponse)
async def get_current_user_info(user: KeycloakUser = Depends(get_current_user)):
    """Get current authenticated user information."""
    return UserInfoResponse(
        user_id=user.sub,
        email=user.email,
        username=user.preferred_username,
        given_name=user.given_name,
        family_name=user.family_name,
        name=user.name,
        roles=user.roles,
        groups=user.groups
    )


@router.get("/userinfo")
async def get_detailed_user_info(user: KeycloakUser = Depends(get_current_user)) -> Dict[str, Any]:
    """Get detailed user information from Keycloak."""
    # This would require the access token, which we can get from the request
    # For now, return the basic user info
    return {
        "sub": user.sub,
        "email": user.email,
        "preferred_username": user.preferred_username,
        "given_name": user.given_name,
        "family_name": user.family_name,
        "name": user.name,
        "roles": user.roles,
        "groups": user.groups
    }


@router.post("/token/introspect", response_model=TokenInfoResponse)
async def introspect_token(token: str):
    """Introspect a token to get its information."""
    try:
        auth = get_keycloak_auth()
        token_info = auth.introspect_token(token)
        
        return TokenInfoResponse(
            active=token_info.get("active", False),
            exp=token_info.get("exp"),
            iat=token_info.get("iat"),
            sub=token_info.get("sub"),
            username=token_info.get("username"),
            email=token_info.get("email"),
            client_id=token_info.get("client_id")
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Token introspection failed: {str(e)}")


@router.get("/config")
async def get_auth_config():
    """Get Keycloak configuration for frontend."""
    from app.auth.keycloak import get_keycloak_config
    from app.config.settings import settings
    config = await get_keycloak_config()
    
    if not config:
        raise HTTPException(status_code=503, detail="Keycloak not configured")
    
    # Use external URL for frontend (browser needs to access Keycloak directly)
    frontend_keycloak_url = settings.keycloak_server_url
    
    return {
        "realm": config["realm"],
        "server_url": frontend_keycloak_url,
        "client_id": config["client_id"],
        "public-client": True,  # We're using public client for frontend
        "confidential-port": 0  # Disable confidential port for public client
    }


