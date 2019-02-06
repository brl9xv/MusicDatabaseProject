from __future__ import unicode_literals
import concurrent.futures
import psycopg2
import asyncio
import discord
from discord.ext import commands
import youtube_dl
import vlc
from database_info import *

class music:
    def __init__(self, bot):
        # Save reference to passed bot instance
        self.bot = bot
        
        # Connect to database and create operation cursor
        self.con = psycopg2.connect(database=DATABASE,user=USER,password=PASSWORD,host=HOST,port=PORT)
        self.cur=self.con.cursor()

        # Set up audio task loop
        self.bot.loop.create_task(self.audio_loop())
        self.player = vlc.Instance().media_player_new()
        self.player.event_manager().event_attach(vlc.EventType.MediaPlayerEndReached,self.song_finished)
        self.queue = asyncio.Queue()
        self.queue_list = []
        self.next = False
        self.playing = False

        # Save youtube-dl options
        self.opts={
                'format':'bestaudio',
                'outtmpl':'',
                'postprocessors':[{'key':'FFmpegExtractAudio','preferredcodec':'m4a'}],
                }

    def song_finished(self, event):
        if event.type == vlc.EventType.MediaPlayerEndReached:
            self.next = True

    async def download(self, key):
        try:
            self.opts['outtmpl'] = ('../Music/'+key+'.m4a')
            with youtube_dl.YoutubeDL(self.opts) as ydl:
                ydl.download(['https://www.youtube.com/?v='+key])
        except(...):
            print('Download error caught...')
            print(e)

    async def audio_loop(self):
        while True:
            self.next = False
            media_path = await self.queue.get()
            if not os.path.isfile(media_path):
                print('Media does not exist')
            else:
                self.player.set_media(vlc.Instance().media_new_path(media_path))
                self.player.play()
                self.playing = True
                while not self.next:
                    await asyncio.sleep(1)
                self.player.stop()
                self.playing = False

    async def searchdb(self, content):
        cut = content.find(' ')
        param = content[:cut]
        term = content[cut+1:]
        if not (param == "title" or param == "artist" or param == "genre"):
            param = "title"
            term = content
        self.cur.execute("select title, artist, genre, link from music where {0} like '%{1}%';".format(param,term))
        return self.cur.fetchall()

    @commands.command(pass_context=True, no_pm=True)
    async def play(self, ctx):
        try:
            results = await self.searchdb(ctx.message.content[9:])
            if len(results) < 1:
                await self.bot.send_message(ctx.message.channel,'No results...')
            elif len(results) == 1:
                await self.bot.send_message(ctx.message.channel,'Enqueing: '+results[0][0]+" - "+results[0][1])
                await self.queue.put("../Music/"+results[0][3]+".m4a")
            else:
                await self.bot.send_message(ctx.message.channel,'Multiple results, pick a number or all...')
                all_results = ''
                for i in range(len(results)):
                    all_results += str(i+1)+': '+results[i][0]+' - '+results[i][1]+'\n'
                await self.bot.send_message(ctx.message.channel, all_results)
                choice_m = await self.bot.wait_for_message(author=ctx.message.author)
                choice = choice_m.content
                if choice == 'all':
                    await self.bot.send_message(ctx.message.channel,'Enqueing: all results')
                    for r in results:
                        await self.queue.put("../Music/"+r[3]+".m4a")
                else:
                    await self.bot.send_message(ctx.message.channel,'Enqueing: '+results[int(choice)-1][0])
                    await self.queue.put("../Music/"+results[int(choice)-1][3]+".m4a")

        except psycopg2.Error as e:
            await self.bot.send_message(ctx.message.channel,'Error...')
            print(e)

    @commands.command(pass_context=True, no_pm=True)
    async def skip(self, ctx):
        if self.playing:
            await self.bot.send_message(ctx.message.channel,'Skipping...')
            self.next = True
        else:
            await self.bot.send_message(ctx.message.channel,'Nothing is playing...')

    
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
