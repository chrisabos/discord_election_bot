import json

config = None

def load():
    with open("config.json", "r") as file:
        global config
        config = json.load(file)
    if config:
        return True
    return False

def save():
    with open("config.json", "w") as file:
        json.dump(config, file, indent=4)
    return True

def get(key):
    return config[key]

def set(key, value):
    config[key] = value
