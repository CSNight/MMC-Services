from Crypto import Random
from Crypto.Hash import SHA
from Crypto.Cipher import PKCS1_v1_5 as Cipher_pkcs1_v1_5
from Crypto.Signature import PKCS1_v1_5 as Signature_pkcs1_v1_5
from Crypto.PublicKey import RSA
import base64
import os
import sys
import time


class RsaEncrypt:
    def __init__(self, pubkey_path=None, prikey_path=None):
        self.__pubkey_path = pubkey_path if pubkey_path is not None else 'rsa-public.rpuk'
        self.__prikey_path = prikey_path if prikey_path is not None else 'rsa-private.rprk'
        self.__random_generator = Random.new().read
        self.__rsa = RSA.generate(4096, self.__random_generator)
        self.__block_size = 400
        self.__decrypt_block_size = 512
        self.tempFileExt = ".rsa"

    def new(self, pubkey_path=None, prikey_path=None, pri_password=None):
        pubkey_path = pubkey_path if pubkey_path is not None else self.__pubkey_path
        prikey_path = prikey_path if prikey_path is not None else self.__prikey_path
        private_pem = self.__rsa.exportKey(passphrase=pri_password, pkcs=8,
                                           protection="PBKDF2WithHMAC-SHA1AndAES256-CBC")
        with open(prikey_path, 'wb') as f:
            f.write(private_pem)
        public_pem = self.__rsa.publickey().exportKey(passphrase=pri_password, pkcs=8,
                                                      protection="PBKDF2WithHMAC-SHA1AndAES256-CBC")
        with open(pubkey_path, 'wb') as f:
            f.write(public_pem)

    def sign(self, message, pri_password=None):
        if not os.path.isfile(self.__prikey_path):
            return
        with open(self.__prikey_path) as f:
            key = f.read()
            rsa_key = RSA.importKey(key, passphrase=pri_password)
            signer = Signature_pkcs1_v1_5.new(rsa_key)
            signature = None
            if signer.can_sign():
                digest = SHA.new()
                digest.update(message)
                sign = signer.sign(digest)
                signature = base64.b64encode(sign)
            return signature

    def verify(self, message, signature, pri_password=None):
        if not os.path.isfile(self.__pubkey_path):
            return
        with open(self.__pubkey_path) as f:
            key = f.read()
            rsa_key = RSA.importKey(key, passphrase=pri_password)
            verifier = Signature_pkcs1_v1_5.new(rsa_key)
            digest = SHA.new()
            digest.update(message)
            is_verify = verifier.verify(digest, base64.b64decode(signature))
            return is_verify

    def rsa_byte_encrypt(self, input_byte, pri_password=None):
        if not os.path.isfile(self.__pubkey_path):
            return
        with open(self.__pubkey_path) as f:
            key = f.read()
            rsa_key = RSA.importKey(key, passphrase=pri_password)
            cipher = Cipher_pkcs1_v1_5.new(rsa_key)
            res = bytes()
            block_count = int((len(input_byte) - 1) / self.__block_size + 1)
            for i in range(block_count):
                res = res + cipher.encrypt(input_byte[i * self.__block_size:(i + 1) * self.__block_size])
            return res

    def rsa_byte_decrypt(self, input_byte, pri_password=None):
        if not os.path.isfile(self.__prikey_path):
            return
        with open(self.__prikey_path) as f:
            key = f.read()
            rsa_key = RSA.importKey(key, passphrase=pri_password)
            cipher = Cipher_pkcs1_v1_5.new(rsa_key)
            res = bytes()
            block_count = int((len(input_byte) - 1) / self.__decrypt_block_size + 1)
            for i in range(block_count):
                item = cipher.decrypt(input_byte[i * self.__decrypt_block_size:(i + 1) * self.__decrypt_block_size],
                                      'xyz')
                res = res + item
            return res

    def rsa_str_encrypt(self, input_str, pri_password=None):
        res = self.rsa_byte_encrypt(input_str.encode(), pri_password=pri_password)
        return base64.b64encode(res).decode()

    def rsa_str_decrypt(self, input_str, pri_password=None):
        res = self.rsa_byte_decrypt(base64.b64decode(input_str), pri_password=pri_password)
        return res.decode()

    def rsa_file_encrypt(self, file_path, pri_password=None, encrypt_file=None):
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
                    block_count = int((file_length - 1) / self.__block_size + 1)
                    for i in range(block_count):
                        block_size = self.__block_size
                        if i == block_count - 1:
                            block_size = file_length - i * self.__block_size
                        chunk = old_f.read(block_size)
                        encrypt_chunk = self.rsa_byte_encrypt(chunk, pri_password)
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

    def rsa_file_decrypt(self, encrypt_file, decrypt_file, pri_password=None):
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
                    block_count = int((file_length - 1) / self.__decrypt_block_size + 1)
                    for i in range(block_count):
                        block_size = self.__decrypt_block_size
                        if i == block_count - 1:
                            block_size = file_length - i * self.__decrypt_block_size
                        chunk = old_f.read(block_size)
                        encrypt_chunk = self.rsa_byte_decrypt(chunk, pri_password)
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
