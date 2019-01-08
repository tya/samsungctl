# -*- coding: utf-8 -*-

from __future__ import print_function
from Crypto.Cipher import AES
import hashlib
import keys
import struct
from .pyrijndael.rijndael import Rijndael

import logging

logger = logging.getLogger('samsungctl')

BLOCK_SIZE = 16
SHA_DIGEST_LENGTH = 20

USER_ID_POS = 15
USER_ID_LEN_POS = 11
GX_SIZE = 0x80


def encrypt_parameter_data_with_aes(inpt):
    iv = b"\x00" * BLOCK_SIZE
    output = b""
    for num in range(0, 128, 16):
        cipher = AES.new(
            bytes(bytearray.fromhex(keys.wbKey)),
            AES.MODE_CBC,
            iv
        )
        output += cipher.encrypt(inpt[num:num+16])
    return output


def decrypt_parameter_data_with_aes(inpt):
    iv = b"\x00" * BLOCK_SIZE
    output = b""
    for num in range(0, 128, 16):
        cipher = AES.new(
            bytes(bytearray.fromhex(keys.wbKey)),
            AES.MODE_CBC,
            iv
        )

        output += cipher.decrypt(inpt[num:num+16])
    return output


def apply_samygo_key_transform(input):
    r = Rijndael(bytes(bytearray.fromhex(keys.transKey)))
    return r.encrypt(input)


def generate_server_hello(user_id, pin):
    sha1 = hashlib.sha1()
    sha1.update(pin.encode('utf-8'))

    pin_hash = sha1.digest()
    logger.debug('crypto: pin hash: ', pin_hash)

    aes_key = pin_hash[:16]
    logger.debug('crypto: aes: ', aes_key)

    iv = b"\x00" * BLOCK_SIZE
    cipher = AES.new(aes_key, AES.MODE_CBC, iv)

    encrypted = cipher.encrypt(bytes(bytearray.fromhex(keys.publicKey)))
    logger.debug('crypto: aes encrypted: ', encrypted.hex())

    swapped = encrypt_parameter_data_with_aes(encrypted)
    logger.debug('crypto: aes swapped: ', swapped)

    data = struct.pack(">I", len(user_id)) + user_id.encode('utf-8') + swapped
    logger.debug('crypto: data buffer: ', data)

    sha1 = hashlib.sha1()
    sha1.update(data)

    data_hash = sha1.digest()
    logger.debug('crypto: data hash: ', data_hash)

    server_hello = (
        b"\x01\x02" +
        (b"\x00" * 5) +
        struct.pack(">I", len(user_id) + 132) +
        data +
        (b"\x00" * 5)
    )

    return server_hello, data_hash, aes_key


def parse_client_hello(client_hello, data_hash, aes_key, g_user_id):

    data = bytes(bytearray.fromhex(client_hello))
    logger.debug('crypto: client hello: ', data)

    first_len = struct.unpack(">I", data[7:11])[0]
    user_id_len = struct.unpack(">I", data[11:15])[0]

    # Always equals firstLen????:)
    dest_len = user_id_len + 132 + SHA_DIGEST_LENGTH
    third_len = user_id_len + 132

    start = USER_ID_LEN_POS
    stop = third_len + USER_ID_LEN_POS

    dest = data[start:stop] + data_hash
    logger.debug('crypto: dest: ', dest)

    start = USER_ID_POS
    stop = user_id_len + USER_ID_POS

    user_id = data[start:stop]
    logger.debug('crypto: useer id: ', user_id)

    start = stop
    stop += GX_SIZE

    p_enc_wbgx = data[start:stop]
    logger.debug('crypto: pEncWBGx: ', p_enc_wbgx)

    p_enc_gx = decrypt_parameter_data_with_aes(p_enc_wbgx)
    logger.debug('crypto: pEncGx: ', p_enc_gx)

    iv = b"\x00" * BLOCK_SIZE
    cipher = AES.new(aes_key, AES.MODE_CBC, iv)

    pgx = cipher.decrypt(p_enc_gx)
    logger.debug('crypto: pGx: ', pgx)

    bn_pgx = int(pgx, 16)
    bn_prime = int(keys.prime, 16)
    bn_private_key = int(keys.privateKey, 16)
    secret_hex = hex(pow(bn_pgx, bn_private_key, bn_prime))[2:].upper()

    secret = bytes(bytearray.fromhex(secret_hex.replace('L', '')))
    logger.debug('crypto: secret: ', secret)

    start = stop
    stop += SHA_DIGEST_LENGTH

    data_hash2 = data[start:stop]
    logger.debug('crypto: data hash 2: ', data_hash2)

    secret2 = user_id + secret
    logger.debug('crypto: secret 2: ', secret2)

    sha1 = hashlib.sha1()
    sha1.update(secret2)
    data_hash3 = sha1.digest()
    logger.debug('crypto: data hash 3: ', data_hash3)

    if data_hash2 != data_hash3:
        print("Pin error!!!")
        return False

    start = stop
    stop += 1
    if ord(data[start:stop]):
        print("First flag error!!!")
        return False

    start = stop
    stop += 4
    if struct.unpack(">I", data[start:stop])[0]:
        print("Second flag error!!!")
        return False

    sha1 = hashlib.sha1()
    sha1.update(dest)
    dest_hash = sha1.digest()
    logger.debug('crypto: dest hash: ', dest_hash)

    final_buffer = (
        user_id +
        g_user_id.encode('utf-8') +
        pgx +
        bytes(bytearray.fromhex(keys.publicKey)) +
        secret
    )
    sha1 = hashlib.sha1()
    sha1.update(final_buffer)

    sk_prime = sha1.digest()
    logger.debug('crypto: sk prime: ', sk_prime)

    sha1 = hashlib.sha1()
    sha1.update(sk_prime + b"\x00")

    sk_prime_hash = sha1.digest()
    logger.debug('crypto: sk prime hash: ', sk_prime_hash)

    ctx = apply_samygo_key_transform(sk_prime_hash[:16])
    logger.debug('crypto: ctx: ', ctx)

    return hex(int(ctx)), sk_prime


def generate_server_acknowledge(sk_prime):
    sha1 = hashlib.sha1()
    sha1.update(sk_prime + b"\x01")
    sk_prime_hash = sha1.digest()

    return (
        "0103000000000000000014" +
        sk_prime_hash.hex().upper() +
        "0000000000"
    )


def parse_client_acknowledge(client_ack, sk_prime):
    sha1 = hashlib.sha1()
    sha1.update(sk_prime + b"\x02")
    sk_prime_hash = sha1.digest()
    tmp_client_ack = (
        "0104000000000000000014" +
        sk_prime_hash.hex().upper() +
        "0000000000"
    )

    return client_ack == tmp_client_ack
