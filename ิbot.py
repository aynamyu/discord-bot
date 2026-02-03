import os
import discord
import asyncio
import yt_dlp
from dotenv import load_dotenv
from discord.ext import commands

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'extract_flat': 'in_playlist',
    'nocheckcertificate': True,
    'default_search': 'ytsearch1',
    'source_address': '0.0.0.0'
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -filter:a "volume=0.8"', 
}

class MusicBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        super().__init__(command_prefix=".", intents=intents)
        
        self.queues = {} 
        self.is_playing = {}

    async def get_queue(self, guild_id):
        if guild_id not in self.queues:
            self.queues[guild_id] = asyncio.Queue()
            self.is_playing[guild_id] = False
        return self.queues[guild_id]

    async def play_next(self, ctx):
        guild_id = ctx.guild.id
        queue = await self.get_queue(guild_id)

        if queue.empty():
            self.is_playing[guild_id] = False
            return

        song = await queue.get()
        
        if not ctx.voice_client:
            return

        def after_playing(error):
            if error: print(f"Player error: {error}")
            self.loop.create_task(self.play_next(ctx))

        source = discord.FFmpegPCMAudio(song['url'], **FFMPEG_OPTIONS)
        ctx.voice_client.play(source, after=after_playing)
        self.is_playing[guild_id] = True
        await ctx.send(f"🎶 เล่นเพลง: **{song['title']}**")

bot = MusicBot()

@bot.event
async def on_ready():
    print(f'✅ Logged in as {bot.user} (ID: {bot.user.id})')

@bot.event
async def on_message(message):
    if message.author.bot: return
    if not message.content.startswith('.'): return 
    await bot.process_commands(message)

@bot.command(name="p")
async def play(ctx, *, query):
    if not ctx.voice_client:
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
        else:
            return await ctx.send("เข้าห้องเสียงก่อนเร็ว!")

    async with ctx.typing():
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            loop = asyncio.get_event_loop()
            try:
                info = await loop.run_in_executor(None, lambda: ydl.extract_info(query, download=False))
                if 'entries' in info:
                    info = info['entries'][0]
            except Exception as e:
                return await ctx.send(f"❌ หาเพลงไม่เจอคับ: {e}")

        data = {
            'url': info['url'],
            'title': info['title']
        }

        queue = await bot.get_queue(ctx.guild.id)
        await queue.put(data)

    if not bot.is_playing[ctx.guild.id]:
        await bot.play_next(ctx)
    else:
        await ctx.send(f"✅ เพิ่มเข้าคิว: **{data['title']}**")
