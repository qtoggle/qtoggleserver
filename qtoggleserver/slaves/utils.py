
import hashlib
import re


def generate_password(master_key: str, mac_address: str, username: str) -> str:
    mac_stripped = re.sub('[^A-F0-9]', '', mac_address.upper())
    to_hash = f'{master_key}:{mac_stripped}:{username}'

    return hashlib.sha256(to_hash.encode()).hexdigest()[:32]  # Max 32 chars allowed in password
