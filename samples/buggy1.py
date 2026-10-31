import os
import pickle

def get_user(name):
    query = "SELECT * FROM users WHERE name = '" + name + "'"
    return query

def load(data):
    return pickle.loads(data)

password = "admin123"
x = 10 / 0