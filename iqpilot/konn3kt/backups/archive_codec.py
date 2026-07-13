"""
Copyright © IQ.Lvbs, apart of Project Teal Lvbs, All Rights Reserved, licensed under https://konn3kt.com/tos

Seals/unseals backup payloads. The on-device RSA key is hashed to an AES key+IV,
the payload is zlib-wrapped (a 4-byte "ZLIB" magic prefix), AES-CBC sealed, then
base64 armoured. The byte format is unchanged so existing archives still open.
"""
import base64
import hashlib
import json
import re
import zlib
from pathlib import Path

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from iqpilot.konn3kt.backups.cbc_vault import VaultCipher
from openpilot.system.hardware.hw import Paths

_ZLIB_TAG = b"ZLIB"


def _canonical_der(pem_bytes: bytes) -> bytes:
  """Canonical DER for an RSA key PEM, accepting either the public or private half."""
  hint = pem_bytes.decode(errors="ignore").lower()
  if "private" in hint:
    key = serialization.load_pem_private_key(pem_bytes, password=None, backend=default_backend())
    if not isinstance(key, rsa.RSAPrivateKey):
      raise ValueError("Invalid RSA key format: Unable to determine if key is public or private.")
    return key.private_bytes(serialization.Encoding.DER, serialization.PrivateFormat.TraditionalOpenSSL,
                             serialization.NoEncryption())
  if "public" in hint:
    key = serialization.load_pem_public_key(pem_bytes, backend=default_backend())
    if not isinstance(key, rsa.RSAPublicKey):
      raise ValueError("Invalid RSA key format: Unable to determine if key is public or private.")
    return key.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.PKCS1)
  raise ValueError("Unknown key format: Unable to determine if key is public or private.")


def _key_iv_from_rsa(key_path: str, aes_256: bool) -> tuple[bytes, bytes]:
  with open(key_path, "rb") as fh:
    digest = hashlib.sha256(_canonical_der(fh.read())).digest()
  return (digest[:32] if aes_256 else digest[:16]), digest[16:32]


def _cipher(aes_256: bool) -> VaultCipher:
  key_name = "id_rsa" if aes_256 else "id_rsa.pub"
  key_path = Path(Paths.persist_root()) / "comma" / key_name
  key, iv = _key_iv_from_rsa(str(key_path), aes_256)
  return VaultCipher(key, iv)


def _zlib_wrap(payload: bytes) -> bytes:
  return _ZLIB_TAG + zlib.compress(payload, level=9)


def _zlib_unwrap(blob: bytes) -> bytes:
  return zlib.decompress(blob[len(_ZLIB_TAG):])


def seal_backup_blob(text: str, use_aes_256: bool = True) -> str:
  try:
    sealed = _cipher(use_aes_256).encrypt(_zlib_wrap(text.encode("utf-8")))
    return base64.b64encode(sealed).decode("utf-8")
  except Exception as e:
    print(f"Compression and encryption failed: {e}")
    return ""


def unseal_backup_blob(armoured: str, use_aes_256: bool = False) -> str:
  try:
    plain = _cipher(use_aes_256).decrypt(base64.b64decode(armoured))
    return _zlib_unwrap(plain).decode("utf-8")
  except Exception as e:
    print(f"Decryption and decompression failed: {e}")
    return ""


_CAMEL_BOUNDARY_A = re.compile(r'(.)([A-Z][a-z]+)')
_CAMEL_BOUNDARY_B = re.compile(r'([a-z0-9])([A-Z])')


def _snake(name: str) -> str:
  return _CAMEL_BOUNDARY_B.sub(r'\1_\2', _CAMEL_BOUNDARY_A.sub(r'\1_\2', name)).lower()


def _snake_keys(obj):
  if isinstance(obj, dict):
    return {_snake(k): _snake_keys(v) for k, v in obj.items()}
  if isinstance(obj, list):
    return [_snake_keys(v) for v in obj]
  return obj


class SnakeKeyEncoder(json.JSONEncoder):
  def encode(self, obj):
    return super().encode(_snake_keys(obj))
