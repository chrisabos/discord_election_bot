import json

data = None

def save():
    with open("/home/pi/discord_election_bot/election_data.json", "w") as file:
        json.dump(data, file, indent = 4)
        file.close()
    return True

def load():
    with open("/home/pi/discord_election_bot/election_data.json", "r") as file:
        global data
        data = json.load(file)
        file.close()
    if data:
        return True
    return False

def get():
    return data
