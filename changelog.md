# Change Log

## Version 0.085 Work in progress:
 * Added Docker Build process for Raspberry PI. 
 * [docker_build_raspberry_pi](docker_build_raspberry_pi/README.md)
 
## Version 0.08 Work in progress:
 * Added history played music viewer, and the ability to play the previous tracks.
 * Added live searching of metadata
 * Fixed displaying of album art issues between http(s) protocols.
 * Cosmetic GUI Changes

## Version 0.075 Work in progress:
 * Debugged HTTP Range requests further and hopefully fix it finally.
 * Identified my DLNA issue with Metadata and Samsung T.Vs. Basically the dislike the source URL with ?query=1234 type 
   parameters within the URL. So I have implemented a dynamically generated ID HASH that references the required metadata
   in the Slinger DB and send the correct file to the DLNA device, thus getting around the complex query parameter issue
   causing confusion.

## Version 0.07 Work in progress:
 * Bug fixes for device scanning and removal of devices once no longer on the network
 * Added initial/preliminary DLNA support, will work with Kodi, but may not work with your T.V due to
   likely requiring an valid url without parameters (looking at you Samsung). This is still work in progress to get around
   this limitation.
 * Added limited video support, can play mp4, avi, mkv etc type movies, update your config to add this ability
 * Added SMB metadata retrival limit to prevent large files taking along to cast, especially appropriate for video files
 * New config settings:
```
    MATCH_MUSIC_TYPE=mkv::video/mkv
    MATCH_MUSIC_TYPE=avi::video/avi
    MATCH_MUSIC_TYPE=mp4::video/mp4
    
    # MAX 200 megs to download to extract metadata
    SMB_MAX_METADATA_SCAN_SIZE=(1024*1024)*200       
``` 

## Version 0.06 Work in progress:
 * Added in browser Config Editor
 * Added graphical UI tweaks to the playlist
 * Added Spotify Playlist loader
 * Added metadata file validation (i.e. if you delete music files then run validation to remove metadata)
 * Moved most of the Ajax calls to use POST to work around encoding GET parameters

## Version 0.05 Work in progress:
 * Added Custom temp directory location for quick RAM disk type transcoding operations.
 
## Version 0.04 Work in progress:
 * Added .dsf SACD format playback to Chromecast via conversion to FLAC 24 bit 96khz
 * Update supported **Python release** up to **3.13**
 * Fixed graphical issues
