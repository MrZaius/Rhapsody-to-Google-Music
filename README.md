Provides a utility class around the Google Music API that allows for easy syncing of csv file and ultimately an export of Rhapsody.

##Features
Choose a local playlistto sync and it will:
* Create or modify an existing Google Music playlist
* parse delimited file and search and match them to Google All Access.(Google Music Subscription Required) and
* 
the end)

##Usage

```python
from musicsync import MusicSync
ms = MusicSync()
# Will prompt for Email and Password - if 2-factor auth is on you'll need to generate a one-time password
# The first time you use this (or another script that uses gmusicapi) you will be prompted to authenticate via an OAuth browser window - you will need to copy paste the URL (be careful - under Windows sometimes spaces are inserted into the copy/paste at new lines)


#see  How to Export Rhapsody to a Playlist file
#url: http://www.cutdek.com/blog/2011/6/23/exporting-your-rhapsody-library-to-csv.html

#Delimiter should be: \ (see example playlist.txt file)

# To sync a playlist
ms.sync_playlist("c:/path/to/playlist")

#song_compare() -- matches the song from rhapsody to google music, if the script is having trouble matching songs, look to modify the rules in this def. 

#Note: sorry for the messy code, i got it to work for my needs in a few hours, and figured I'd dump it out here for others to use.

##Requirements
Requires:
* gmusicapi (can use: pip install gmusicapi - or get it from https://github.com/simon-weber/Unofficial-Google-Music-API)

- - -

API used: https://github.com/simon-weber/Unofficial-Google-Music-API

Thanks to: Kevin Kwok and Simon Weber and Tom

Use at your own risk - especially for existing playlists

Free to use, reuse, copy, clone, etc
