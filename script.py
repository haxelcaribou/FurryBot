#!/usr/bin/python3

import discord
import secrets
import re

client = discord.Client()
TOKEN = secrets.token


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    channel = message.channel

    message_content = message.clean_content.lower()

    if "lewd" in message_content:
        if channel.is_nsfw():
            await channel.send("Actaully I don't do anything. Nice try tho.")
        else:
            await channel.send("Oi! Not in front of the children.")


client.run(TOKEN)
