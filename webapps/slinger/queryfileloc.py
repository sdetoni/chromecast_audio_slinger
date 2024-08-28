import logging

import slinger.SlingerGlobalFuncs as SGF
from smb.SMBConnection import SMBConnection
import smb
import json
import os

self = eval('self'); output = self.output
postData = self.getCGIParametersFormData ()

if not "type"           in postData: postData["type"]           = ''
if not "location"       in postData: postData["location"]       = ''
if not "page_size"      in postData: postData["page_size"]      = ''
if not "sort_order"     in postData: postData["sort_order"]     = ''
if not "sort_type"      in postData: postData["sort_type"]      = ''
if not "filter_type"    in postData: postData["filter_type"]    = ''
if not "get_folder_art" in postData: postData["get_folder_art"] = ''

if not SGF.validateSMBFileAccessLocation(postData["type"].lower(), postData["location"]):
    output("no")
    exit(0)

if postData['get_folder_art'].lower() in ('y', 'yes', 'true', 'on'):
    artLoc = ""
    artURL = "img/folder.png"
    if postData["type"].lower() == 'smb' and postData["location"] != '':
        artLoc = SGF.getFolderArtSMB (postData["location"])
    elif postData["type"].lower() == 'file' and postData["location"] != '':
        # make sure there is leaf node in the location part to make the getFolderArtFile() work correctly.
        if not postData["location"].endswith(os.sep):
            postData["location"] += os.sep
        artLoc = SGF.getFolderArtFile (postData["location"])

    if artLoc != "":
        artURL = SGF.makeDownloadURL(self, postData["type"].lower(), artLoc)

    jsonArtURL = { "art_url" : artURL }
    self.do_HEAD(mimetype='application/json', turnOffCache=False, statusCode=200, closeHeader=True)
    output(json.dumps(jsonArtURL, indent=4))
    exit(0)

if postData["type"].lower() == 'smb' and postData["location"] != '':
    # read file locations
    _, _, server, shareName, filePath = SGF.parseSMBConfigString(postData["location"])
    username, password = SGF.matchSMBCredentialsConfigString(postData["location"])

    conn = SMBConnection(username=username, password=password, my_name="", remote_name="", use_ntlm_v2=True)
    conn.connect(server)

    fileList = []
    for fattrib in (smb.SMBConnection.SMB_FILE_ATTRIBUTE_DIRECTORY, smb.SMBConnection.SMB_FILE_ATTRIBUTE_INCL_NORMAL | smb.SMBConnection.SMB_FILE_ATTRIBUTE_ARCHIVE | smb.SMBConnection.SMB_FILE_ATTRIBUTE_READONLY | smb.SMBConnection.SMB_FILE_ATTRIBUTE_SYSTEM):
        flist = conn.listPath(service_name=shareName, path=filePath, search=fattrib)
        flist.sort(key= lambda x : x.filename)
        for file in flist:
            if file.filename in ('.', '..'):
                continue

            # test if matching for valid audio files only ...
            if (not file.isDirectory) and (postData["filter_type"] in ('audio_only')) and (not SGF.getCastMimeType (fileName = file.filename, testForKnownExt=True)):
                continue

            full_path = postData["location"].rstrip('\\') + '\\' +  file.filename
            if file.isDirectory:
                full_path += '\\'

            f = { "create_time" : file.create_time, "filename" : file.filename, "isDirectory" : file.isDirectory,
                  "isNormal" : file.isNormal, "short_name" : file.short_name, "file_size" : file.file_size, "full_path" : full_path }
            fileList.append(f)
    conn.close()

    self.do_HEAD(mimetype='application/json', turnOffCache=False, statusCode=200, closeHeader=True)
    output(json.dumps(fileList, indent=4))
    exit (0)
elif postData["type"].lower() == 'file' and postData["location"] != '':
    fileList = []
    dList = [d for d in os.listdir(postData["location"]) if os.path.isdir(postData["location"].rstrip(os.sep) + os.sep + d)]
    dList.sort()
    for d in dList:
        full_path = postData["location"].rstrip(os.sep) + os.sep + d + os.sep
        s = os.stat(full_path)

        f = {"create_time": s.st_ctime, "filename": d, "isDirectory": True,
             "isNormal": False, "short_name": d, "file_size": 0,
             "full_path": full_path}
        fileList.append(f)

    fList = [f for f in os.listdir(postData["location"]) if os.path.isfile(postData["location"].rstrip(os.sep) + os.sep + f)]
    fList.sort()
    for f in fList:
        full_path = postData["location"].rstrip(os.sep) + os.sep + f
        s = os.stat(full_path)

        # test if matching for valid audio files only ...
        if  (postData["filter_type"] in ('audio_only')) and (not SGF.getCastMimeType(fileName=f, testForKnownExt=True)):
            continue

        f = {"create_time": s.st_ctime, "filename": f, "isDirectory": False,
             "isNormal": True, "short_name": f, "file_size": s.st_size,
             "full_path": full_path}
        fileList.append(f)

    self.do_HEAD(mimetype='application/json', turnOffCache=False, statusCode=200, closeHeader=True)
    output(json.dumps(fileList, indent=4))
    exit (0)

self.do_HEAD(mimetype='application/json', turnOffCache=False, statusCode=500, closeHeader=True)



