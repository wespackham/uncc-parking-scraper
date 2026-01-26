import requests
import json

url = "https://parkingavailability.charlotte.edu/decks/stream"

with requests.get(url, stream=True) as r:
    r.raise_for_status()

    for line in r.iter_lines(decode_unicode=True):
        if line.startswith("data:"):
            json_data = line.removeprefix("data:")
            parking_data = json.loads(json_data)
            #print(data)
            for lot in parking_data:
                print(lot)
            break
