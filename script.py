#!/usr/bin/python3

import secrets
import re
import requests
import discord
import blocklist

# TODO:
# graceful exit
# add way to look at image data (post artist?)
# tag search
# better description display
# rate limiting

CLIENT = discord.Client()


URL = "https://e621.net/posts.json"
HEADERS = {
    # If you are running this yourself
    # I would change the User_Agent to include your main e621 username
    "User-Agent": "DiscordFurryBot V1.2",
}

URL_REGEX = re.compile(
    r"(https?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+)")


STATUS = "!~ tags"


cache = []


# returns true if any tag is on the blocklist
def check_post(post):
    tags = post["tags"]["general"]
    for tag in tags:
        if tag in blocklist.general_tags:
            return True
    if post["score"]["total"] < 0:
        return True
    return False


def clamp(num, min_num, max_num):
    return max(min(num, max_num), min_num)


@CLIENT.event
async def on_ready():
    print(f"We have logged in as {CLIENT.user}")
    await CLIENT.change_presence(activity=discord.Game(STATUS))


@CLIENT.event
async def on_message(user_message):
    if user_message.author == CLIENT.user:
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

        response = requests.get(URL, params=params, headers=HEADERS,
                                auth=(secrets.login, secrets.api_key))

        if response.status_code != 200:
            await channel.send("Error: recieved status code: " + str(response.status_code))
            return

        response_json = response.json()

        posts = response_json["posts"]

        filtered = []
        for post in posts:
            if not check_post(post):
                filtered.append(post)
        posts = filtered

        if len(posts) == 0:
            await channel.send("no images found")
            return

        post = posts[0]
        image_url = post["file"]["url"]

        bot_message = await channel.send(image_url)
        await bot_message.add_reaction("⬅️")
        await bot_message.add_reaction("➡️")

        cache.append(
            {"message": bot_message, "pos": 0, "posts": posts})
        if len(cache) > 10:
            old_post = cache.pop(0)
            old_message = old_post["message"]
            await old_message.remove_reaction("⬅️", CLIENT.user)
            await old_message.remove_reaction("➡️", CLIENT.user)

        return


@CLIENT.event
async def on_reaction_add(reaction, user):
    message = reaction.message
    if user == CLIENT.user:
        return
    if message.author == CLIENT.user and message in map(lambda a: a["message"], cache):
        emoji = reaction.emoji
        if emoji not in ("⬅️", "➡️"):
            return
        await message.remove_reaction(reaction.emoji, user)
        # change image
        message_num = 0
        for info in cache:
            if message == info["message"]:
                break
            message_num += 1
        posts = cache[message_num]["posts"]
        pos = cache[message_num]["pos"]
        if emoji == "⬅️":
            pos -= 1
        else:
            pos += 1
        pos = clamp(pos, 0, len(posts) - 1)

        cache[message_num]["pos"] = pos

        image_url = posts[pos]["file"]["url"]

        await message.edit(content=image_url)


async def cleanup():
    for info in cache:
        message = info["message"]
        await message.remove_reaction("⬅️", CLIENT.user)
        await message.remove_reaction("➡️", CLIENT.user)


CLIENT.run(secrets.token)
