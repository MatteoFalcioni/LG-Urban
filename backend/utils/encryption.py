"""
Encryption utilities for API keys and sensitive data.
Uses Fernet symmetric encryption for secure storage.
"""

import base64
import os
from cryptography.fernet import Fernet
from typing import Optional


def get_encryption_key() -> bytes:
    """
    Get or generate the encryption key for API keys.
    In production, this should be stored securely (e.g., environment variable, key management service).
    """
    key_str = os.getenv('ENCRYPTION_KEY')
    if not key_str:
        # Generate a new key if none exists (for development)
        key = Fernet.generate_key()
        print(f"Generated new encryption key. Set ENCRYPTION_KEY={key.decode()} in your environment.")
        return key
    
    try:
        return key_str.encode()
    except Exception:
        raise ValueError("Invalid ENCRYPTION_KEY format")


def encrypt_api_key(api_key: str) -> str:
    """
    Encrypt an API key for storage.
    Returns base64-encoded encrypted string.
    """
    if not api_key:
        return ""
    
    key = get_encryption_key()
    fernet = Fernet(key)
    encrypted = fernet.encrypt(api_key.encode())
    return base64.b64encode(encrypted).decode()


def decrypt_api_key(encrypted_key: str) -> str:
    """
    Decrypt an API key from storage.
    Takes base64-encoded encrypted string, returns plain text.
    """
    if not encrypted_key:
        return ""
    
    try:
        key = get_encryption_key()
        fernet = Fernet(key)
        encrypted_bytes = base64.b64decode(encrypted_key.encode())
        decrypted = fernet.decrypt(encrypted_bytes)
        return decrypted.decode()
    except Exception as e:
        raise ValueError(f"Failed to decrypt API key: {e}")


def mask_api_key(api_key: str) -> str:
    """
    Mask an API key for display purposes.
    Shows first few and last few characters.
    """
    if not api_key or len(api_key) < 8:
        return "***"
    
    if api_key.startswith('sk-'):
        # OpenAI key format
        return f"sk-...{api_key[-6:]}"
    elif api_key.startswith('sk-ant-'):
        # Anthropic key format
        return f"sk-ant-...{api_key[-6:]}"
    else:
        # Generic masking
        return f"{api_key[:4]}...{api_key[-4:]}"
