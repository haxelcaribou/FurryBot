#!/usr/bin/python3

import discord
import secrets

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


client.run(TOKEN)
