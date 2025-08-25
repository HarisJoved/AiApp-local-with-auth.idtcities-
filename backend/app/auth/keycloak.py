import os
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import requests
from jose import jwt, jwk, JWTError
from jose.utils import base64url_decode
from keycloak import KeycloakOpenID
from app.config.settings import settings

# Security scheme for JWT tokens
security = HTTPBearer()

class KeycloakConfig:
    """Keycloak configuration and client management"""
    
    def __init__(self):
        self.server_url = settings.keycloak_server_url
        self.realm = settings.keycloak_realm
        self.client_id = settings.keycloak_client_id
        self.client_secret = settings.keycloak_client_secret
        self.admin_client_id = settings.keycloak_admin_client_id
        self.admin_username = settings.keycloak_admin_username
        self.admin_password = settings.keycloak_admin_password
        
        # Initialize Keycloak client
        self.keycloak_openid = KeycloakOpenID(
            server_url=self.server_url,
            client_id=self.client_id,
            realm_name=self.realm,
            client_secret_key=self.client_secret,
            verify=True
        )
        
        # Admin client for user management
        self.admin_client = KeycloakOpenID(
            server_url=self.server_url,
            client_id=self.admin_client_id,
            realm_name=self.realm,
            verify=True
        )

class KeycloakUser(BaseModel):
    """Pydantic model for Keycloak user information"""
    sub: str  # User ID
    email: Optional[str] = None
    preferred_username: Optional[str] = None
    name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    email_verified: Optional[bool] = None
    realm_access: Optional[Dict[str, Any]] = None
    resource_access: Optional[Dict[str, Any]] = None

# Global Keycloak configuration instance
_keycloak_config: Optional[KeycloakConfig] = None

def init_keycloak_auth():
    """Initialize Keycloak authentication"""
    global _keycloak_config
    try:
        _keycloak_config = KeycloakConfig()
        print(f"Keycloak initialized: {_keycloak_config.server_url}/realms/{_keycloak_config.realm}")
    except Exception as e:
        print(f"Failed to initialize Keycloak: {e}")
        _keycloak_config = None

def get_keycloak_auth() -> Optional[KeycloakConfig]:
    """Get Keycloak configuration instance"""
    return _keycloak_config

async def verify_jwt_token(token: str) -> Dict[str, Any]:
    """Verify JWT token using JWKS from Keycloak"""
    if not _keycloak_config:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Keycloak authentication not configured"
        )
    
    try:
        # Get the header from the token to find the key ID
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        
        if not kid:
            raise JWTError("Token header missing 'kid' field")
        
        # Fetch JWKS from Keycloak
        jwks_url = f"{_keycloak_config.server_url}/realms/{_keycloak_config.realm}/protocol/openid-connect/certs"
        response = requests.get(jwks_url)
        response.raise_for_status()
        jwks = response.json()
        
        # Find the matching key
        key = None
        for jwk_key in jwks.get("keys", []):
            if jwk_key.get("kid") == kid:
                key = jwk_key
                break
        
        if not key:
            raise JWTError(f"Unable to find key with kid '{kid}' in JWKS")
        
        # Construct the RSA key
        public_key = jwk.construct(key)
        
        # Verify and decode the token
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=_keycloak_config.client_id,
            issuer=f"{_keycloak_config.server_url}/realms/{_keycloak_config.realm}"
        )
        
        return payload
        
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"JWT validation failed: {str(e)}"
        )
    except requests.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to fetch JWKS: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation error: {str(e)}"
        )

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> KeycloakUser:
    """Validate JWT token and return user information"""
    if not _keycloak_config:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Keycloak authentication not configured"
        )
    
    try:
        # Verify JWT token locally
        payload = await verify_jwt_token(credentials.credentials)
        
        # Extract user information from token claims
        user_info = KeycloakUser(
            sub=payload.get("sub"),
            email=payload.get("email"),
            preferred_username=payload.get("preferred_username"),
            name=payload.get("name"),
            given_name=payload.get("given_name"),
            family_name=payload.get("family_name"),
            email_verified=payload.get("email_verified"),
            realm_access=payload.get("realm_access"),
            resource_access=payload.get("resource_access")
        )
        
        return user_info
        
    except HTTPException:
        # Re-raise HTTP exceptions from verify_jwt_token
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication credentials: {str(e)}"
        )

async def get_user_info(access_token: str) -> Optional[Dict[str, Any]]:
    """Get user information from Keycloak using access token"""
    if not _keycloak_config:
        return None
    
    try:
        user_info = _keycloak_config.keycloak_openid.userinfo(access_token)
        return user_info
    except Exception:
        return None

async def introspect_token(access_token: str) -> Optional[Dict[str, Any]]:
    """Introspect token to check if it's valid"""
    if not _keycloak_config:
        return None
    
    try:
        token_info = _keycloak_config.keycloak_openid.introspect(access_token)
        return token_info
    except Exception:
        return None

async def get_keycloak_config() -> Dict[str, Any]:
    """Get Keycloak configuration for frontend"""
    if not _keycloak_config:
        return {}
    
    return {
        "server_url": _keycloak_config.server_url,
        "realm": _keycloak_config.realm,
        "client_id": _keycloak_config.client_id
    }
