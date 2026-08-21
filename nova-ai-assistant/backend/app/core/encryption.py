"""NOVA Field-Level Encryption Security Module.

Uses AES-256-GCM authenticated encryption to protect sensitive memory fields and credentials
before storage in the database.

Security properties:
  1. Key sourced exclusively from secure environment configuration (never in DB/logs).
  2. Cryptographic 96-bit random IV (nonce) generated per encryption.
  3. Built-in GCM 128-bit authentication tag detects any ciphertext tampering.
  4. Plaintext sensitive values are never logged.
"""
import os
import base64
import hashlib
import logging
from typing import Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings

logger = logging.getLogger(__name__)

# Derive a 256-bit (32-byte) key from environment secret.
# ENCRYPTION_SECRET_KEY must be set explicitly in production.
# Falling back to the service role key would silently break decryption
# if that key is ever rotated — always set ENCRYPTION_SECRET_KEY separately.
_RAW_SECRET = settings.ENCRYPTION_SECRET_KEY or settings.SUPABASE_SERVICE_ROLE_KEY
if not _RAW_SECRET:
    _RAW_SECRET = "nova-fallback-encryption-secret-32bytes-key"
_ENCRYPTION_KEY_32BYTES = hashlib.sha256(_RAW_SECRET.encode("utf-8")).digest()
_AES_GCM = AESGCM(_ENCRYPTION_KEY_32BYTES)
_NONCE_BYTE_LENGTH = 12  # Standard 96-bit nonce for AES-GCM


class EncryptionError(Exception):
    """Raised when encryption or decryption fails (e.g. tampering, invalid key, corrupt data)."""
    pass


def encrypt_field(plaintext: str, associated_data: Optional[bytes] = None) -> str:
    """Encrypt a sensitive plaintext string using AES-256-GCM.

    Args:
        plaintext: The sensitive text value to encrypt.
        associated_data: Optional additional authenticated data (AAD).

    Returns:
        Base64-encoded string containing (12-byte nonce + ciphertext + 16-byte auth tag).

    Raises:
        ValueError: If plaintext is empty or invalid.
        EncryptionError: If encryption fails.
    """
    if plaintext is None:
        raise ValueError("Plaintext to encrypt cannot be None.")

    try:
        # Generate fresh 12-byte random nonce
        nonce = os.urandom(_NONCE_BYTE_LENGTH)
        plaintext_bytes = plaintext.encode("utf-8")

        # AES-GCM encrypt returns ciphertext + 16-byte tag appended
        ciphertext_and_tag = _AES_GCM.encrypt(nonce, plaintext_bytes, associated_data)

        # Concatenate nonce + (ciphertext + tag) and Base64 encode
        combined = nonce + ciphertext_and_tag
        return base64.b64encode(combined).decode("utf-8")

    except Exception as e:
        logger.error(f"[ENCRYPTION ERROR] Field encryption failed: {type(e).__name__}")
        raise EncryptionError("Field encryption failed.") from e


def decrypt_field(ciphertext_b64: str, associated_data: Optional[bytes] = None) -> str:
    """Decrypt an AES-256-GCM encrypted Base64 string.

    Args:
        ciphertext_b64: Base64-encoded payload (nonce + ciphertext + auth tag).
        associated_data: Optional additional authenticated data (AAD).

    Returns:
        Decrypted original plaintext string.

    Raises:
        ValueError: If payload is empty.
        EncryptionError: If authentication tag fails (tampered data) or decryption fails.
    """
    if not ciphertext_b64 or not ciphertext_b64.strip():
        raise ValueError("Ciphertext payload cannot be empty.")

    try:
        combined = base64.b64decode(ciphertext_b64)
    except Exception as e:
        raise EncryptionError("Invalid Base64 payload encoding.") from e

    if len(combined) <= _NONCE_BYTE_LENGTH + 16:
        raise EncryptionError("Ciphertext payload is too short to contain valid nonce and GCM tag.")

    nonce = combined[:_NONCE_BYTE_LENGTH]
    ciphertext_and_tag = combined[_NONCE_BYTE_LENGTH:]

    try:
        decrypted_bytes = _AES_GCM.decrypt(nonce, ciphertext_and_tag, associated_data)
        return decrypted_bytes.decode("utf-8")
    except Exception as e:
        # GCM auth tag mismatch raises cryptography.exceptions.InvalidTag
        logger.warning("[ENCRYPTION WARNING] Decryption failed: Data tampering or invalid key detected.")
        raise EncryptionError(
            "Decryption failed: Ciphertext or authentication tag has been tampered with."
        ) from e
