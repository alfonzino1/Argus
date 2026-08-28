"""
Tests for authentication module.
"""
import pytest
from src.utils.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
    authenticate_user,
    generate_secret_key,
    _get_default_users,
)


class TestPasswordHashing:
    """Test password hashing and verification."""
    
    def test_hash_password(self):
        """Test password hashing."""
        password = "test_password123"
        hashed = get_password_hash(password)
        
        assert hashed is not None
        assert hashed != password
        assert len(hashed) > 0
    
    def test_verify_password_correct(self):
        """Test verifying correct password."""
        password = "test_password123"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Test verifying incorrect password."""
        password = "test_password123"
        wrong_password = "wrong_password"
        hashed = get_password_hash(password)
        
        assert verify_password(wrong_password, hashed) is False
    
    def test_verify_password_different_hashes(self):
        """Test that same password produces different hashes."""
        password = "test_password123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        assert hash1 != hash2  # bcrypt includes random salt
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestJWTToken:
    """Test JWT token creation and decoding."""
    
    def test_create_access_token(self):
        """Test creating access token."""
        data = {"sub": "testuser", "role": "admin"}
        token = create_access_token(data)
        
        assert token is not None
        assert len(token) > 0
        assert '.' in token  # JWT format: header.payload.signature
    
    def test_decode_access_token(self):
        """Test decoding valid access token."""
        data = {"sub": "testuser", "role": "admin"}
        token = create_access_token(data)
        
        payload = decode_access_token(token)
        
        assert payload is not None
        assert payload['sub'] == "testuser"
        assert payload['role'] == "admin"
        assert 'exp' in payload
    
    def test_decode_invalid_token(self):
        """Test decoding invalid token."""
        invalid_token = "invalid.token.here"
        payload = decode_access_token(invalid_token)
        
        assert payload is None
    
    def test_decode_expired_token(self):
        """Test decoding expired token."""
        from datetime import timedelta
        data = {"sub": "testuser"}
        token = create_access_token(data, expires_delta=timedelta(seconds=-1))
        
        payload = decode_access_token(token)
        assert payload is None


class TestSecretKeyGeneration:
    """Test secret key generation."""
    
    def test_generate_secret_key(self):
        """Test generating secret key."""
        key1 = generate_secret_key()
        key2 = generate_secret_key()
        
        assert key1 is not None
        assert len(key1) > 32  # Should be at least 32 characters
        assert key1 != key2  # Each key should be unique


class TestAuthenticateUser:
    """Test user authentication."""
    
    def test_authenticate_valid_user(self):
        """Test authenticating with valid credentials."""
        user = authenticate_user("admin", "changeme")
        
        assert user is not None
        assert user['username'] == "admin"
        assert user['disabled'] is False
    
    def test_authenticate_invalid_username(self):
        """Test authenticating with invalid username."""
        user = authenticate_user("nonexistent", "password")
        
        assert user is None
    
    def test_authenticate_invalid_password(self):
        """Test authenticating with invalid password."""
        user = authenticate_user("admin", "wrongpassword")
        
        assert user is None
