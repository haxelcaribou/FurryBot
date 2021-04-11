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

    if "e621" in message_content:
        await channel.send("Lewd")


client.run(TOKEN)
