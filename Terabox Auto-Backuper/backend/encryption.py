"""Criptografia de arquivos usando Fernet (cryptography)."""

import os
import base64
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def generate_key(password: str = None) -> str:
    """Gera uma chave Fernet. Se password for fornecido, deriva a chave dele."""
    if password:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"terabox_autobackup_salt",
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key.decode()
    return Fernet.generate_key().decode()


def get_fernet(key: str) -> Fernet:
    """Retorna instância Fernet a partir da chave."""
    if len(key) == 44 and key.endswith("="):
        return Fernet(key.encode())
    # Assumir que é senha, derivar
    derived = generate_key(key)
    return Fernet(derived.encode())


def encrypt_file(key: str, src_path: str, dst_path: str = None) -> str:
    """Criptografa um arquivo. Retorna o caminho do arquivo criptografado."""
    fernet = get_fernet(key)
    if dst_path is None:
        dst_path = src_path + ".enc"
    with open(src_path, "rb") as f:
        data = f.read()
    encrypted = fernet.encrypt(data)
    Path(dst_path).parent.mkdir(parents=True, exist_ok=True)
    with open(dst_path, "wb") as f:
        f.write(encrypted)
    return dst_path


def decrypt_file(key: str, src_path: str, dst_path: str = None) -> str:
    """Descriptografa um arquivo. Retorna o caminho do arquivo descriptografado."""
    fernet = get_fernet(key)
    if dst_path is None:
        if src_path.endswith(".enc"):
            dst_path = src_path[:-4]
        else:
            dst_path = src_path + ".dec"
    with open(src_path, "rb") as f:
        data = f.read()
    decrypted = fernet.decrypt(data)
    Path(dst_path).parent.mkdir(parents=True, exist_ok=True)
    with open(dst_path, "wb") as f:
        f.write(decrypted)
    return dst_path


class FileEncryptedException(Exception):
    """Arquivo já está criptografado."""
    pass