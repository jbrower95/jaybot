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
import speech_recognition as sr

# set this to the token for the bot.
token = os.environ['JAY_BOT']
r = sr.Recognizer()

def loadFromFile(fp):
    with open(fp, "r") as f:
        lines = list(filter(lambda line: line and line[0] != '#', f.readlines()))
    return lines


class JayClient(discord.Client):

    OWNER = 'your.guy.jay'
    CHANNEL = 'jaybot-commands'

    HELP = '''
    Welcome to JayBot! (tm)

    JayBot introduces people when they join or leave a channel.

    Available commands:

    /silence - Shutup Jay. To unsilence, type it again.
    /ranked - Enable ranked mode. It tells people to shut up while enabled.
    /summon - If you're in a voice chat, brings Jay Bot to your chat.
    /insult <person> - Tag someone to insult them!
    /kill - Remove JayBot from the current voice chat.
    /help - Print this menu.
    '''

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
            full_cmd = message.content.split()
            if not full_cmd: return
            cmd = full_cmd[0]
            if cmd == "/roll":
                parts = message.content.split(" ")
                result = random.randint(1, 101)
                await message.channel.send(f'Rolled {result}!')
            if cmd == '/silence':
                self.silenced = not self.silenced
                await message.channel.send(f'{"Silenced!" if self.silenced else "Not silenced!"} To toggle, type /silence')
            if cmd == '/ranked':
                self.ranked = not self.ranked
                await message.channel.send(f'Ranked mode: {"enabled" if self.ranked else "disabled"}')
            if cmd == '/summon':
                author = message.author.name
                await self.attach_to_user(author)
            if cmd == '/kill':
                await self.kill_all()
                self.load_data()
            if cmd == '/insult':
                if not self.guild:
                    return
                args = full_cmd[1:]
                if not args:
                    await message.channel.send(f'Error: Tag someone to insult them!')
                person = full_cmd[1]
                person_id = int(person[3:-1])
                target_member = None
                # look up this person.
                for member in self.guild.members:
                    if member.id == person_id:
                        # Found the member.
                        target_member = member
                        break
                if not target_member:
                    await message.channel.send(f'Error: Couldnt find that user!')
                await self.speak_sync(random.choice(self.insults).format(member.name))


            if message.content == '/help':
                await message.channel.send(JayClient.HELP)

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
        self.insults = loadFromFile(path.join('data', 'insults.txt'))

    async def attach_to_user(self, name):
        if self.connection:
            await self.connection.disconnect()
        self.connection = None
        self.guild = None
        self.channel = None
        self.silenced = True
        for guild in self.guilds:
            print(f"Found guild: {guild.name}")
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
