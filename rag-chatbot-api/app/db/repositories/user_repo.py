"""
User repository for database operations.
"""
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.security import generate_api_key, hash_api_key
from app.models.database import User
from app.utils.logging import get_logger

logger = get_logger(__name__)


class UserRepository:
    """Repository for user database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_user(self, email: Optional[str] = None, rate_limit_tier: str = "free") -> tuple[User, str]:
        """
        Create a new user with an API key.

        Args:
            email: Optional user email
            rate_limit_tier: Rate limit tier (free, basic, premium, enterprise)

        Returns:
            Tuple of (User object, plain API key)
        """
        # Generate API key
        plain_api_key = generate_api_key()
        hashed_key = hash_api_key(plain_api_key)

        # Create user
        user = User(
            email=email,
            api_key=plain_api_key,  # Store plain key for retrieval (in production, show once)
            api_key_hash=hashed_key,
            is_active=True,
            rate_limit_tier=rate_limit_tier
        )

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        logger.info("user_created", user_id=user.id, email=email, tier=rate_limit_tier)

        return user, plain_api_key

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User object or None
        """
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_user_by_api_key(self, api_key: str) -> Optional[User]:
        """
        Get user by API key.

        Args:
            api_key: API key

        Returns:
            User object or None
        """
        result = await self.db.execute(
            select(User).where(User.api_key == api_key)
        )
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email.

        Args:
            email: User email

        Returns:
            User object or None
        """
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def deactivate_user(self, user_id: str) -> bool:
        """
        Deactivate a user.

        Args:
            user_id: User ID

        Returns:
            True if successful
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            return False

        user.is_active = False
        await self.db.commit()

        logger.info("user_deactivated", user_id=user_id)
        return True

    async def revoke_api_key(self, api_key: str) -> bool:
        """
        Revoke an API key by deactivating the user.

        Args:
            api_key: API key to revoke

        Returns:
            True if successful
        """
        user = await self.get_user_by_api_key(api_key)
        if not user:
            return False

        return await self.deactivate_user(user.id)

    async def update_rate_limit_tier(self, user_id: str, tier: str) -> bool:
        """
        Update user's rate limit tier.

        Args:
            user_id: User ID
            tier: New rate limit tier

        Returns:
            True if successful
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            return False

        user.rate_limit_tier = tier
        await self.db.commit()

        logger.info("user_tier_updated", user_id=user_id, new_tier=tier)
        return True
