"""Separate implementation of authentication right now"""

from werkzeug.security import generate_password_hash, check_password_hash


def hash_password(salt, plaintext):
    # 'salt' the passwords to prevent brute forcing
    return generate_password_hash(salt + str(plaintext))


def is_correct_password(hashed_password, salt, plaintext):
    return check_password_hash(hashed_password, salt + str(plaintext))
