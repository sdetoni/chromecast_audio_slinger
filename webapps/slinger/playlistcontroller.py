import daemon.GlobalFuncs as GF
import slinger.SlingerGlobalFuncs as SGF
import json
import re
import logging

self = eval('self'); output = self.output
postData = self.getCGIParametersFormData ()
if not "action"             in postData: postData["action"]             = ''
if not "name"               in postData: postData["name"]               = ''
if not "newname"            in postData: postData["newname"]            = ''
if not "rowid"              in postData: postData["rowid"]              = ''
if not "type"               in postData: postData["type"]               = ''
if not "location"           in postData: postData["location"]           = ''
if not "directory_load"     in postData: postData["directory_load"]     = ''
if not "max_recurse_depth"  in postData: postData["max_recurse_depth"]  = '100'
if not "max_queue_len"      in postData: postData["max_queue_len"]      = '1000'
if not "spotifyPlaylistUrl" in postData: postData["spotifyPlaylistUrl"] = ''

postData["name"] = postData["name"].strip()

if not isinstance(postData["rowid"], list):
    postData["rowid"] = [ postData["rowid"] ]

if not isinstance(postData["location"], list):
    postData["location"] = [ postData["location"] ]

if postData["action"] == "playlist_list":
    # load playlist matching on name, otherwise load all playlists
    jsonData = {}
    plList = []
    if postData["name"]:
        if not isinstance(postData["name"], list):
            plList = [postData["name"]]
        else:
            plList = postData["name"]
    else:
        for plName in SGF.DB.GetPlayListNames():
            plList.append(plName['name'])

    for plName in plList:
        jsonData[plName] = SGF.DB.GetPlayListSongs (playListName=plName)
        # load metadata for playlist:
        for song in jsonData[plName]:
            if song['type'] == 'smb':
                song['metadata'] = SGF.getMediaMetaDataSMB (song['location'], httpObj=self)
            elif song['type'] == 'file':
                song['metadata'] = SGF.getMediaMetaDataFile(song['location'], httpObj=self)

    output(json.dumps(jsonData, default=lambda o: o.__dict__, indent=4))
    exit (0)
elif (postData["action"] == 'exists_playlist_item') and (postData["name"] != '') and (len(postData["location"][0]) > 0) and (len(postData["type"]) > 0):
    r = { 'exists' : False, 'rowid' : -1 }
    item = SGF.DB.PlayListSongExists (name = postData["name"], location=postData["location"][0], type=postData["type"])
    if item:
        r = { 'exists' : True, 'rowid' : item['seq'] }
    output(json.dumps(r, default=lambda o: o.__dict__, indent=4))
    exit(0)
elif (postData["action"] == 'add_playlist_items') and (postData["name"] != '') and (len(postData["location"]) > 0) and (len(postData["type"]) > 0):
    for loc in postData["location"]:
        # Decode possible unicode string
        loc = SGF.decode_percent_u(loc)

        if not SGF.validateSMBFileAccessLocation(postData["type"].lower(), loc):
            continue

        if postData["directory_load"] == 'true':
            if postData["type"] == 'smb':
                queueFileList = SGF.loadDirectoryQueueSMB(location=loc, maxDepth=int(postData["max_recurse_depth"]),
                                                          maxQueueLen=int(postData["max_queue_len"]))
            elif postData["type"] == 'file':
                queueFileList = SGF.loadDirectoryQueueFile(location=loc, maxDepth=int(postData["max_recurse_depth"]),
                                                           maxQueueLen=int(postData["max_queue_len"]))
            for qf in queueFileList:
                SGF.DB.AddPlayListSong (playListName=postData["name"], location=qf["full_path"], type = qf["type"])
        else:
            if loc:
                SGF.DB.AddPlayListSong(playListName=postData["name"], location=loc, type=postData["type"])
    output("ok")
elif  (postData["action"] == 'delete_playlist_items') and (postData["name"] != '') and (len(postData["rowid"]) > 0):
    SGF.DB.DeletePlayListSongs (postData["name"], postData["rowid"])
    output ("ok")
    exit(0)
elif (postData["action"] == 'get_playlist_names'):
    pl = SGF.DB.GetPlayListNames()
    output(json.dumps(pl, default=lambda o: o.__dict__, indent=4))
    exit(0)
elif (postData["action"] == 'create_playlist') and (postData["name"] != '') and (not SGF.DB.PlayListExists (postData["name"])):
    SGF.DB.CreatePlayList (postData["name"])
    output ("ok")
    exit(0)
elif (postData["action"] == 'delete_playlist') and (postData["name"] != ''):
    SGF.DB.DeletePlayList (postData["name"])
    output ("ok")
    exit(0)
elif (postData["action"] == 'rename_playlist') and (postData["name"] != '') and (postData["newname"] != ''):
    if SGF.DB.RenamePlayList (postData["name"], postData["newname"]):
        output('ok')
    else:
        output('name already exists')
    exit(0)
elif  (postData["action"] == 'import_spotify_playlist'):
    spotifyPlaylistUrl  = postData["spotifyPlaylistUrl"]
    spotifyPlaylistID   = spotifyPlaylistUrl.split("/")[-1].split("?")[0]
    spotifyClientID     = GF.Config.getSetting ('slinger/SPOTIFY_CLIENT_ID',     "5f573c9620494bae87890c0f08a60293")
    spotifyClientSecret = GF.Config.getSetting ('slinger/SPOTIFT_CLIENT_SECRET', "212476d9b0f3472eaa762d90b19b0ba8")
    accessToken         = SGF.Spotify_GetAccessToken  (client_id=spotifyClientID, client_secret=spotifyClientSecret)
    tracks              = SGF.Spotify_GetPlaylistTracks (access_token=accessToken, playlist_id=spotifyPlaylistID)
    playListInfo        = SGF.Spotify_GetPlaylistInfo (access_token=accessToken, playlist_id=spotifyPlaylistID)

    # create a new playlist
    if not playListInfo:
        logging.error(f"Playlist appears invalid : {spotifyPlaylistUrl}")
        exit (0)

    SGF.DB.CreatePlayList(playListInfo["name"])

    # scan spotify playlist and match to metadata
    infoResponse = ""
    loadedCount = 0
    failedCount = 0

    for track in tracks:
        matchedLocation = {'row' : None, 'score' : 0, 'metadata' : '' }

        for matchPass in range (0,2):  # first pass match on name as is, next passes removed remastered keywords
            trackName   = track["track"]["name"]
            trackAlbum  = track["track"]["album"]["name"]
            trackArtist = track["track"]["artists"][0]["name"]

            if matchPass:
                for regexpNamePat in (r'(.*)(\(.*\))', r'(.*)(- remaster.*)'):
                    m = re.match(regexpNamePat, trackName, re.IGNORECASE)
                    if m:
                        trackName = m.group(1).strip()
                    m = re.match(regexpNamePat, trackAlbum, re.IGNORECASE)
                    if m:
                        trackAlbum = m.group(1).strip()

                if re.match(r".*\/.*", trackArtist):
                    trackArtist = re.sub(r'(.*?)\s*\/\s*(.*)', r'(\g<1>|\g<2>)',  trackArtist, count=1, flags=re.IGNORECASE)


            for row  in SGF.DB.SearchMetaDataTrackAlbumArtist (regexTrack=trackName, regexArtist=trackArtist, regexAlbum=trackAlbum):
                score    = 10
                metadata = json.loads(row['metadata'])
                bitrate  = 0

                # increate name matching by removing '- Remastered' name tags
                if (re.search(trackAlbum, metadata['albumName'], re.IGNORECASE) and re.search(trackArtist, metadata['artist'], re.IGNORECASE)):
                    score = 50

                # very basic bitrate calculation
                if 'bitrate' in metadata.keys():
                    try:
                        br      =  int(metadata['bitrate'].split(' ')[0])
                        bitrate =  br
                        score   += br / 100
                    except:
                        pass
                elif row['location'].lower().endswith('.flac'):
                    score += 100

                if (not matchedLocation['row']) or (matchedLocation['score'] < score):
                    matchedLocation['row']      = row
                    matchedLocation['score']    = score
                    matchedLocation['metadata'] = metadata
                    continue

            if matchedLocation['row']:
                logging.info (f"Loading {SGF.toASCII(str(matchedLocation['row']['location']))} into play list '{playListInfo['name']}'")
                SGF.DB.AddPlayListSong(playListInfo["name"], matchedLocation['row']["location"], matchedLocation['row']['type'])
                infoResponse += f"ADDED '{trackName}' from album '{trackAlbum}', artist '{trackArtist}'\n"
                loadedCount += 1
                break
            else:
                if matchPass:
                    logging.warning(f"Failed matching '{trackName}' on album '{trackAlbum}' as artist '{trackArtist}'")
                    infoResponse += f"FAILED MATCH on '{trackName}' from album '{trackAlbum}', artist '{trackArtist}'\n"
                    failedCount += 1

    infoResponse = f"Play List: {playListInfo['name']}\n" + \
                   f"Loaded: {loadedCount}, Failed Matches: {failedCount}, Playlist Size:{loadedCount + failedCount}\n\n" + \
                   infoResponse
    output(infoResponse.strip())
    exit(0)

output ("nope!")