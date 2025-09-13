"""
Authentication utilities for JWT token management and password hashing.
Provides JWT token generation, validation, and role-based claims.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings
from app.models.user import UserRole
import uuid


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenPayload:
    """JWT token payload structure."""
    
    def __init__(self, user_id: str, email: str, role: Optional[str], exp: datetime):
        self.user_id = user_id
        self.email = email
        self.role = role
        self.exp = exp
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TokenPayload":
        """Create TokenPayload from dictionary."""
        return cls(
            user_id=data["sub"],
            email=data["email"],
            role=data.get("role"),  # Role is optional for refresh tokens
            exp=datetime.fromtimestamp(data["exp"])
        )


def create_access_token(
    user_id: uuid.UUID,
    email: str,
    role: UserRole,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT access token with user claims.
    
    Args:
        user_id: User's UUID
        email: User's email address
        role: User's role (agent/admin)
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT token string
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode = {
        "sub": str(user_id),  # Subject (user ID)
        "email": email,
        "role": role.value,
        "exp": expire,
        "iat": datetime.utcnow(),  # Issued at
        "type": "access"
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    
    return encoded_jwt


def create_refresh_token(
    user_id: uuid.UUID,
    email: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT refresh token.
    
    Args:
        user_id: User's UUID
        email: User's email address
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT refresh token string
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.jwt_refresh_token_expire_days)
    
    to_encode = {
        "sub": str(user_id),
        "email": email,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Optional[TokenPayload]:
    """
    Verify and decode JWT token.
    
    Args:
        token: JWT token string
        token_type: Expected token type ("access" or "refresh")
        
    Returns:
        TokenPayload if valid, None if invalid
        
    Raises:
        JWTError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        
        # Verify token type
        if payload.get("type") != token_type:
            raise JWTError(f"Invalid token type. Expected {token_type}")
        
        # Check if token has expired
        exp_timestamp = payload.get("exp")
        if exp_timestamp and datetime.fromtimestamp(exp_timestamp) < datetime.utcnow():
            raise JWTError("Token has expired")
        
        # Validate required fields
        user_id = payload.get("sub")
        email = payload.get("email")
        
        if not user_id or not email:
            raise JWTError("Invalid token payload")
        
        return TokenPayload.from_dict(payload)
        
    except JWTError:
        raise
    except Exception as e:
        raise JWTError(f"Token validation error: {str(e)}")


def hash_password(password: str) -> str:
    """
    Hash password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string
        
    Raises:
        ValueError: If password is too short
    """
    if not password or len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password against hash.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password from database
        
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def extract_token_from_header(authorization: str) -> str:
    """
    Extract JWT token from Authorization header.
    
    Args:
        authorization: Authorization header value
        
    Returns:
        JWT token string
        
    Raises:
        ValueError: If header format is invalid
    """
    if not authorization:
        raise ValueError("Authorization header is required")
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError("Invalid authentication scheme")
        return token
    except ValueError:
        raise ValueError("Invalid authorization header format")