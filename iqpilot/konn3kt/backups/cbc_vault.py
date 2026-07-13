"""
Copyright © IQ.Lvbs, apart of Project Teal Lvbs, All Rights Reserved, licensed under https://konn3kt.com/tos

AES-CBC box used to seal/unseal on-device backups. Wire format is unchanged from
prior backups so existing archives still open: 16- or 32-byte key, 16-byte IV,
CBC mode, PKCS#7 block padding.
"""
from Crypto.Cipher import AES

_BLOCK = 16
_ACCEPTED_KEY_LENGTHS = (16, 32)


def _apply_pkcs7(raw: bytes) -> bytes:
  pad_len = _BLOCK - (len(raw) % _BLOCK)
  return raw + bytes((pad_len,)) * pad_len


def _remove_pkcs7(raw: bytes) -> bytes:
  return raw[:-raw[-1]]


class VaultCipher:
  def __init__(self, key: bytes, iv: bytes):
    if len(key) not in _ACCEPTED_KEY_LENGTHS:
      raise ValueError("AES key length must be 16 (AES-128) or 32 (AES-256) bytes")
    if len(iv) != _BLOCK:
      raise ValueError("AES-CBC IV must be exactly 16 bytes")
    self._key = key
    self._iv = iv

  def _fresh_cipher(self):
    return AES.new(self._key, AES.MODE_CBC, self._iv)

  def encrypt(self, plaintext: bytes) -> bytes:
    return self._fresh_cipher().encrypt(_apply_pkcs7(plaintext))

  def decrypt(self, sealed: bytes) -> bytes:
    return _remove_pkcs7(self._fresh_cipher().decrypt(sealed))
