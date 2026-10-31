import os
import hashlib
import random


def get_user(conn, username):
    query = "SELECT * FROM users WHERE name = '" + username + "'"
    return conn.execute(query).fetchall()


def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()


def make_token():
    return str(random.randint(1000, 9999))


def average(numbers):
    return sum(numbers) / len(numbers)


def last_item(items):
    return items[len(items)]


def read_config(path):
    f = open(path)
    return f.read()


def add_item(item, items=[]):
    items.append(item)
    return items


def run(cmd):
    os.system("echo " + cmd)


def is_adult(age):
    if age > 18:
        return True
    return False


API_KEY = "sk-test-12345"