import slinger.SlingerGlobalFuncs as SGF
import json

self = eval('self'); output = self.output
postData = self.getCGIParametersFormData ()
if not "action"            in postData: postData["action"]            = ''
if not "name"              in postData: postData["name"]              = ''
if not "newname"           in postData: postData["newname"]           = ''
if not "rowid"             in postData: postData["rowid"]             = ''
if not "type"              in postData: postData["type"]              = ''
if not "location"          in postData: postData["location"]          = ''
if not "directory_load"    in postData: postData["directory_load"]    = ''
if not "max_recurse_depth" in postData: postData["max_recurse_depth"] = '100'
if not "max_queue_len"     in postData: postData["max_queue_len"]     = '1000'

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
elif (postData["action"] == 'add_playlist_items') and (postData["name"] != '') and (len(postData["location"]) > 0):
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

output ("nope!")