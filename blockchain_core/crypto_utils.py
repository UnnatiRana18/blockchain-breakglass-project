"""
Cryptographic utility module: SHA-256, Merkle tree construction, and AES-256-GCM cipher.
"""
import hashlib
import json
import os
import base64
from typing import List, Dict, Any, Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def sha256(data: str) -> str:
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

def hash_dict(d: Dict[str, Any]) -> str:
    serialized = json.dumps(d, sort_keys=True)
    return sha256(serialized)

def build_merkle_tree(leaves: List[str]) -> Tuple[str, List[List[str]]]:
    if not leaves:
        empty_root = sha256("EMPTY_TREE")
        return empty_root, [[empty_root]]
    current_level = [l if len(l) == 64 else sha256(str(l)) for l in leaves]
    tree = [current_level]
    while len(current_level) > 1:
        next_level = []
        for i in range(0, len(current_level), 2):
            left = current_level[i]
            right = current_level[i + 1] if i + 1 < len(current_level) else left
            next_level.append(sha256(left + right))
        current_level = next_level
        tree.append(current_level)
    return current_level[0], tree

class EnvelopeEncryption:
    def __init__(self, key: bytes = None):
        self.key = key if key is not None else AESGCM.generate_key(bit_length=256)
        self.aesgcm = AESGCM(self.key)

    def encrypt_json(self, payload: Dict[str, Any]) -> Dict[str, str]:
        data_bytes = json.dumps(payload).encode('utf-8')
        nonce = os.urandom(12)
        ciphertext = self.aesgcm.encrypt(nonce, data_bytes, None)
        return {
            "nonce": base64.b64encode(nonce).decode('utf-8'),
            "ciphertext": base64.b64encode(ciphertext).decode('utf-8'),
            "payload_hash": sha256(json.dumps(payload, sort_keys=True))
        }

    def decrypt_json(self, encrypted_bundle: Dict[str, str]) -> Dict[str, Any]:
        nonce = base64.b64decode(encrypted_bundle["nonce"].encode('utf-8'))
        ciphertext = base64.b64decode(encrypted_bundle["ciphertext"].encode('utf-8'))
        decrypted_bytes = self.aesgcm.decrypt(nonce, ciphertext, None)
        return json.loads(decrypted_bytes.decode('utf-8'))
