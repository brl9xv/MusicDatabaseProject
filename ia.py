#***********************************************************************************#
#                                   Modules/Imports                                 #
#***********************************************************************************#

# Async Imports
from __future__ import unicode_literals
import concurrent.futures
import asyncio

# Database Imports
import psycopg2
from constant_info import *

# Discord API
import discord
from discord.ext import commands

# Media Player and Downloader
from audioread import audio_open as aread
from google_images_download import google_images_download as gid
import os.path
import random
import vlc
import youtube_dl

#***********************************************************************************#
#                                   Main Class/Cog                                  #
#***********************************************************************************#

class Music(commands.Cog):

    def __init__(self, bot):
        # Save reference to passed bot instance
        self.bot = bot
        
        # Connect to database and create operation cursor
        self.con = psycopg2.connect(database=DATABASE,user=USER,password=PASSWORD,host=HOST,port=PORT)
        self.cur=self.con.cursor()

        # Set up audio task loop
        self.bot.loop.create_task(self.audio_loop())
        self.channel = None
        self.player = vlc.Instance().media_player_new()
        self.player.event_manager().event_attach(vlc.EventType.MediaPlayerEndReached,self.song_finished)
        self.queue_paths = asyncio.Queue()
        self.queue_titles = []
        self.next = False
        self.paused = False
        self.playing = False

        # Save youtube-dl options
        self.opts={
                'format':'bestaudio',
                'outtmpl':'',
                'postprocessors':[{'key':'FFmpegExtractAudio','preferredcodec':'m4a'}],
                }

    async def audio_loop(self):
        while True:
            self.next = False
            media_path = await self.queue_paths.get()
            if not os.path.isfile(media_path):
                print('Media does not exist... Redownloading')
                print(media_path[6:-4])
                await self.download(media_path[6:-4])
            else:
                self.player.set_media(vlc.Instance().media_new_path(media_path))
                self.player.play()
                self.playing = True

                # Now playing message
                title = self.queue_titles[0][0]
                artist = self.queue_titles[0][1]
                await self.channel.send('Now Playing: {0} - {1}'.format(title,artist))
                self.queue_titles = self.queue_titles[1:]
                while not self.next:
                    await asyncio.sleep(1)
                self.player.stop()
                self.playing = False

    def song_finished(self, event):
        if event.type == vlc.EventType.MediaPlayerEndReached:
            self.next = True

#***********************************************************************************#
#                                   Non-Commands                                    #
#***********************************************************************************#

    # Downloads key.m4a from Youtube to Music/
    async def download(self, key):
        try:
            self.opts['outtmpl'] = ('Music/'+key+'.m4a')
            with youtube_dl.YoutubeDL(self.opts) as ydl:
                ydl.download(['https://www.youtube.com/?v='+key])
        except(...):
            await self.channel.send('Download error...')
            print(e)

    # Requests for information
    async def request_info(self, ctx, content):
        await ctx.message.channel.send(content)
        request_m = await self.bot.wait_for('message', check=lambda m: m.author==ctx.message.author)
        return (request_m.content).lower()

    # Helper function to convert strings to lists (splits at spaces)
    async def string_split(self, s):
        result = []
        cut = s.find(' ')
        while cut != -1:
            result.append(s[:cut])
            s = s[cut+1:]
            cut = s.find(' ')
        result.append(s)
        return result

#***********************************************************************************#
#                               Database Control Commands                           #
#***********************************************************************************#
    
    @commands.command(pass_context=True, no_pm=True)
    async def add(self, ctx):

        request = await self.string_split(ctx.message.content)

        # Check for correct parameters
        if len(request) == 2:
            await ctx.message.channel.send('Try "ia add [song | album | artist | label ]"')
            return

        # Add song
        if request[2] == 'song':
            # Get title
            title = await self.request_info(ctx, 'What is the song called?')

            # Get artist
            artist = await self.request_info(ctx, 'Who is the artist?')
            print(artist)

            # Get album
            yAlbum = ''
            while yAlbum != 'y' and yAlbum != 'n':
                yAlbum = await self.request_info(ctx, 'Is the song from an album? (y/n)')
                print(yAlbum)
            if yAlbum == 'y':
                album = await self.request_info(ctx, 'What is the name of the album')


            # Get genre
            genre_s = await self.request_info(ctx, 'What is the song\'s genre(s)? \n If there is multiple please seperate with a comma...')

            # Proccess genres into list
            genres = []
            cut = genre_s.find(',')
            while cut != -1:
                genres.append(genre_s[:cut])
                genre_s = genre_s[cut+2:]
                cut = genre_s.find(',')
            genres.append(genre_s)

            # Get link
            link = await self.request_info(ctx, 'What is the link to the song?')

            # Cut link to get unique key
            cut = link.find('=')+1
            key = link[cut:]

            # Attempt download
            await ctx.message.channel.send('Downloading...')
            await self.download(key)

            # Get length
            tag = aread('Music/{0}.m4a'.format(key))
            length = int(tag.duration)
            print(length)

            # Attempt database insertion
            await ctx.message.channel.send('Adding "{0}" to database'.format(title))
            try:

                # Insert with album
                if yAlbum == 'y':
                    query = "insert into music(title, artist, album, key, length) values ('{0}', '{1}', '{2}', '{3}', '{4}');"
                    self.cur.execute(query.format(title, artist, album, key, length))

                # Insert without album
                else:
                    query = "insert into music(title, artist, key, length) values ('{0}', '{1}', '{2}', '{3}');"
                    self.cur.execute(query.format(title, artist, key, length))

                # Insert all genres
                for genre in genres:
                    query = "insert into genre(key, genre) values ('{0}', '{1}');"
                    self.cur.execute(query.format(key, genre))

                # Save successful changes
                self.con.commit()
                await ctx.message.channel.send('Database modified successfully!')

            # If insertion fails
            except psycopg2.Error as e:
                await ctx.message.channel.send('Insert error...')
                self.con.rollback()
                print(e)

            return
        
        # Add artist
        elif request[2] == 'artist':
            # Get name
            name = await self.request_info(ctx, 'What is the artist\'s name?')
            
            # Get founded
            founded = await self.request_info(ctx, 'What year was the band founded')
			
	    # Attempt database insertion
            await ctx.message.channel.send('Adding "{0}" to database'.format(name))
            try:
                query = "insert into artist(name, founded) values ('{0}', '{1}');"
                self.cur.execute(query.format(name, founded))

                # Save successful changes
                self.con.commit()
                await ctx.message.channel.send('Database modified successfully!')

            # If insertion fails
            except psycopg2.Error as e:
                await ctx.message.channel.send('Insert error...')
                self.con.rollback()
                print(e)
				
            return

        # Add album
        elif request[2] == 'album':
            # Get name
            name = await self.request_info(ctx, 'What is the album\'s name?')

            # Get artist
            artist = await self.request_info(ctx, 'What artist is the album by?')

            # Get label
            label = await self.request_info(ctx, 'What label was the album published under?')

            # Get release
            release = await self.request_info(ctx, 'When was the album released?')

            # Get album art
            await ctx.message.channel.send('Finding album art...')
            query = '{0} {1} album cover'.format(name, artist)
            inst = gid.googleimagesdownload()
            art_m = inst.download({'keywords':query,
                                   'limit':1,
                                   'output_directory':'Art/',
                                   'no_directory':True})
            art = art_m[query][0]
            await ctx.message.channel.send(file=discord.File(art))

            # Attempt database insertion
            await ctx.message.channel.send('Adding "{0}" to database'.format(name))
            try:
                query = "insert into album(name, artist, label, art, release) values ('{0}', '{1}', '{2}', '{3}', '{4}');"
                self.cur.execute(query.format(name, artist, label, art, release))

                # Save successful changes
                self.con.commit()
                await ctx.message.channel.send('Database modified successfully!')

            # If insertion fails
            except psycopg2.Error as e:
                await ctx.message.channel.send('Insert error...')
                self.con.rollback()
                print(e)
                return

            #await ctx.message.channel.send('How many songs would you like to add?')
            #numsongs_m = await self.bot.wait_for('message', check=lambda m: m.author==ctx.message.author)
            numsongs = await self.request_info(ctx, 'How many songs would you like to add')#int(numsongs_m.content)

            for i in range(numsongs):
                # Get title
                await ctx.message.channel.send('Song {0} of {1}:'.format(i+1,numsongs))
                #await ctx.message.channel.send('What is the song called?')
                #title_m = await self.bot.wait_for('message', check=lambda m: m.author==ctx.message.author)
                title = await self.request_info(ctx, 'What is the song called?')#(title_m.content).lower()

                # Get genre
                #await ctx.message.channel.send('What is song\'s genre(s)?')
                #await ctx.message.channel.send('If there is multiple please separate with a comma...')
                #genre_m = await self.bot.wait_for('message', check=lambda m: m.author==ctx.message.author)
                genre_s = await self.request_info(ctx, 'What is song\'s genre(s)? \n If there is multiple please seperate with a comma')

                # Proccess genres into list
                genres = []
                cut = genre_s.find(',')
                while cut != -1:
                    genres.append(genre_s[:cut])
                    genre_s = genre_s[cut+2:]
                    cut = genre_s.find(',')
                genres.append(genre_s)

                # Get link
                await ctx.message.channel.send('What is the link to the song?')
                link_m = await self.bot.wait_for('message', check=lambda m: m.author==ctx.message.author)

                # Cut link to get unique key
                cut = link_m.content.find('=')+1
                key = link_m.content[cut:]

                # Attempt download
                await ctx.message.channel.send('Downloading...')
                await self.download(key)

                # Get length
                tag = aread('Music/{0}.m4a'.format(key))
                length = int(tag.duration)
                print(length)

                # Attempt database insertion
                await ctx.message.channel.send('Adding "{0}" to database'.format(title))
                try:
                    query = "insert into music(title, artist, album, key, length) values ('{0}', '{1}', '{2}', '{3}', '{4}');"
                    self.cur.execute(query.format(title, artist, name, key, length))
                    
                    # Insert all genres
                    for genre in genres:
                        query = "insert into genre(key, genre) values ('{0}', '{1}');"
                        self.cur.execute(query.format(key, genre))

                    # Save successful changes
                    self.con.commit()
                    await ctx.message.channel.send('Database modified successfully!')

                # If insertion fails
                except psycopg2.Error as e:
                    await ctx.message.channel.send('Insert error...')
                    self.con.rollback()
                    i+=1
                    print(e)

            return

        # Add label
        elif request[2] == 'label':
            # Get name
            await ctx.message.channel.send('What is the label\'s name?')
            name_m = await self.bot.wait_for('message', check=lambda m: m.author==ctx.message.author)
            name = (name_m.content).lower()

            # Get founded
            await ctx.message.channel.send('What year was the label founded?')
            founded_m = await self.bot.wait_for('message', check=lambda m: m.author==ctx.message.author)
            founded = (founded_m.content).lower()

            # Get address
            await ctx.message.channel.send('What city is the label\'s headquarters located in?')
            address_m = await self.bot.wait_for('message', check=lambda m: m.author==ctx.message.author)
            address = (address_m.content).lower()

            # Attempt database insertion
            await ctx.message.channel.send('Adding "{0}" to database'.format(name))
            try:
                query = "insert into label(name, founded, address) values ('{0}', '{1}', '{2}');"
                self.cur.execute(query.format(name, founded, address))

                # Save successful changes
                self.con.commit()
                await ctx.message.channel.send('Database modified successfully!')

            # If insertion fails
            except psycopg2.Error as e:
                await ctx.message.channel.send('Insert error...')
                self.con.rollback()
                print(e)

            return

        # Invalid parameter
        else:
            await ctx.message.channel.send('Try "ia add [song | album | artist | label ]"')
            return

    @commands.command(pass_context=True, no_pm=True)
    async def edit(self, ctx):
        return

#***********************************************************************************#
#                               Media Control Commands                              #
#***********************************************************************************#

    @commands.command(pass_context=True, no_pm=True)
    async def clear(self, ctx):
        if self.queue_titles == []:
            await ctx.message.channel.send("Queue is empty...")
        else:
            self.queue_titles = []
            self.queue_paths = asyncio.Queue()
            await ctx.message.channel.send("Queue cleared!")

    # Pauses audio loop
    @commands.command(pass_context=True, no_pm=True)
    async def pause(self, ctx):
        if self.playing:
            if not self.paused:
                self.paused = True
                self.player.pause()
                await ctx.message.channel.send("Media playback paused...")
            else:
                self.paused = False
                self.player.pause()
                await ctx.message.channel.send("Media playback resumed!")
        else:
            await ctx.message.channel.send('Nothing is playing...')


    # Enqueues from database
    @commands.command(pass_context=True, no_pm=True)
    async def play(self, ctx):
        try:
            self.channel = ctx.message.channel
            request = await self.string_split(ctx.message.content)

            # Handle incomplete usage
            if len(request) < 4:
                await ctx.message.channel.send('Try "ia play [song | album | artist | label | playlist | genre] ["name"]"')
                return

            # Concatenate search term
            for i in range(len(request)-4):
                request[3] += (' '+request[4+i])
            
            # Search 
            if request[2] in {'label','artist','album','playlist'}:
                self.cur.execute("select distinct name from {0} where name = '{1}';".format(request[2],request[3]))

            elif request[2] == 'genre':
                self.cur.execute("select distinct genre from genre where genre like '{0}';".format(request[3]))

            elif request[2] == 'song':
                self.cur.execute("select distinct title, artist, key from music where title like '{0}';".format(request[3]))

            # Handle incorrect usage
            else:
                await ctx.message.channel.send('Try "ia play [song | album | artist | label | playlist | genre] ["name"]"')
                return

            # Store search results
            results = self.cur.fetchall()

            if request[2] == 'song':
                # No results
                if len(results) < 1:
                    await ctx.message.channel.send('No results...')
                    return

                # Exactly one result
                elif len(results) == 1:
                    await ctx.message.channel.send('Enqueing: '+results[0][0]+" - "+results[0][1])
                    self.queue_titles.append([results[0][0].title(),results[0][1].title()])
                    await self.queue_paths.put("Music/"+results[0][2]+".m4a")

                # Multiple results
                else:
                    await ctx.message.channel.send('Multiple results, pick a number or all...')
                    all_results = ''
                    for i in range(len(results)):
                        all_results += str(i+1)+': '+results[i][0]+' - '+results[i][1]+'\n'
                    await ctx.message.channel.send( all_results)
                    choice_m = await self.bot.wait_for('message', check=lambda m: m.author==ctx.message.author)
                    choice = choice_m.content

                    # Play all results
                    if choice == 'all':
                        await ctx.message.channel.send('Enqueing: all results')
                        for r in results:
                            await self.queue_paths.put("Music/"+r[2]+".m4a")
                            self.queue_titles.append([r[0].title(),r[1].title()])

                    # Play one result
                    else:
                        await ctx.message.channel.send('Enqueing: '+results[int(choice)-1][0])
                        await self.queue_paths.put("Music/"+results[int(choice)-1][2]+".m4a")
                        self.queue_titles.append(results[int(choice)-1][0].title(),results[int(choice)-1][1].title())

            else:
                choice_num = "0"

                # No results
                if len(results) < 1:
                    await ctx.message.channel.send('No results...')
                    return

                # Exactly one result
                elif len(results) == 1:
                    choice_num = "1"

                # Multiple results
                if choice_num == 0:
                    await ctx.message.channel.send('Multiple results, pick a number...')
                    all_results = ''
                    for i in range(len(results)):
                        all_results += str(i+1)+': '+results[i][0]+'\n'
                    await ctx.message.channel.send(all_results)
                    choice_m = await self.bot.wait_for('message', check=lambda m: m.author==ctx.message.author)
                    choice_num = choice_m.content
                
                # Find matching songs
                choice = results[int(choice_num)-1][0] 
                
                if request[2] == 'artist':
                    self.cur.execute("select m.title, m.artist, m.key from music as m, artist as a where m.artist = a.name and a.name = '{0}';".format(choice))
                
                elif request[2] == 'album':
                    self.cur.execute("select m.title, m.artist, m.key, a.art from music as m, album as a where m.album = a.name and a.name = '{0}';".format(choice))

                elif request[2] == 'playlist':
                    self.cur.execute("select m.title, m.artist, m.key from music as m, playlist as p where m.key = p.key and p.name = '{0}';".format(choice))

                elif request[2] == 'genre':
                    self.cur.execute("select m.title, m.artist, m.key from music as m, genre as g where m.key = g.key and g.genre = '{0}';".format(choice))

                else:
                    self.cur.execute("select m.title, m.artist, m.key from music as m, label as l, album as a where l.name = a.label and a.name = m.album and l.name = '{0}';".format(choice))

                results = self.cur.fetchall()

                # Enqueue songs
                if request[2] == 'album':
                    await ctx.message.channel.send(file=discord.File(results[0][3]))
                await ctx.message.channel.send('Enqueing songs from {0}: {1}'.format(request[2], choice.title()))
                for r in results:
                    await self.queue_paths.put("Music/"+r[2]+".m4a")
                    self.queue_titles.append([r[0].title(),r[1].title()])



        except psycopg2.Error as e:
            await ctx.message.channel.send('Retrieval error...')
            print(e)

    # Prints names of songs in queue
    @commands.command(pass_context=True, no_pm=True)
    async def queue(self, ctx):
        if self.queue_paths.empty(): 
            await ctx.message.channel.send( 'Queue is empty...')
        else:
            q_str = ''
            for i in range(len(self.queue_titles)):
                q_str += (str(i+1)+': {0} - {1}\n'.format(self.queue_titles[i][0],self.queue_titles[i][1]))
            await ctx.message.channel.send( 'Current Queue:\n'+q_str)

    
    @commands.command(pass_context=True, no_pm=True)
    async def shuffle(self, ctx):
        if not self.queue_paths.empty():

            # Store values in queue_paths
            temp = []
            for i in range(self.queue_paths.qsize()):
                temp.append(await self.queue_paths.get())

            # Shuffle queue_paths and queue_titles at once
            c = list(zip(temp,self.queue_titles))
            random.shuffle(c)
            temp, self.queue_titles = list(zip(*c))
            for i in range(len(temp)):
                await self.queue_paths.put(temp[i])
            await ctx.message.channel.send('Shuffled!')

        else:
            await ctx.message.channel.send('Queue is empty...')
    
    # Ends the current song
    @commands.command(pass_context=True, no_pm=True)
    async def skip(self, ctx):
        if self.playing:
            await ctx.message.channel.send('Skipping...')
            self.next = True
        else:
            await ctx.message.channel.send('Nothing is playing...')

#***********************************************************************************#
#                           Discord Client Initialization                           #
#***********************************************************************************#

client=commands.Bot(command_prefix=commands.when_mentioned_or('ia '))
client.add_cog(Music(client))

@client.event
async def on_ready():
    print('User: '+str(client.user.name))
    print('ID: '+str(client.user.id))
    print('Ready!')

client.run(TOKEN)
