"""
    musicsync.py

    Provides a utility class around the Google Music API that allows for easy synching of playlists.
    Currently it will look at all the files already in the playlist and:
     Upload any missing files (and add them to the playlist)
     Add any files that are already uploaded but not in the online playlist
     Optionally remove any files from the playlist that are not in the local copy (does not delete
     files!)
     Uploads are done one by one followed by a playlist update for each file (rather than as a
     batch)
    It does not remove duplicate entries from playlists or handle multiple entries.

    TODO: Add optional duplicate remover

    API used: https://github.com/simon-weber/Unofficial-Google-Music-API
    Thanks to: Kevion Kwok and Simon Weber

    Use at your own risk - especially for existing playlists

    Free to use, reuse, copy, clone, etc

    Usage:
     ms = MusicSync()
     # Will prompt for Email and Password - if 2-factor auth is on you'll need to generate a one-
       time password
     ms.sync_playlist("c:/path/to/playlist.m3u")

     ms.delete_song("song_id")
"""
__author__ = "Tom Graham"
__email__ = "tom@sirwhite.com"


__modified_by__ = "Jon Feutz"
__modified_by_email__ = "jon.feutz@gmail.com"

#Purpose
#Modified Tom's script to read a file export of a Rhapsody sqlite3 database
#and then used the file to create playlists in Google Music.

#Modifieds script to Parse a file in the format::
#[Playlist]\[Artist]\[Album]\[Title]

# Quick Notes
# Using the directions for Rhapsody found here: 
# url:http://www.cutdek.com/blog/2011/6/23/exporting-your-rhapsody-library-to-csv.html
# Navicat Light works awesome for this, run query, choose export to text file, choose Other Symbol for delimiter and set to: \
# Modify the example.py with your google music username and password (will not work unless you have a subscription)
#install gmusicapi with pip

# I wrote this fairly quickly and didnt take the time reorganize the code.
# you may need to play with the song_compare subs to do a better job of find the correct song in all access.

 

from gmusicapi import Webclient, Mobileclient, Musicmanager
from gmusicapi.clients import OAUTH_FILEPATH
import mutagen
import json
import os
import time
import re
import codecs
from getpass import getpass
from httplib import BadStatusLine, CannotSendRequest

MAX_UPLOAD_ATTEMPTS_PER_FILE = 3
MAX_CONNECTION_ERRORS_BEFORE_QUIT = 5
STANDARD_SLEEP = 5
MAX_SONGS_IN_PLAYLIST = 6000
LOCAL_OAUTH_FILE = './oauth.cred'

class MusicSync(object):
    def __init__(self, email=None, password=None):
        self.mm = Musicmanager()
        self.wc = Webclient()
        self.mc = Mobileclient()
        if not email:
            email = raw_input("Email: ")
        if not password:
            password = getpass()

        self.email = email
        self.password = password

        self.logged_in = self.auth()

        print "Fetching playlists from Google..."
        self.playlists = self.wc.get_all_playlist_ids(auto=False)
        print "Got %d playlists." % len(self.playlists['user'])
        print ""


    def auth(self):
        self.logged_in = self.wc.login(self.email, self.password)
        self.logged_in = self.mc.login(self.email, self.password, Mobileclient.FROM_MAC_ADDRESS)
        if not self.logged_in:
            print "Login failed..."
            exit()

        print ""
        print "Logged in as %s" % self.email
        print ""

        if not os.path.isfile(OAUTH_FILEPATH):
            print "First time login. Please follow the instructions below:"
            self.mm.perform_oauth()
        self.logged_in = self.mm.login()
        if not self.logged_in:
            print "OAuth failed... try deleting your %s file and trying again." % OAUTH_FILEPATH
            exit()

        print "Authenticated"
        print ""
    

    def add_rhapsody_playlist(self, filename, remove_missing=False):
        filename = self.get_platform_path(filename)
        os.chdir(os.path.dirname(filename))
       # playlist_title = os.path.splitext(os.path.basename(filename))[0]
        print "Synching File: %s" % filename
      
       
        print "Parsing Songs from %s" % filename
        pc_songs = self.get_songs_from_file(filename)
        #print (pc_songs)
        print "%d songs in local file: %s" % (len(pc_songs),filename)

        # Sanity check max 1000 songs per playlist
        if len(pc_songs) > MAX_SONGS_IN_PLAYLIST:
            print "    Google music doesn't allow more than %d songs in a playlist..." % MAX_SONGS_IN_PLAYLIST
            print "    Will only attempt to sync the first %d songs." % MAX_SONGS_IN_PLAYLIST
            del pc_songs[MAX_SONGS_IN_PLAYLIST:]

        existing_files = 0
        added_files = 0
        failed_files = 0
        removed_files = 0
        fatal_count = 0

        for song in pc_songs:
           playlist_title = song['playlist']
           if playlist_title not in self.playlists['user']:
                self.playlists['user'][playlist_title] = [self.mc.create_playlist(playlist_title)]
                time.sleep(.7)
        print "Starting Playlist Sync with Google music..."
        for song in pc_songs:
            #print song
            
            plid = ""
           
            print  "--------------------------------"
            print  ""
            print  "Playlist: %s" % song['playlist']
            print  "Artist: %s"  % song['artist']
            print  "Song: %s" % song['title']
            print  "Album: %s" % song['album']
            
               
            playlist_title = song['playlist']    
               
            plid = self.playlists['user'][playlist_title][0]
                
            goog_songs = self.wc.get_playlist_songs(plid)
           
            if self.song_already_in_list(song, goog_songs):
                	existing_files += 1
                        print "Result: Song Already Added"
                	continue
            print "Total %d songs in Google playlist: %s" % (len(goog_songs),playlist_title)
            print "%s - %s,   didn't exist...Will try to add..." % (song['artist'],song['title'])
            
            print  ""
            print  "--------------------------------"	
            results = self.mc.search_all_access(song['title'], max_results=50)
            nid = self.filter_search_results(results, song)
            print "AA nId: %s " % nid
            if nid:
                song_id =  self.mc.add_aa_track(nid)
            	added = self.wc.add_songs_to_playlist(plid, song_id)
                
                
                print "Playlist UUid: %s" % plid
                print "Song ID: %s" % song_id
            	time.sleep(.3) # Don't spam the server too fast...
            	print "Result: done adding to playlist"  
            	added_files += 1
                continue
            else:
               query = "%s %s" % (song['artist'],song['title'].split(' ')[0])
               print "Query %s" % query
               results = self.mc.search_all_access(query, max_results=50)
               nid = self.filter_search_results(results, song)
               if nid:
                song_id =  self.mc.add_aa_track(nid)
            	added = self.wc.add_songs_to_playlist(plid, song_id)
                
                
                print "Playlist UUid: %s" % plid
                print "Song ID: %s" % song_id
            	time.sleep(.3) # Don't spam the server too fast...
            	print " -- done adding to playlist"  
            	added_files += 1
                continue    
            print "Result: NID Blank, Song not Found in All Access"


        print ""
        print "---"
        print "%d songs unmodified" % existing_files
        print "%d songs added" % added_files
        print "%d songs failed" % failed_files
        print "%d songs removed" % removed_files

   
     
    def get_songs_from_file(self, filename):
        songs = []
        f = codecs.open(filename, encoding='utf-8')
        for line in f:
            line = line.rstrip().replace(u'\ufeff',u'')
            if line == "" or line[0] == "#":
                continue
            la= line.split("\\")
            regex_filter = '[^A-Za-z0-9\,\-\.\ \(\)\'\!\?\$\/ \& \:]'
            
            artist = re.sub(regex_filter,'',la[1])
            playlist = re.sub(regex_filter,'',la[0])
            album = re.sub(regex_filter,'',la[2])
            title = re.sub(regex_filter,'',la[3])
            
           # print "Filtered Strings:"
           # print "Artist: %s" % artist
           # print "Playlist: %s" % playlist
           # print "Song: %s" % title
           # print "Album: %s" % album
 
            dt = {'playlist':playlist,'artist':artist, 'album': album, 'title': title}
           # print (dt)

            songs.append(dt)
        f.close()
        return songs

    def get_songs_from_playlist(self, filename):
        songs = []
        f = codecs.open(filename, encoding='utf-8')
        for line in f:
            line = line.rstrip().replace(u'\ufeff',u'')
            if line == "" or line[0] == "#":
                continue
            path  = os.path.abspath(self.get_platform_path(line))
            #if not os.path.exists(path):
             #   print "File not found: %s" % line
              #  continue
            songs.append(path)
        f.close()
        return songs

    def get_files_from_playlist(self, filename):
        files = []
        f = codecs.open(filename, encoding='utf-8')
        for line in f:
            line = line.rstrip().replace(u'\ufeff',u'')
            if line == "" or line[0] == "#":
                continue
            path  = os.path.abspath(self.get_platform_path(line))
            if not os.path.exists(path):
                print "File not found: %s" % line
                continue
            files.append(path)
        f.close()
        return files

    def song_already_in_list(self, song, goog_songs):
        #tag = self.get_id3_tag(filename)
        i = 0
        while i < len(goog_songs):
            #print goog_songs
            if self.tag_compare(goog_songs[i], song):
                goog_songs.pop(i)
                return True
            i += 1
        return False

    def file_already_in_list(self, filename, goog_songs):
        tag = self.get_id3_tag(filename)
        i = 0
        while i < len(goog_songs):
            if self.tag_compare(goog_songs[i], tag):
                goog_songs.pop(i)
                return True
            i += 1
        return False

    def get_id3_tag(self, filename):
        data = mutagen.File(filename, easy=True)
        r = {}
        if 'title' not in data:
            title = os.path.splitext(os.path.basename(filename))[0]
            print 'Found song with no ID3 title, setting using filename:'
            print '  %s' % title
            print '  (please note - the id3 format used (v2.4) is invisible to windows)'
            data['title'] = [title]
            data.save()
        r['title'] = data['title'][0]
        r['track'] = int(data['tracknumber'][0].split('/')[0]) if 'tracknumber' in data else 0
        # If there is no track, try and get a track number off the front of the file... since thats
        # what google seems to do...
        # Not sure how google expects it to be formatted, for now this is a best guess
        if r['track'] == 0:
            m = re.match("(\d+) ", os.path.basename(filename))
            if m:
                r['track'] = int(m.group(0))
        r['artist'] = data['artist'][0] if 'artist' in data else ''
        r['album'] = data['album'][0] if 'album' in data else ''
        return r

    def find_song(self, filename,plid):
        tag = self.get_id3_tag(filename)
        print "Song Tag: %s " % tag
        print "Filename: %s" % filename
        ws_plids =  []
        ws_plids.append(plid)
        print (ws_plids)
        playlists = self.wc.get_all_playlist_ids()
        print (playlists)
        results = self.wc.get_playlist_songs(ws_plids)
        # NOTE - dianostic print here to check results if you're creating duplicates
        print results
        print "%s ][ %s ][ %s ][ %s" % (tag['title'], tag['artist'], tag['album'], tag['track'])
        for r in results:
            if self.tag_compare(r, tag):
                # TODO: add rough time check to make sure its "close"
                return r
        return None

    def filter_search_results(self,results, song):
       #Try Exact Matching
       for g_song in results['song_hits']:
            if self.tag_compare(g_song['track'],song):
               return g_song['track']['nid']
            elif self.song_compare(g_song['track'],song,'artist'):
               #try just the artist
               return g_song['track']['nid']
            elif self.song_compare(g_song['track'],song,'part-song'):
               #try part of song and artist
               return g_song['track']['nid']
       return None
   
    def song_compare(self,g_song,tag,type):
         if 'track' not in g_song:
            g_song['track'] = 0
         title_parts = tag['title'].split('(') #removing shit like (featuring wiz)
         tp = title_parts[0].split(' ') #First word maybe
         if 'artist'in type:
          return g_song['artist'].lower() == tag['artist'].lower()
         if 'part-song' in type:
           return g_song['title'].find(tp[0]) and g_song['artist'].lower() == tag['artist'].lower()
         
         return None
         
    def tag_compare(self, g_song, tag):
        if 'track' not in g_song:
            g_song['track'] = 0
                  
        return g_song['title'].split(' ')[0].lower() == tag['title'].split(' ')[0].lower() and\
               g_song['artist'].lower() == tag['artist'].lower()

    def delete_song(self, sid):
        self.wc.delete_songs(sid)
        print "Deleted song by id [%s]" % sid

    def get_platform_path(self, full_path):
        # Try to avoid messing with the path if possible
        if os.sep == '/' and '\\' not in full_path:
            return full_path
        if os.sep == '\\' and '\\' in full_path:
            return full_path
        if '\\' not in full_path:
            return full_path
        return os.path.normpath(full_path.replace('\\', '/'))
