from __future__ import unicode_literals
import concurrent.futures
import psycopg2
import asyncio
import discord
from discord.ext import commands
import youtube_dl
import vlc

class music:
    def __init__(self, bot):
        self.opts={
                'format':'bestaudio',
                'outtmpl':'',
                'postprocessors':[{'key':'FFmpegExtractAudio','preferredcodec':'m4a'}],
                }
        self.bot=bot
    
    @commands.command(pass_context=True, no_pm=True)
    async def add(self, ctx):
        try:
            cut = ctx.message.content.find('=')+1
            self.opts['outtmpl']='~/Music/'+ctx.message.content[cut:]+'.m4a'
            await self.bot.send_message(ctx.message.channel, 'downloading...')
            with youtube_dl.YoutubeDL(self.opts) as ydl:
                ydl.download([ctx.message.content[7:]])
        
        except(...):
            print (e)


            

client=commands.Bot(command_prefix=commands.when_mentioned_or("ia "))
client.add_cog(music(client))

client.run("NTQwMzM2ODcyNjczNTA5Mzc2.DzPdnQ.qRzQA3LGUTEdPsLotEj9dMLGxJY")
