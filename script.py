#!/usr/bin/python

import secrets
import asyncio
import signal
import sys
import logging
from datetime import datetime
import requests
import discord
import blocklist

# TODO:
# tag search
# rate limiting
# ephemeral errors
# all move posst buttons disabled when only one post
# - Move to specific set buttons method


intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.reactions = True

CLIENT = discord.Client(intents=intents)

# enable logging
logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(
    filename="discord.log", encoding="utf-8", mode="w")
formatter = logging.Formatter(
    '[{asctime}] [{levelname:<8}] {name}: {message}', "%Y-%m-%d %H:%M:%S", style='{')
handler.setFormatter(formatter)
logger.addHandler(handler)


MAX_IMAGES = 32

STATUS = "!~ tags"

BASE_URL = "https://e621.net/"
HEADERS = {
    # If you are running this yourself change the User_Agent to include your main e621 username
    "User-Agent": "DiscordFurryBot V1.2",
}

MAX_CACHE_SIZE = 32
cache = []


class HTTP404Exception(Exception):
    pass


class ButtonRow(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    active_style = discord.ButtonStyle.blurple
    inactive_style = discord.ButtonStyle.grey

    @discord.ui.button(style=inactive_style,
                       label="First",
                       emoji="⬅️",
                       custom_id="first_button")
    async def first_image(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await change_image(interaction.message, to_left=True, to_end=True)

    @discord.ui.button(style=inactive_style,
                       label="Prev",
                       emoji="◀️",
                       custom_id="prev_button")
    async def prev_image(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await change_image(interaction.message, to_left=True)

    @discord.ui.button(style=active_style,
                       label="Next",
                       emoji="▶️",
                       custom_id="next_button")
    async def next_image(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await change_image(interaction.message)

    @discord.ui.button(style=active_style,
                       label="Last",
                       emoji="➡️",
                       custom_id="last_button")
    async def last_image(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await change_image(interaction.message, to_end=True)

    @discord.ui.button(style=discord.ButtonStyle.red,
                       label="Delete",
                       custom_id="delete_message")
    async def delete_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()
        await interaction.response.send_message("Message deleted", ephemeral=True)


def cache_index(message):
    i = 0
    while i < len(cache):
        if message == cache[i]["message"]:
            return i
        i += 1
    return -1


# returns false if any tag is on the blocklist
def check_post(post):
    tags = post["tags"]["general"]
    for tag in tags:
        if tag in blocklist.general_tags:
            return False
    if post["score"]["total"] < 0:
        return False
    return True


def get_posts(tags="", is_nsfw=False):
    params = {
        "limit": MAX_IMAGES,
        "tags": tags
    }

    params["tags"] += " -huge_filesize -flash score:>=0"

    if not is_nsfw:
        params["tags"] += " rating:s status:active tagcount:>15"
        for tag in blocklist.nsfw_only:
            params["tags"] += " -" + tag

    response = requests.get(f"{BASE_URL}posts.json", params=params, headers=HEADERS,
                            auth=(secrets.login, secrets.api_key), timeout=5)

    if response.status_code != 200:
        raise HTTP404Exception(str(response.status_code))

    response_json = response.json()

    posts = response_json["posts"]

    return posts


async def disable_buttons(post):
    message = post["message"]
    view = post["view"]
    for button in view.children:
        button.disabled = True
    await message.edit(view=view)


@CLIENT.event
async def on_ready():
    print(f"We have logged in as {CLIENT.user}")
    await CLIENT.change_presence(activity=discord.Game(STATUS))


@CLIENT.event
async def on_message_delete(message):
    if message.author != CLIENT.user:
        return
    cache_pos = cache_index(message)
    if cache_pos == -1:
        return
    cache.pop(cache_pos)


@CLIENT.event
async def on_message(user_message):
    author = user_message.author
    if author == CLIENT.user:
        return

    channel = user_message.channel

    message_content = user_message.clean_content.lower()

    if message_content.startswith("!~ "):

        tags = message_content[3:]

        is_nsfw = channel.is_nsfw()

        try:
            posts = get_posts(tags, is_nsfw)
        except HTTP404Exception as status_code:
            await channel.send(f"Error: Recieved status code: {status_code}")
            return
        except requests.exceptions.ConnectTimeout:
            await channel.send("Error: Request timed out")

        filtered = []
        for post in posts:
            if check_post(post):
                filtered.append(post)
        posts = filtered

        if len(posts) == 0:
            await channel.send("No images found")
            return

        post = posts[0]

        embed = discord.Embed(title=tags, url=f"{BASE_URL}posts/{post['id']}")
        embed = set_embed_params(embed, post)
        embed.set_author(name=author, icon_url=author.avatar.url)
        embed.set_footer(text=f"Post 1 of {len(posts)}")

        view = set_buttons_enable(ButtonRow(), 0, len(posts) - 1)
        bot_message = await channel.send(embed=embed, view=view)

        cache.append({"message": bot_message, "pos": 0,
                     "posts": posts, "embed": embed, "view": view})
        if len(cache) > MAX_CACHE_SIZE:
            old_post = cache.pop(0)
            await disable_buttons(old_post)

        return


async def change_image(message, to_left=False, to_end=False):
    cache_pos = cache_index(message)
    if cache_pos == -1:
        return
    item = cache[cache_pos]
    posts = item["posts"]
    pos = item["pos"]
    view = item["view"]
    embed = item["embed"]

    if to_end:
        pos = 0 if to_left else len(posts) - 1
    else:
        pos = max(0, pos - 1) if to_left else min(pos + 1, len(posts) - 1)

    cache[cache_pos]["pos"] = pos

    view = set_buttons_enable(view, pos, len(posts) - 1)

    post = posts[pos]

    embed = set_embed_params(embed, post)
    embed.set_footer(text=f"Post {pos+1} of {len(posts)}")

    await message.edit(embed=embed, view=view)


def set_buttons_enable(view, pos, num_posts):
    for button in view.children:
        button.disabled = False

    if pos == 0:
        for button in view.children:
            button.disabled = button.custom_id in ("first_button",
                                                   "prev_button")
    elif pos == num_posts:
        for button in view.children:
            button.disabled = button.custom_id in ("next_button",
                                                   "last_button")

    return view


def set_embed_params(embed, post):
    embed.set_image(url=post["file"]["url"])
    embed.url = f"{BASE_URL}posts/{post['id']}"
    embed.timestamp = datetime.now()

    embed.clear_fields()
    embed.add_field(name="Uploaded",
                    value=datetime
                    .strptime(post["created_at"][:19], "%Y-%m-%dT%H:%M:%S")
                    .strftime("%B %-d %Y"))

    artists = [t.removesuffix("_(artist)") for t in post["tags"]["artist"]
               if t not in ("avoid_posting",
                            "conditional_dnp",
                            "epilepsy_warning",
                            "sound_warning",
                            "unknown_artist_signature")]
    if len(artists) == 1:
        embed.add_field(name="Artist", value=artists[0])
    elif len(artists) > 1:
        embed.add_field(name="Artists", value=", ".join(artists))

    embed.add_field(name="Score", value=post["score"]["total"])
    # embed.add_field(name="Size", value=f"{post['file']['width']}x{post['file']['height']}")

    if post["rating"] == "s":
        embed.color = discord.Color.dark_green()
    elif post["rating"] == "q":
        embed.color = discord.Color.gold()
    else:
        embed.color = discord.Color.red()

    # embed.description = post["description"]
    return embed


async def cleanup():
    print("\nCleaning up")
    for item in cache:
        await disable_buttons(item)


def terminate_process(signum, frame):
    sys.exit()


signal.signal(signal.SIGTERM, terminate_process)


loop = asyncio.get_event_loop()

try:
    loop.run_until_complete(CLIENT.start(secrets.token))
except (KeyboardInterrupt, SystemExit):
    loop.run_until_complete(cleanup())
    loop.run_until_complete(CLIENT.close())
    # cancel all tasks lingering
finally:
    loop.close()
    print("Exiting")
