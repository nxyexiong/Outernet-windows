import base64
import hashlib
import os
import struct
from Crypto import Random
from Crypto.Cipher import AES, ChaCha20
from Crypto.Util import Padding

class AESCipher:

    def __init__(self, secret):
        self.pack_iv_len = 16
        self.pack_pad_len = 32
        self.key = hashlib.sha256(secret).digest()

    def encrypt(self, raw):
        raw = Padding.pad(raw, self.pack_pad_len)
        iv = Random.new().read(self.pack_iv_len)
        cipher = AES.new(self.key, AES.MODE_CFB, iv)
        return iv + cipher.encrypt(raw)

    def decrypt(self, enc):
        iv = enc[:self.pack_iv_len]
        cipher = AES.new(self.key, AES.MODE_CFB, iv)
        raw = cipher.decrypt(enc[self.pack_iv_len:])
        return Padding.unpad(raw, self.pack_pad_len)

    def encrypt_all(self, raw):
        '''length of data must be under 65536'''
        enc = self.encrypt(raw)
        elen = len(enc)
        return struct.pack('!H', elen) + enc

    def decrypt_all(self, enc):
        '''returns decrypted data and length of decrypted ciphertext'''
        result = b''
        dlen = 0
        while enc:
            if len(enc) < 2:
                return result, dlen
            elen, = struct.unpack('!H', enc[:2])
            if len(enc) < 2 + elen:
                return result, dlen
            result += self.decrypt(enc[2:2 + elen])
            dlen += 2 + elen
            enc = enc[2 + elen:]
        return result, dlen


class Chacha20Cipher:

    def __init__(self, secret):
        self.nonce_len = 8
        self.key = hashlib.sha256(secret).digest()

    def encrypt(self, raw):
        nonce = Random.new().read(self.nonce_len)
        cipher = ChaCha20.new(key=self.key, nonce=nonce)
        return nonce + cipher.encrypt(raw)

    def decrypt(self, enc):
        nonce = enc[:self.nonce_len]
        cipher = ChaCha20.new(key=self.key, nonce=nonce)
        return cipher.decrypt(enc[self.nonce_len:])


if __name__ == "__main__":
    # AES
    cipher = AESCipher(b'test')
    data = os.urandom(12345)
    edata = cipher.encrypt_all(data)
    ddata, dlen = cipher.decrypt_all(edata)
    assert data == ddata
    assert dlen == len(edata)

    # Chacha20
    cipher = Chacha20Cipher(b'test')
    data = b'haha'
    edata = cipher.encrypt(data)
    ddata = cipher.decrypt(edata)
    assert data == ddata

    print('test ok')