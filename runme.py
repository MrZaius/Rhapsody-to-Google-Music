from musicsync import MusicSync
# Quick Notes
# Using the directions to export a file from Rhapsody, make the delimiter (\), 
# output columns Playlist,artist,album,title (See playlist3.txt) example
# url:http://www.cutdek.com/blog/2011/6/23/exporting-your-rhapsody-library-to-csv.html
#you must have a Google Music All Access Subscription


ms = MusicSync("google_username","google_password")
ms.add_rhapsody_playlist("playlist.txt")
