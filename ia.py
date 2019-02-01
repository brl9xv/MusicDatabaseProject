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
        self.bot = bot
        self.con = psycopg2.connect(database='musicdatabase',user='gigacorn',password='bplieb123',host='localhost',port='5432')
        self.cur=self.con.cursor()
        self.opts={
                'format':'bestaudio',
                'outtmpl':'',
                'postprocessors':[{'key':'FFmpegExtractAudio','preferredcodec':'m4a'}],
                }

    async def download(self, key):
        try:
            self.opts['outtmpl'] = ('../Music/'+key+'.m4a')
            with youtube_dl.YoutubeDL(self.opts) as ydl:
                ydl.download(['https://www.youtube.com/?v='+key])
        except(...):
            print('Download error caught...')
            print(e)

    
    @commands.command(pass_context=True, no_pm=True)
    async def add(self, ctx):

        # Get title
        await self.bot.send_message(ctx.message.channel, 'What is the song called?')
        title_m = await self.bot.wait_for_message(author=ctx.message.author)
        title = title_m.content

        # Get artist
        await self.bot.send_message(ctx.message.channel, 'Who is the artist?')
        artist_m = await self.bot.wait_for_message(author=ctx.message.author)
        artist = artist_m.content

        # Get genre
        await self.bot.send_message(ctx.message.channel, 'What is song\'s genre?')
        genre_m = await self.bot.wait_for_message(author=ctx.message.author)
        genre = genre_m.content

        # Get link
        await self.bot.send_message(ctx.message.channel, 'What is the link to the song?')
        link_m = await self.bot.wait_for_message(author=ctx.message.author)

        # Cut link to get unique key
        cut = link_m.content.find('=')+1
        key = link_m.content[cut:]

        # Attempt download
        await self.bot.send_message(ctx.message.channel, 'Downloading...')
        await self.download(key)

        # Attempt database modifications
        await self.bot.send_message(ctx.message.channel, 'Adding "{0}" to database'.format(title))
        try:
            query = "INSERT INTO music(title, artist, genre, key) VALUES ('{0}', '{1}', '{2}', '{3}');"
            self.cur.execute(query.format(title, artist, genre, key))
            self.con.commit()
            await self.bot.send_message(ctx.message.channel, 'Database modified successfully!')

        except psycopg2.Error as e:
            print('Caught insert error...')
            con.rollback()
            print(e)




client=commands.Bot(command_prefix=commands.when_mentioned_or("ia "))
client.add_cog(music(client))

@client.event
async def on_ready():
    print('Ready!')
    print('User: '+str(client.user.name))
    print('ID: '+str(client.user.id))

@client.event
async def on_message(message):
    if message.author != client.user:
        await client.send_message(message.channel, 'really rocks')


client.run("NTQwMzM2ODcyNjczNTA5Mzc2.DzPdnQ.qRzQA3LGUTEdPsLotEj9dMLGxJY")
