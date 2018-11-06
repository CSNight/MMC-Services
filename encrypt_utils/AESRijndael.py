from Crypto.Cipher import AES
from Crypto.Protocol import KDF
from Crypto.Util import Padding
import base64
import os
import sys
import time


class AesRijndael:
    def __init__(self):
        self.encryptSize = 10000000
        self.decryptSize = 10000016
        self.__salt = base64.standard_b64decode("gsf4jvkyhye5/d7k8OrLgM==")
        self.__IV = base64.standard_b64decode("Rkb4jvUy/ye7Cd7k89QQgQ==")
        self.tempFileExt = ".aes"
        self.__iteration_count = 10000
        self.__salt_size = 16

    def aes_encrypt(self, input_byte, encrypt_key):
        pbk_key_instance = KDF.PBKDF2(encrypt_key, self.__salt, dkLen=self.__salt_size, count=self.__iteration_count)
        pbes_key_cipher = AES.new(pbk_key_instance, AES.MODE_CBC, self.__IV)
        pad_byte = Padding.pad(input_byte, AES.block_size)
        secret_res = pbes_key_cipher.encrypt(pad_byte)
        return secret_res

    def aes_decrypt(self, input_byte, encrypt_key):
        pbk_key_instance = KDF.PBKDF2(encrypt_key, self.__salt, dkLen=self.__salt_size, count=self.__iteration_count)
        pbes_key_cipher = AES.new(pbk_key_instance, AES.MODE_CBC, self.__IV)
        desecret_res = pbes_key_cipher.decrypt(input_byte)
        unpad_byte = Padding.unpad(desecret_res, AES.block_size)
        return unpad_byte

    def aes_str_encrypt(self, input_str, encrypt_key):
        return base64.b64encode(self.aes_encrypt(input_str.encode(), encrypt_key)).decode()

    def aes_str_decrypt(self, input_str, decrypt_key):
        return self.aes_decrypt(base64.b64decode(input_str), decrypt_key).decode()

    def aes_file_encrypt(self, file_path, encrypt_key, encrypt_file=None):
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
                        encrypt_chunk = self.aes_encrypt(chunk, encrypt_key)
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

    def aes_file_decrypt(self, encrypt_file, encrypt_key, decrypt_file):
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
                        encrypt_chunk = self.aes_decrypt(chunk, encrypt_key)
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
