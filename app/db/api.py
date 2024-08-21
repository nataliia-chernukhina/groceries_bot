import logging
from mongoengine import connect as _mongo_connect
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from app.constants import APP_BASE64_KEY


def connect():
    connection = _mongo_connect('groceries-bot-mongo', host='localhost')
    logging.info(f"Connecting to {connection}")


def get_key(salt):
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt.encode(),
        iterations=100000,
        backend=default_backend()
    )
    return base64.urlsafe_b64encode(kdf.derive(APP_BASE64_KEY))


def encrypt(data, salt):
    fernet = Fernet(get_key(salt))
    return fernet.encrypt(data.encode())


def decrypt(data, salt):
    fernet = Fernet(get_key(salt))
    return fernet.decrypt(data).decode()
