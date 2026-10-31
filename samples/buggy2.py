import subprocess

def run_command(user_input):
    subprocess.call("ls " + user_input, shell=True)

def get_item(items, index):
    return items[index + 1]

def average(numbers):
    return sum(numbers) / len(numbers)

def read_file(path):
    f = open(path)
    return f.read()
