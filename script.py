#!/usr/bin/python3

import discord
import secrets
import blocklist
import requests
import re

# TODO:
# see more than most recent image
# add way to look at image data (post artist?)
# tag search
# better description display

client = discord.Client()


url = "https://e621.net/posts.json"
headers = {
    # If you are running this yourself I would change the User_Agent to include your main e621 username
    "User-Agent": "DiscordFurryBot V1.2",
}

url_regex = re.compile(
    r"(https?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+)")

status = "!~ tags"

# returns true if any tag is on the denylist


def check_tags(tags):
    for tag in tags:
        if tag in blocklist.tags:
            return True
    return False


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))
    await client.change_presence(activity=discord.Game(status))


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    channel = message.channel

    message_content = message.clean_content.lower()

    if message_content.startswith("!~ "):

        params = {
            "limit": 32,
            "tags": message_content[3:]
        }

        if not channel.is_nsfw():
            params["tags"] += " rating:s status:active tagcount:>15"
            for tag in blocklist.nsfw_only:
                params["tags"] += " -" + tag

        r = requests.get(url, params=params, headers=headers,
                         auth=(secrets.login, secrets.api_key))

        if r.status_code != 200:
            await channel.send("Error: recieved status code: " + str(r.status_code))
            return

        response = r.json()

        posts = response["posts"]

        for post in posts:

            if check_tags(post["tags"]["general"]):
                continue

            if post["score"]["total"] < 0:
                continue

            image_url = post["file"]["url"]
            image_description = post["description"]

            if image_description and image_description != "" and len(image_description) < 500 and not url_regex.match(image_description):
                await channel.send(image_description)
            await channel.send(image_url)
            return

        await channel.send("no images found")
        return


client.run(secrets.token)
