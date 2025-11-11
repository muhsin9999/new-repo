"""
Authentication endpoints for API key and JWT management.
"""
from typing import Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, create_refresh_token, verify_refresh_token
from app.db.repositories.user_repo import UserRepository
from app.db.session import get_db
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


# Request/Response models
class RegisterRequest(BaseModel):
    """Registration request model."""
    email: Optional[EmailStr] = None


class RegisterResponse(BaseModel):
    """Registration response model."""
    user_id: str
    api_key: str
    message: str


class TokenRequest(BaseModel):
    """Token request model."""
    api_key: str


class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


class RefreshTokenRequest(BaseModel):
    """Refresh token request model."""
    refresh_token: str


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=RegisterResponse,
    summary="Register and get API key"
)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db)
) -> RegisterResponse:
    """
    Register a new user and generate an API key.
    Returns the API key that should be used for subsequent requests.

    Note: The API key is only shown once. Store it securely.
    """
    user_repo = UserRepository(db)

    # Check if email already exists
    if request.email:
        existing_user = await user_repo.get_user_by_email(request.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

    # Create user
    user, plain_api_key = await user_repo.create_user(email=request.email)

    logger.info("user_registered", user_id=user.id, email=request.email)

    return RegisterResponse(
        user_id=user.id,
        api_key=plain_api_key,
        message="API key created successfully. Store it securely - it won't be shown again."
    )


@router.post(
    "/token",
    status_code=status.HTTP_200_OK,
    response_model=TokenResponse,
    summary="Get JWT token"
)
async def get_token(
    request: TokenRequest,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """
    Exchange API key for JWT tokens.
    Returns both access token and refresh token.

    The access token should be used in the Authorization header:
    `Authorization: Bearer <access_token>`
    """
    user_repo = UserRepository(db)

    # Verify API key and get user
    user = await user_repo.get_user_by_api_key(request.api_key)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    # Create tokens
    access_token = create_access_token(data={"sub": user.id})
    refresh_token = create_refresh_token(data={"sub": user.id})

    logger.info("tokens_issued", user_id=user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=3600
    )


@router.post(
    "/refresh",
    status_code=status.HTTP_200_OK,
    response_model=TokenResponse,
    summary="Refresh JWT token"
)
async def refresh_access_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """
    Refresh an expired access token using a refresh token.
    Returns new access and refresh tokens.
    """
    try:
        payload = verify_refresh_token(request.refresh_token)
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        user_repo = UserRepository(db)
        user = await user_repo.get_user_by_id(user_id)

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )

        # Create new tokens
        access_token = create_access_token(data={"sub": user.id})
        new_refresh_token = create_refresh_token(data={"sub": user.id})

        logger.info("tokens_refreshed", user_id=user.id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=3600
        )

    except Exception as e:
        logger.error("token_refresh_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )


@router.delete(
    "/revoke",
    status_code=status.HTTP_200_OK,
    summary="Revoke API key"
)
async def revoke_api_key(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Revoke an API key to prevent further use.
    This will deactivate the user account.
    """
    user_repo = UserRepository(db)

    success = await user_repo.revoke_api_key(x_api_key)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    logger.info("api_key_revoked")

    return {"message": "API key revoked successfully"}
