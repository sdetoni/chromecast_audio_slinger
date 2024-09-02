import logging
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

artWorkMetaData = []

if postData["type"].lower() == 'smb' and postData["location"] != '':
    artWorkMetaData = SGF.loadDirectoryQueueSMB(location = SGF.getBaseLocationPath(postData["location"], postData["type"].lower()),
                                                maxDepth=GF.Config.getSettingValue('slinger/MATCH_ART_MAX_SCAN_DEPTH'),
                                                matchFunc=SGF.matchArtTypes)
elif postData["type"].lower() == 'file' and postData["location"] != '':
    artWorkMetaData = SGF.loadDirectoryQueueFile(location = SGF.getBaseLocationPath(postData["location"], postData["type"].lower()),
                                                 maxDepth=GF.Config.getSettingValue('slinger/MATCH_ART_MAX_SCAN_DEPTH'),
                                                 matchFunc=SGF.matchArtTypes)
# convert images into download urls...
imageDLS = []
for md in artWorkMetaData:
    imageDLS.append({'filename' : md['filename'], 'src' : SGF.makeDownloadURL(self, md['type'], md['full_path']) })
output(json.dumps(imageDLS, default=lambda o: o.__dict__, indent=4))