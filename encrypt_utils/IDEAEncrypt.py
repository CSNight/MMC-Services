import os
import sys
import time
import base64
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding, hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import modes, Cipher
from cryptography.hazmat.primitives.ciphers.algorithms import IDEA


class IdeaEncrypt:
    def __init__(self):
        self.encryptSize = 10000000
        self.decryptSize = 10000008
        self.__salt = base64.standard_b64decode("gsf4jvkyhye5/d7k8OrLgM==")
        self.__IV = base64.standard_b64decode("Rkb4jvUy/ye7Cd7k89QQgQ==")
        self.tempFileExt = ".idea"
        self.__iteration_count = 10000
        self.__salt_size = 16
        self._backend = default_backend()

    def idea_byte_encrypt(self, input_byte, encrypt_key):
        padder = padding.PKCS7(IDEA.block_size).padder()
        padded_data = padder.update(input_byte) + padder.finalize()
        pbk = PBKDF2HMAC(hashes.SHA256, self.__salt_size, self.__salt, self.__iteration_count, self._backend)
        pbk_key = pbk.derive(encrypt_key.encode())
        encryptor = Cipher(
            IDEA(pbk_key), modes.CBC(self.__IV[0:8]), self._backend
        ).encryptor()
        cipher_text = encryptor.update(padded_data) + encryptor.finalize()
        return cipher_text

    def idea_byte_decrypt(self, input_byte, encrypt_key):
        pbk = PBKDF2HMAC(hashes.SHA256, self.__salt_size, self.__salt, self.__iteration_count, self._backend)
        pbk_key = pbk.derive(encrypt_key.encode())
        decryptor = Cipher(
            IDEA(pbk_key), modes.CBC(self.__IV[0:8]), self._backend
        ).decryptor()
        cipher_text = decryptor.update(input_byte) + decryptor.finalize()
        un_padder = padding.PKCS7(IDEA.block_size).unpadder()
        un_padded_data = un_padder.update(cipher_text) + un_padder.finalize()
        return un_padded_data

    def idea_str_encrypt(self, input_str, encrypt_key):
        return base64.b64encode(self.idea_byte_encrypt(input_str.encode(), encrypt_key)).decode()

    def idea_str_decrypt(self, input_str, decrypt_key):
        return self.idea_byte_decrypt(base64.b64decode(input_str), decrypt_key).decode()

    def idea_file_encrypt(self, file_path, encrypt_key, encrypt_file=None):
        if not os.path.isfile(file_path):
            return
        if encrypt_file is None:
            encrypt_file = file_path[0:str(file_path).rindex('.')] + self.tempFileExt
        if os.path.isfile(encrypt_file):
            os.remove(encrypt_file)
        with open(file_path, 'rb+') as old_f:
            with open(encrypt_file, "ab+") as new_f:
                if old_f.readable():
                    file_length = os.path.getsize(file_path)
                    block_count = int((file_length - 1) / self.encryptSize + 1)
                    for i in range(block_count):
                        block_size = self.encryptSize
                        if i == block_count - 1:
                            block_size = file_length - i * self.encryptSize
                        chunk = old_f.read(block_size)
                        encrypt_chunk = self.idea_byte_encrypt(chunk, encrypt_key)
                        new_f.write(encrypt_chunk)
                        new_f.flush()
                        del chunk, encrypt_chunk, block_size
                        sys.stdout.write(
                            "\r" + "process status:%.3f%% eta:%.3fs" % (
                                float(i * 100 / block_count), round(time.process_time(), 2)))
                new_f.flush()
                new_f.close()
            old_f.flush()
            old_f.close()
        print("\r" + "process done!")

    def idea_file_decrypt(self, encrypt_file, encrypt_key, decrypt_file):
        if not os.path.isfile(encrypt_file):
            return
        if decrypt_file is None:
            encrypt_file = encrypt_file[0:str(encrypt_file).rindex('.')] + self.tempFileExt
        if os.path.isfile(decrypt_file):
            os.remove(decrypt_file)
        with open(encrypt_file, 'rb+') as old_f:
            with open(decrypt_file, "ab+") as new_f:
                if old_f.readable():
                    file_length = os.path.getsize(encrypt_file)
                    block_count = int((file_length - 1) / self.decryptSize + 1)
                    for i in range(block_count):
                        block_size = self.decryptSize
                        if i == block_count - 1:
                            block_size = file_length - i * self.decryptSize
                        chunk = old_f.read(block_size)
                        encrypt_chunk = self.idea_byte_decrypt(chunk, encrypt_key)
                        new_f.write(encrypt_chunk)
                        new_f.flush()
                        del chunk, encrypt_chunk, block_size
                        sys.stdout.write(
                            "\r" + "process status:%.3f%% eta:%.3fs" % (
                                float(i * 100 / block_count), round(time.process_time(), 2)))
                new_f.flush()
                new_f.close()
            old_f.flush()
            old_f.close()
        print("\r" + "process done!")
