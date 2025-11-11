"""
Unit tests for security module.
"""
import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_api_key,
    hash_api_key,
    verify_api_key,
)


class TestAPIKey:
    """Tests for API key generation and verification."""

    def test_generate_api_key(self):
        """Test API key generation."""
        key1 = generate_api_key()
        key2 = generate_api_key()

        assert len(key1) > 0
        assert len(key2) > 0
        assert key1 != key2  # Should be unique

    def test_hash_api_key(self):
        """Test API key hashing."""
        plain_key = "test-api-key-123"
        hashed = hash_api_key(plain_key)

        assert hashed != plain_key
        assert len(hashed) > len(plain_key)

    def test_verify_api_key(self):
        """Test API key verification."""
        plain_key = "test-api-key-456"
        hashed = hash_api_key(plain_key)

        # Correct key should verify
        assert verify_api_key(plain_key, hashed) is True

        # Incorrect key should not verify
        assert verify_api_key("wrong-key", hashed) is False


class TestJWT:
    """Tests for JWT token operations."""

    def test_create_access_token(self):
        """Test JWT token creation."""
        data = {"sub": "user123"}
        token = create_access_token(data)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_access_token(self):
        """Test JWT token decoding."""
        data = {"sub": "user123"}
        token = create_access_token(data)

        decoded = decode_access_token(token)

        assert decoded["sub"] == "user123"
        assert "exp" in decoded
        assert "iat" in decoded

    def test_decode_invalid_token(self):
        """Test decoding invalid token."""
        from app.core.exceptions import AuthenticationError

        with pytest.raises(AuthenticationError):
            decode_access_token("invalid-token")

    def test_token_with_custom_expiration(self):
        """Test token creation with custom expiration."""
        from datetime import timedelta

        data = {"sub": "user456"}
        expires = timedelta(minutes=30)
        token = create_access_token(data, expires_delta=expires)

        decoded = decode_access_token(token)
        assert decoded["sub"] == "user456"
