#!/usr/bin/python3

import requests

url = "https://e621.net/posts.json"
headers = {
    "User-Agent": "DiscordFurryBot V0.1",
}

params = {
    "limit": 1,
    "tags": "fluffy rating:s"
}

#  TODO: get url
r = requests.get(url, params=params, headers=headers)

print(r.url)
print(r.status_code)

response = r.json()

print(response)

# get response
image_url = response["posts"][0]["file"]["url"]

print(image_url)
