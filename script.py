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
# rate limiting

client = discord.Client()


url = "https://e621.net/posts.json"
headers = {
    # If you are running this yourself I would change the User_Agent to include your main e621 username
    "User-Agent": "DiscordFurryBot V1.2",
}

url_regex = re.compile(
    r"(https?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+)")


status = "!~ tags"


cache = []


# returns true if any tag is on the blocklist
def check_tags(tags):
    for tag in tags:
        if tag in blocklist.general_tags:
            return True
    return False


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))
    await client.change_presence(activity=discord.Game(status))


@client.event
async def on_message(user_message):
    if user_message.author == client.user:
        return

    channel = user_message.channel

    message_content = user_message.clean_content.lower()

    if message_content.startswith("!~ "):

        params = {
            "limit": 32,
            "tags": message_content[3:]
        }

        params["tags"] += " -huge_filesize -flash score:>=0"

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

        post_num = 1

        for post in posts:

            post_num += 1

            if check_tags(post["tags"]["general"]):
                continue

            if post["score"]["total"] < 0:
                continue

            image_url = post["file"]["url"]
            image_description = post["description"]

            if image_description and image_description != "" and len(image_description) < 500 and not url_regex.search(image_description):
                await channel.send(image_description)
            bot_message = await channel.send(image_url)
            await bot_message.add_reaction("⬅️")
            await bot_message.add_reaction("➡️")

            cache.append(
                {"id": bot_message.id, "channel": bot_message.channel.id, "post_num": post_num, "posts": posts})
            if len(cache) > 2:
                old_post = cache.pop(0)
                old_channel = client.get_channel(old_post["channel"])
                old_message = await old_channel.fetch_message(old_post["id"])
                await old_message.remove_reaction("⬅️", client.user)
                await old_message.remove_reaction("➡️", client.user)

            return

        await channel.send("no images found")
        return


@client.event
async def on_reaction_add(reaction, user):
    pass

client.run(secrets.token)
