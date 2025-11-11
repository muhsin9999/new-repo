"""
FastAPI dependencies for dependency injection.
Handles authentication, database sessions, and other shared dependencies.
"""
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.security import decode_access_token, verify_api_key
from app.db.session import get_db
from app.models.database import User
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def get_current_user_from_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current user from API key header.

    Args:
        x_api_key: API key from request header
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException: If API key is invalid or missing
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is required",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Query user by API key
    result = await db.execute(
        select(User).where(User.api_key == x_api_key, User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if not user:
        logger.warning("invalid_api_key_attempt", api_key_prefix=x_api_key[:8])
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    logger.info("user_authenticated", user_id=user.id, method="api_key")
    return user


async def get_current_user_from_token(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current user from JWT token in Authorization header.

    Args:
        authorization: Authorization header with Bearer token
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException: If token is invalid or missing
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Query user by ID
    result = await db.execute(
        select(User).where(User.id == user_id, User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.info("user_authenticated", user_id=user.id, method="jwt")
    return user


async def get_current_user(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current user from either API key or JWT token.
    Tries API key first, then falls back to JWT.

    Args:
        x_api_key: Optional API key from header
        authorization: Optional Authorization header with Bearer token
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException: If neither authentication method is valid
    """
    # Try API key first
    if x_api_key:
        try:
            return await get_current_user_from_api_key(x_api_key, db)
        except HTTPException:
            pass

    # Try JWT token
    if authorization:
        return await get_current_user_from_token(authorization, db)

    # No valid authentication found
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide either X-API-Key or Authorization header.",
        headers={"WWW-Authenticate": "Bearer, ApiKey"},
    )


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Verify that the current user is active.

    Args:
        current_user: Current authenticated user

    Returns:
        User object

    Raises:
        HTTPException: If user is not active
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


def check_rate_limit_tier(required_tier: str):
    """
    Dependency factory for checking user's rate limit tier.

    Args:
        required_tier: Required tier level

    Returns:
        Dependency function
    """
    async def _check_tier(current_user: User = Depends(get_current_active_user)) -> User:
        tier_hierarchy = {"free": 0, "basic": 1, "premium": 2, "enterprise": 3}

        user_tier_level = tier_hierarchy.get(current_user.rate_limit_tier, 0)
        required_tier_level = tier_hierarchy.get(required_tier, 0)

        if user_tier_level < required_tier_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This endpoint requires {required_tier} tier or higher",
            )

        return current_user

    return _check_tier
