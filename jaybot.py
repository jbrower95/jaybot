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


def loadFromFile(fp):
    with open(fp, "r") as f:
        lines = list(filter(lambda line: line and line[0] != '#', f.readlines()))
    return lines



class JayClient(discord.Client):

    OWNER = 'your.guy.jay'
    CHANNEL = 'jaybot-commands'

    def __init__(self):
        super().__init__()
        self.connection = None
        self.silenced = False
        self.guild = None
        self.ranked = False
        self.channel = None
        self.load_data()

    def sleep_nonblock(self, timeout_seconds):
        target_time = time.time() + timeout_seconds
        while time.time() < target_time:
            time.sleep(.01)

    def running(self):
        return self.connection is not None and self.channel is not None and self.guild is not None

    async def play_mp3(self, path) -> None:
        source = await discord.FFmpegOpusAudio.from_probe(path)
        self.connection.play(source)
        print(f"Played {path}")
        # Client play is non-blocking. And the `after` callback doesn't allow
        # async functions. For now, the best we can do is loop + block the event
        # thread temporarily while waiting for this to finish.
        while self.connection.is_playing():
            time.sleep(.01)
        print(f"Finished playing {path}!")

    async def speak_sync(self, sentence) -> None :
        if self.silenced or not self.connection:
            print("INFO: Failed to speak (silenced, or no connection.)")
            return
        sentence = sentence.strip()
        self.sleep_nonblock(.5)
        name = path.join('cached', hashlib.md5(sentence.encode()).hexdigest()[:12] + '.mp3')
        print(f"INFO: Saying {sentence}!")
        if not path.exists(name):
            print("INFO: Going to network...")
            tts = gTTS(sentence)
            tts.save(name)
            print("INFO: Saved.")
        await self.play_mp3(name)

    async def on_message(self, message):
        print(message.channel.name)
        if message.channel.name == JayClient.CHANNEL:
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
            if message.content == '/kill':
                await self.kill_all()
                self.load_data()

    async def kill_all(self):
        if self.connection:
            await self.connection.disconnect()
        self.guild = None
        self.ranked = False
        self.silenced = False
        self.channel = False

    def load_data(self):
        self.greetings = loadFromFile(path.join('data', 'bot-greetings.txt'))
        self.departures = loadFromFile(path.join('data', 'departures.txt'))
        self.ranked_messages = loadFromFile(path.join('data', 'ranked.txt'))
        self.welcomes = loadFromFile(path.join('data', 'greetings.txt'))

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
        self.sleep_nonblock(2)
        await self.speak_sync(random.choice(self.greetings))


    async def on_ready(self):
        print('Logged on as {0}!'.format(self.user))
        await self.attach_to_user(JayClient.OWNER)
        if not self.connection:
            print("WARN: Tried to start JayBot without your.guy.jay in a voice chat.")

    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return
        if not self.running():
            return
        name = member.nick or member.name
        if after.channel is None and before.channel.id == self.channel.id:
            await self.speak_sync(random.choice(self.departures).format(name))
        elif after.channel is not None and after.channel.id == self.channel.id and not (before.deaf or before.mute or before.self_mute or before.self_deaf or before.self_stream or before.self_video or after.deaf or after.mute or after.self_mute or after.self_deaf or after.self_stream or after.self_video) :
            if self.ranked:
                await self.speak_sync(random.choice(self.ranked_messages).format(name))
            else:
                await self.speak_sync(random.choice(self.welcomes).format(name))


client = JayClient()
client.run(token)
