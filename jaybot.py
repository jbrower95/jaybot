#!/usr/bin/python3

import discord
import tempfile
import time
import random
import os
from os import path
import hashlib
import asyncio
from tempfile import NamedTemporaryFile
from gtts import gTTS
import multiprocessing as mp

# set this to the token for the bot.
token = os.environ['JAY_BOT']

greetings = [
    "Hey guys. It's ya boy Jay bot.",
    "What's up nerds, It's Jay bot.",
    "Sup losers, It's Jay bot.",
    "Get wrecked, idiots. It's jay bot",
    "Who's ready for ranked. It's jay bot.",
    "Silence me with /silence in chat. It's jay bot!"
]

departures = [
    "Nobody liked {} anyways. See ya!",
    "Looks like {} left!",
    "Now that {} is gone, let's talk shit.",
    "{} is gone. Rip.",
    "Can you believe it? {} rage quit.",
    "Bye {}!"
]

ranked_messages = [
    "Shut up, {}, we're playing ranked.",
    "Not right now, {}, we're playing ranked.",
    "Please leave, {}, we're playing ranked.",
    "We're playing ranked, {}. Please be respectful.",
]

welcomes = [
    "{} has joined!",
    "Everybody say hi to {}!",
    "Is that a cheap hooker, or just {}?",
    "Howdy, {}!",
    "Welcome back, {}!",
    "I didn't order strippers, that's just {}!"
]

class JayClient(discord.Client):

    OWNER = 'your.guy.jay'

    def __init__(self):
        super().__init__()
        self.connection = None
        self.silenced = False
        self.guild = None
        self.ranked = False
        self.channel = None

    def sleep_nonblock(self, timeout_seconds):
        target_time = time.time() + timeout_seconds
        while time.time() < target_time:
            time.sleep(.01)

    def running(self):
        return self.connection is not None and self.channel is not None and self.guild is not None

    async def speak_sync(self, sentence) -> None :
        if self.silenced or not self.connection:
            return
        self.sleep_nonblock(.5)
        name = hashlib.md5(sentence.encode()).hexdigest()[:12] + '.mp3'
        if not path.exists(name):
            tts = gTTS(sentence)
            tts.save(name)
        source = await discord.FFmpegOpusAudio.from_probe(name)
        self.connection.play(source)

        # Client play is non-blocking. And the `after` callback doesn't allow
        # async functions. For now, the best we can do is loop + block the event
        # thread temporarily while waiting for this to finish.
        while self.connection.is_playing():
            time.sleep(.01)

    async def on_message(self, message):
        if message.content is not None and "/roll" in message.content:
            parts = message.content.split(" ")
            result = random.randint(1, 101)
            await message.channel.send(f'Rolled {result}!')
        if message.content == '/silence':
            self.silenced = True
            await message.channel.send(f'Silenced! To re-enable, type /enable')
        if message.content == '/enable':
            self.silenced = False
            await message.channel.send(f'Enabled! To disable, type /silence')
        if message.content == '/ranked':
            self.ranked = not self.ranked
            await message.channel.send(f'Ranked mode enabled: {self.ranked}')
        if message.content == '/summon':
            author = message.author.name
            await self.attach_to_user(author)


    async def attach_to_user(self, name):
        if self.connection:
            await self.connection.disconnect()
        self.connection = None
        self.guild = None
        self.channel = None
        self.silenced = True
        for guild in self.guilds:
            channels = guild.voice_channels
            for channel in channels:
                members = channel.members
                for member in members:
                    if member.name == name:
                        self.channel = channel
                        self.guild = guild
                        self.connection = await channel.connect()
                        break
                if self.channel:
                    break
            if self.guild:
                break
        self.silenced = False

    async def on_ready(self):
        print('Logged on as {0}!'.format(self.user))
        await self.attach_to_user(JayClient.OWNER)
        if not self.connection:
            print("WARN: Tried to start JayBot without your.guy.jay in a voice chat.")
        else:
            await self.speak_sync(random.choice(greetings))

    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return
        if not self.running():
            return
        name = member.nick or member.name
        if after.channel is None and before.channel.id == self.channel.id:
            await self.speak_sync(random.choice(departures).format(name))
        elif after.channel is not None and after.channel.id == self.channel.id and not (before.deaf or before.mute or before.self_mute or before.self_deaf or before.self_stream or before.self_video or after.deaf or after.mute or after.self_mute or after.self_deaf or after.self_stream or after.self_video) :
            if self.ranked:
                await self.speak_sync(random.choice(ranked_messages).format(name))
            else:
                await self.speak_sync(random.choice(welcomes).format(name))


client = JayClient()
client.run(token)
