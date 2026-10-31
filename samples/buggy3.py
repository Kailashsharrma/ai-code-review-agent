import hashlib
import random

def hash_password(pw):
    return hashlib.md5(pw.encode()).hexdigest()

def make_token():
    return str(random.randint(1000, 9999))

def find_user(users, name):
    for i in range(len(users)):
        if users[i]["name"] == name:
            return users[i]
        else:
            return None