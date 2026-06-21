from datetime import datetime, timedelta, timezone
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import hashlib
import os
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Password Utilities ─────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── JWT Utilities ──────────────────────────────────────────────────────────
def create_access_token(subject: Union[str, int], role: str, extra: dict = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": str(subject),
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: Union[str, int]) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None


# ── AES-256 Encryption (Fernet/PBKDF2) ────────────────────────────────────
def _get_fernet() -> Fernet:
    key_material = settings.AES_ENCRYPTION_KEY.encode()
    salt = b"cybertrace_salt_v1"
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(key_material))
    return Fernet(key)


def encrypt_field(value: str) -> str:
    """Encrypt sensitive field value (PII, evidence metadata)."""
    f = _get_fernet()
    return f.encrypt(value.encode()).decode()


def decrypt_field(encrypted: str) -> str:
    """Decrypt sensitive field value."""
    f = _get_fernet()
    return f.decrypt(encrypted.encode()).decode()


# ── File Integrity ────────────────────────────────────────────────────────
def compute_file_hash(file_bytes: bytes) -> str:
    """SHA-256 hash for evidence chain-of-custody."""
    return hashlib.sha256(file_bytes).hexdigest()


def verify_file_hash(file_bytes: bytes, stored_hash: str) -> bool:
    return compute_file_hash(file_bytes) == stored_hash
