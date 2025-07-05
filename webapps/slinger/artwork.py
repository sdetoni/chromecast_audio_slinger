import logging
import time

import daemon.GlobalFuncs         as GF
import slinger.SlingerGlobalFuncs as SGF
import json

self = eval('self'); output = self.output

postData = self.getCGIParametersFormData ()

if not "type"     in postData: postData["type"]     = ''
if not "location" in postData: postData["location"] = ''

if not SGF.validateSMBFileAccessLocation(postData["type"].lower(), postData["location"]):
    output("no")
    exit(0)

# only allow one instance to scan for artwork to prevent it from killing itself by DDOS
retry = 5
while not SGF.SearchArtSem.acquire(blocking=False):
    retry -= 1
    if retry < 0:
        output(json.dumps([], default=lambda o: o.__dict__, indent=4))
        exit(0)
    time.sleep(1000)

try:
    artWorkMetaData = []
    if postData["type"].lower() == 'smb' and postData["location"] != '':
        artWorkMetaData = SGF.loadDirectoryQueueSMB(location = SGF.getBaseLocationPath(postData["location"], postData["type"].lower()),
                                                    maxDepth=GF.Config.getSettingValue('slinger/MATCH_ART_MAX_SCAN_DEPTH'),
                                                    matchFunc=SGF.matchArtTypes)
    elif postData["type"].lower() == 'file' and postData["location"] != '':
        artWorkMetaData = SGF.loadDirectoryQueueFile(location = SGF.getBaseLocationPath(postData["location"], postData["type"].lower()),
                                                     maxDepth=GF.Config.getSettingValue('slinger/MATCH_ART_MAX_SCAN_DEPTH'),
                                                     matchFunc=SGF.matchArtTypes)

    # convert images into download urls... in a cover, album art file sorted list.
    coverImgDLS = []
    otherImgDLS = []
    for md in artWorkMetaData:
        loaded = False
        for name in GF.Config.getSettingList('slinger/ALBUM_ART_FILENAME'):
            if md['filename'].lower() == name.lower():
                coverImgDLS.append({'filename' : md['filename'], 'src' : SGF.makeDownloadURL(self, md['type'], md['full_path']) })
                loaded = True
                break

        if not loaded:
            otherImgDLS.append({'filename' : md['filename'], 'src' : SGF.makeDownloadURL(self, md['type'], md['full_path']) })

    output(json.dumps(coverImgDLS + otherImgDLS, default=lambda o: o.__dict__, indent=4))
finally:
    SGF.SearchArtSem.release()