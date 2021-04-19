#!/usr/bin/python3

import discord
import secrets
import re
import requests

client = discord.Client()
TOKEN = secrets.token

url = "https://e621.net/posts.json"
headers = {
    "User-Agent": "DiscordFurryBot V0.1",
}

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    channel = message.channel

    message_content = message.clean_content.lower()

    if message_content.startswith("!~ "):

        params = {
            "limit": 1,
            "tags": message_content[3:]
        }

        if not channel.is_nsfw():
            params["tags"] += " rating:s"


        #  TODO: get url
        r = requests.get(url, params=params, headers=headers)

        print(r.url)

        response = r.json()

        # get response
        image_url = response["posts"][0]["file"]["url"]

        await channel.send(image_url)


client.run(TOKEN)
