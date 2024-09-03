import os
import re
import traceback

import daemon.GlobalFuncs as GF
import pychromecast
import zeroconf
from datetime import datetime, timedelta
import urllib
import pymediainfo
import logging
import io
import threading
import slinger.SlingerChromeCastQueue as SlingerChromeCastQueue
import slinger.SlingerDB
from smb.SMBConnection import SMBConnection
import smb
import time
import uuid
import glob
import slinger.crontab as crontab
import socket

DB = slinger.SlingerDB.DB

def get_host_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        # doesn't even have to be reachable
        s.connect(('192.0.0.8', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

LocalHostIP = get_host_ip()

def rtnNoPasswordSMBPath (location):
    un, pw, serv, sName, fp = parseSMBConfigString(location)
    return '\\\\' + serv + '\\' + sName + '\\' + fp
def validateSMBFileAccessLocation (type, path):
    if len(path) <= 0:
        return False

    if type == 'smb':
        pathTest = rtnNoPasswordSMBPath (path)
        for shareInfo in GF.Config.getSettingList('slinger/SMB_MUSIC_UNCPATH'):
            if pathTest.startswith(rtnNoPasswordSMBPath (shareInfo)):
                return True
    elif type == 'file':
        for fileInfo in GF.Config.getSettingList('slinger/FILE_MUSIC_PATH'):
            fileInfo  = fileInfo.rstrip(os.sep)

            # add a missing separator onto path to complete matching with and without os separator char (/ or \)
            if len(path) == len(fileInfo) and (path[-1] != os.sep):
                path = path + os.sep

            if path.startswith(fileInfo + os.sep):
                return True
    return False

def discover_chromecasts():
    zconf = zeroconf.Zeroconf()
    browser = pychromecast.CastBrowser(pychromecast.SimpleCastListener(lambda uuid, service: print(browser.devices[uuid].friendly_name)), zconf)
    browser.start_discovery()

    # Wait for the timeout or the maximum number of devices
    discover_complete = threading.Event()
    discover_complete.wait(5)
    ##pychromecast.discovery.stop_discovery(browser)
    browser.stop_discovery()

    # return list of discovered devices...
    return pychromecast.get_listed_chromecasts(friendly_names=[x.friendly_name for x in browser.devices.values()])

ChromeCastCacheTimeOut = None
ChromeCastCache        = None
def getCachedChromeCast (force=False):
    global ChromeCastCacheTimeOut, ChromeCastCache
    n = datetime.now()
    if not ChromeCastCacheTimeOut:
        ChromeCastCacheTimeOut = n
    if force or ChromeCastCacheTimeOut <= n or not ChromeCastCache or len(ChromeCastCache[0]) <= 0:
        #ChromeCastCache = pychromecast.get_chromecasts()
        lastLen = 0;
        if ChromeCastCache:
            lastLen = len(ChromeCastCache)

        ChromeCastCache = discover_chromecasts()

        # check if detection succeeded, changed or nothing found.
        # if changed then check more frequently.
        if len(ChromeCastCache) <= 0 or lastLen != len(ChromeCastCache):
            ChromeCastCacheTimeOut = datetime.now() + timedelta(seconds=10)
        else:
            ChromeCastCacheTimeOut =  datetime.now() + timedelta(seconds=GF.Config.getSettingValue ('slinger/CHROMECAST_CACHE_TIMEOUT'))

    return ChromeCastCache


def getBaseLocationPath (location, type):
    if type == 'smb':
        if location.endswith('\\'):
            return location
        return location.rsplit('\\', 1)[0] + '\\'
    elif type == 'file':
        if location.endswith(os.sep):
            return location
        return location.rsplit(os.sep, 1)[0] + os.sep

    return ''
def decode_percent_u(encoded_str):
    # Decode the standard percent-encoded parts
    decoded_str = urllib.parse.unquote(encoded_str)

    # Custom decoding for %uXXXX sequences
    def decode_unicode(match):
        # Extract the hexadecimal part and convert it to an integer
        hex_value = match.group(1)
        char = chr(int(hex_value, 16))
        return char

    import re
    # Regular expression to find all %uXXXX sequences
    decoded_str = re.sub(r'%u([0-9A-Fa-f]{4})', decode_unicode, decoded_str)
    return decoded_str

# used to parse SMB_MUSIC_UNCPATH parameters into:
#  username, password, server, shareName, filePath
def parseSMBConfigString (strParam):
    username = password = ""
    strParam = decode_percent_u(strParam)
    param = strParam
    up = param.split('::', 1)
    if len(up) >= 2:
        up = up[0].split('/', 1)
        if len(up) > 0:
            username = up[0]
        if len(up) > 1:
            password = up[1]
        param = param.split('::', 1)[1].strip()
    else:
        param = strParam

    locParts = param.lstrip('\\\\').split('\\')

    server = shareName = filePath = ''
    if len(locParts) > 0:
        server = locParts[0]
    if len(locParts) >= 2:
        shareName = locParts[1]
    if len(locParts) >= 3:
        filePath = '\\'.join(locParts[2:])

    return username, password, server, shareName, filePath

def matchSMBCredentialsConfigString (location):
    username = password = ''
    if location.startswith('\\\\'):
        for param in GF.Config.getSettingList('slinger/SMB_MUSIC_UNCPATH'):
            up = param.split('::', 1)
            if len(up) >= 2 and location.startswith(up[1]):
                up = up[0].split('/', 1)
                if len(up) > 0:
                    username = up[0]
                if len(up) > 1:
                    password = up[1]
                return username, password
            elif location.startswith(up[0]):
                return username, password
    return username, password

def toASCII (s):
    return s.encode("latin-1", "ignore")

def getCastMimeType (fileName, testForKnownExt=False):
    ext = fileName.split ('.')[-1].lower()

    for audioType in GF.Config.getSettingList('slinger/MATCH_MUSIC_TYPE'):
        audioType = audioType.split('::')
        if ext == audioType[0]:
            return audioType[1]

    if testForKnownExt:
        return None
    return "audio"

def matchArtTypes (fileName, testForKnownExt=False):
    ext = fileName.split ('.')[-1].lower()
    for regexp in GF.Config.getSettingList('slinger/MATCH_ART_IMAGE_REGEXP'):
        if re.match(regexp, fileName, re.IGNORECASE):
            return f"image/{ext}"

    if testForKnownExt:
        return None

    return "unknown"

def loadDirectoryQueueSMB (location, maxDepth=100, maxQueueLen=1000, queueFileList=None, smbConn=None, matchFunc=getCastMimeType):
    if not queueFileList:
        queueFileList = []

    if not validateSMBFileAccessLocation('smb', location):
        return queueFileList

    try:
        _, _, server, shareName, filePath = parseSMBConfigString(location)
        if not smbConn:
            username, password = matchSMBCredentialsConfigString(location)
            conn = SMBConnection(username=username, password=password, my_name="", remote_name="", use_ntlm_v2=True)
            conn.connect(server)
        else:
            conn = smbConn

        for fattrib in (smb.SMBConnection.SMB_FILE_ATTRIBUTE_DIRECTORY,
                        smb.SMBConnection.SMB_FILE_ATTRIBUTE_INCL_NORMAL | smb.SMBConnection.SMB_FILE_ATTRIBUTE_ARCHIVE | smb.SMBConnection.SMB_FILE_ATTRIBUTE_READONLY | smb.SMBConnection.SMB_FILE_ATTRIBUTE_SYSTEM):
            flist = conn.listPath(service_name=shareName, path=filePath, search=fattrib)
            flist.sort(key=lambda x: x.filename)
            for file in flist:
                if file.filename in ('.', '..'):
                    continue

                full_path = location.rstrip('\\') + '\\' + file.filename
                logging.info (f"Processing : {toASCII(full_path)}" )
                if file.isDirectory:
                    full_path += '\\'

                    if maxDepth and maxDepth > 0:
                        queueFileList = loadDirectoryQueueSMB(location=full_path, maxDepth=maxDepth-1, maxQueueLen=maxQueueLen, queueFileList=queueFileList, smbConn=conn, matchFunc=matchFunc)
                        continue
                    else:
                        continue

                f = {"create_time": file.create_time, "filename": file.filename, "isDirectory": file.isDirectory,
                     "isNormal": file.isNormal, "short_name": file.short_name, "file_size": file.file_size,
                     "full_path": full_path, "type":"smb"}

                # determine if this a somewhat supported file, and add to queue
                if matchFunc(file.filename, testForKnownExt=True):
                    if len(queueFileList) < maxQueueLen:
                        queueFileList.append(f)
                    else:
                        break

    except Exception as e:
        logging.error(f"{e} [2] Failed loading file @ {server}\\{shareName}\\{filePath}")
    finally:
        try:
            if not smbConn:
                conn.close()
        except:
            pass

    return queueFileList

def loadDirectoryQueueFile (location, maxDepth=100, maxQueueLen=1000, queueFileList = None, matchFunc=getCastMimeType):
    if not queueFileList:
        queueFileList = []

    if not validateSMBFileAccessLocation('file', location):
        return queueFileList

    try:
        fileList = []
        dList = [d for d in os.listdir(location) if os.path.isdir(location.rstrip(os.sep) + os.sep + d)]
        dList.sort()

        for d in dList:
            full_path = location.rstrip(os.sep) + os.sep + d
            if maxDepth > 0:
                queueFileList = loadDirectoryQueueFile(location=full_path, maxDepth=maxDepth - 1, maxQueueLen=maxQueueLen, queueFileList=queueFileList, matchFunc=matchFunc)
                continue
            else:
                continue

        fList = [f for f in os.listdir(location) if os.path.isfile(location.rstrip(os.sep) + os.sep + f)]
        fList.sort()
        for f in fList:
            full_path = location.rstrip(os.sep) + os.sep + f
            s = os.stat(full_path)

            qf = {"create_time": s.st_ctime, "filename": f, "isDirectory": False,
                 "isNormal": True, "short_name": f, "file_size": s.st_size,
                 "full_path": full_path, "type":"file"}

            # determine if this a somewhat supported file, and add to queue
            if matchFunc(f, testForKnownExt=True):
                if maxQueueLen and len(queueFileList) < maxQueueLen:
                    queueFileList.append(qf)
                else:
                    break
    except Exception as e:
        logging.error(f"{e} Failed loading file @ {location}")
    return queueFileList

def getFolderArtSMB (location, trimLeaf = False, smbConn=None):
    albumArtFilename = ""
    try:
        _, _, server, shareName, filePath = parseSMBConfigString(location)
        if not smbConn:
            username, password = matchSMBCredentialsConfigString(location)
            conn = SMBConnection(username=username, password=password, my_name="", remote_name="", use_ntlm_v2=True)
            conn.connect(server)
        else:
            conn = smbConn

        #load folder image for album background if it exists.
        if trimLeaf:
            parentPath = filePath.rsplit ('\\', 1)[0]
        else:
            parentPath = filePath
        for name in GF.Config.getSettingList('slinger/ALBUM_ART_FILENAME'):
            name = name.lower()
            try:
                for file in conn.listPath(service_name=shareName, path=parentPath):
                    if (file.filename.lower() == name.lower()):
                        return f"\\\\{server}\\{shareName}\\{parentPath}\\{file.filename}"
            except:
                pass
    except Exception as e:
        logging.error(f"{e} [getFolderArtSMB] Failed loading file @ {server}\\{shareName}\\{filePath}")
    finally:
        try:
            if not smbConn:
                conn.close()
        except:
            pass
    return albumArtFilename

def makeDownloadURL (httpObj, type, location):
    httpPort = GF.Config.getSetting('HTTP_PORT', '')
    if not httpPort:
        httpPort = httpObj.port_number

    # use host ipv4 address as chromecast may/will not be able to decode local host DNS names.
    hostnamePort = f"{LocalHostIP}:{httpPort}"
    downloadURL = f'{httpObj.protocol}://{hostnamePort}{httpObj.queryBasePath}accessfile.py'
    downloadURL += f'?type={type}&location={urllib.parse.quote(location)}'
    return downloadURL

def getMediaMetaDataSMB (location, httpObj=None, smbConn=None):
    metadata = {}
    if not validateSMBFileAccessLocation('smb', location):
        return metadata

    try:
        _, _, server, shareName, filePath = parseSMBConfigString(location)

        # defaults if it fails to parse ...
        metadata["title"]     = filePath.rsplit('\\', 1)[1]
        metadata["albumName"] = metadata["album_name"] = (filePath.rsplit('\\', 1)[0]).rsplit('\\', 1)[-1]
        metadata["artist"]    = metadata["albumArtist"] = metadata["album_artist"] = 'unknown'
        metadata['bitrate']   = metadata["album_art_location"] = metadata["album_art_location_type"] = metadata["album_art_url"] = ''
        metadata["slinger_uuid"] = str(uuid.uuid1())
        metadata["metadataType"] = "MusicTrackMediaMetadata"

        cachedMetadata = DB.GetCachedMetadata (location, 'smb')
        if cachedMetadata:
            cachedMetadata["slinger_uuid"] = str(uuid.uuid1())
            # build cover art download link dynamically
            if cachedMetadata["album_art_location"] and httpObj:
               cachedMetadata["album_art_url"] = makeDownloadURL(httpObj, cachedMetadata["album_art_location_type"], cachedMetadata["album_art_location"])
            return cachedMetadata

        if not smbConn:
            username, password = matchSMBCredentialsConfigString(location)
            conn = SMBConnection(username=username, password=password, my_name="", remote_name="", use_ntlm_v2=True)
            conn.connect(server)
        else:
            conn = smbConn
        file_attr = conn.getAttributes(shareName, filePath)

        fobj = io.BytesIO()
        file_attributes, filesize = conn.retrieveFile(shareName, filePath, fobj)
        fobj.seek(0)

        mediaInfo = pymediainfo.MediaInfo.parse(fobj)
        mi = mediaInfo.tracks[0].to_data()

        albumArtFilename = getFolderArtSMB(location, trimLeaf=True, smbConn=conn)

        if "title" in mi:
            metadata["title"] = mi["title"]

        if 'other_overall_bit_rate' in mi:
            metadata["bitrate"] = mi['other_overall_bit_rate'][0]

        if "album" in mi:
            metadata["album_name"] = mi["album"]
            metadata["albumName"]  = mi["album"]

        if "album_artist" in mi:
            metadata["album_artist"] = mi["album_artist"]
            metadata["albumArtist"]  = mi["album_artist"]

        if "album_performer" in mi:
            metadata["album_artist"] = mi["album_performer"]
            metadata["artist"] = mi["album_performer"]

        if "performer" in mi:
            metadata["artist"] = mi["performer"]

        # build cover art download link dynamically
        if albumArtFilename:
            if httpObj:
                metadata["album_art_url"] = makeDownloadURL (httpObj, 'smb', albumArtFilename)
            else:
                metadata["album_art_url"] = ''

            metadata["album_art_location"]      = albumArtFilename
            metadata["album_art_location_type"] = "smb"

        DB.StoreCachedMetadata(location, 'smb', metadata)
    except Exception as e:
        logging.error(f"{e} [1] Failed loading file @ {server}\\{shareName}\\{filePath}")
    finally:
        try:
            if not smbConn:
                conn.close()
        except:
            pass

    return metadata

def getFolderArtFile (location):
    parentPath = location.rsplit(os.sep, 1)[0]

    albumArtFilename = ""
    for ff in [f for f in os.listdir(parentPath) if os.path.isfile(parentPath.rstrip(os.sep) + os.sep + f)]:
        if (isFolderArt (location=ff)):
            return parentPath.rstrip(os.sep) + os.sep + ff
    return albumArtFilename

def isFolderArt (location):
    for name in GF.Config.getSettingList('slinger/ALBUM_ART_FILENAME'):
        name = name.lower()
        if location.lower().endswith(name):
            return True
    return False

def getMediaMetaDataFile (location, httpObj=None):
    metadata = {}
    if not validateSMBFileAccessLocation('file', location):
        return metadata

    # defaults if it fails to parse ...
    metadata["title"] = location.rsplit(os.sep, 1)[1]
    metadata["albumName"] = metadata["album_name"]  = (location.rsplit(os.sep, 1)[0]).rsplit(os.sep, 1)[-1]
    metadata["artist"]    = metadata["albumArtist"] = metadata["album_artist"] = 'unknown'
    metadata["album_art_location"] = metadata["album_art_location_type"] = metadata["album_art_url"] = ''
    metadata["slinger_uuid"] = str(uuid.uuid1())
    metadata["metadataType"] = "MusicTrackMediaMetadata"

    """ media Info 
        "proportion_of_this_stream": "0.00143",
        "title": "Walkie-Talkie Man",
        "album": "2004 KROQ New Music",
        "album_performer": "Various Artists",
        "track_name": "Walkie-Talkie Man",
        "track_name_position": "10",
        "performer": "Steriogram",
        "composer": "Steriogram",
        "genre": "Alternative",
        "recorded_date": "2003",
    
    pychromecast
        'title'         : cast.media_controller.status.title,
        'album_artist'  : cast.media_controller.status.album_artist,
        'album_name'    : cast.media_controller.status.album_name,
        'artist'        : cast.media_controller.status.album_name, 
    """
    try:
        cachedMetadata = DB.GetCachedMetadata (location, 'file')
        if cachedMetadata:
            cachedMetadata["slinger_uuid"] = str(uuid.uuid1())
            if cachedMetadata["album_art_location"] and httpObj:
               cachedMetadata["album_art_url"] = makeDownloadURL(httpObj, cachedMetadata["album_art_location_type"], cachedMetadata["album_art_location"])
            return cachedMetadata

        mediaInfo = pymediainfo.MediaInfo.parse(location)
        mi = mediaInfo.tracks[0].to_data()

        # load folder image for album background if it exists.
        albumArtFilename = getFolderArtFile (location)

        if "title" in mi:
            metadata["title"] = mi["title"]

        if "album" in mi:
            metadata["album_name"] = mi["album"]
            metadata["albumName"] = mi["album"]

        if "album_artist" in mi:
            metadata["album_artist"] = mi["album_artist"]
            metadata["albumArtist"] = mi["album_artist"]

        if "album_performer" in mi:
            metadata["album_artist"] = mi["album_performer"]
            metadata["artist"] = mi["album_performer"]

        if "performer" in mi:
            metadata["artist"] = mi["performer"]

        if albumArtFilename:
            if httpObj:
                metadata["album_art_url"] = makeDownloadURL (httpObj, 'file', albumArtFilename)
            else:
                metadata["album_art_url"] = ''

            metadata["album_art_location"] = albumArtFilename
            metadata["album_art_location_type"] = "file"

        DB.StoreCachedMetadata(location, 'file', metadata)
    except Exception as e:
        logging.error(f"Failed loading meta data for {location} : exception {e}")

    return metadata


# =============== Chromecast Queue Processor ===============



chromecastProcesSleepInt = 0
exitQueueProcessing      = False
ChromeCastQueues         = {}
def chromecastQueueProcWakeNow ():
    global chromecastProcesSleepInt
    # logging.warning (f"chromecastQueueProcWakeNow @ {chromecastProcesSleepInt}")
    chromecastProcesSleepInt = 0

def chromecastQueueProcessing ():
    global ChromeCastQueues, exitQueueProcessing, chromecastProcesSleepInt

    qpbfl = GF.Config.getSettingValue('slinger/QUEUE_PROCESS_ACTIVE_BEFORE_SLEEP')
    qpaaw = GF.Config.getSettingValue('slinger/QUEUE_PROCESS_ACTIVE_AFTER_WAKE')
    qpsbw = GF.Config.getSettingValue('slinger/QUEUE_PROCESS_SLEEP_BEFORE_WAKE')

    activeLoopCount = qpaaw
    while (not exitQueueProcessing):
        devicesAreActive = False
        try:
            for cc in getCachedChromeCast():
                if not cc or isinstance(cc, pychromecast.discovery.CastBrowser): continue
                if cc[0].uuid not in ChromeCastQueues:
                    ChromeCastQueues[cc[0].uuid] = SlingerChromeCastQueue.SlingerChromeCastQueue (cc[0])

                ChromeCastQueues[cc[0].uuid].processStatusEvent()
                if ChromeCastQueues[cc[0].uuid].isDeviceActive():
                    devicesAreActive = True
                    activeLoopCount  = qpbfl # wait before going to low active mode
        except Exception as e:
            logging.error(f"chromecastQueueProcessing : {e}")
            logging.error(traceback.format_exc())

        # go into fast update mode if there are active devices, otherwise, slumber a bit
        if devicesAreActive or activeLoopCount > 0:
            chromecastProcesSleepInt = 1
            activeLoopCount          -= 1
        else:
            # delay some time, but keep awake for at least 30 seconds after coming out of sleep to allow chrome cast commands to complete.
            chromecastProcesSleepInt = qpsbw # sleep for a time or until awoken!
            activeLoopCount          = qpaaw
            logging.info (f"*** chromecastProcesSleepInt : sleep mode activated for {chromecastProcesSleepInt} secs, keep-alive after wake for {activeLoopCount} secs ***")

        # Go into low CPU mode...
        chromecastProcesSleepInt *= 2
        while chromecastProcesSleepInt > 0:
            time.sleep(0.5)
            chromecastProcesSleepInt -= 1
            # logging.warning (f'sleep left {chromecastProcesSleepInt} activeLoopCount {activeLoopCount}')

def getChromecastQueueObj (ccast_uuid):
    castQueueObj = None
    for key in ChromeCastQueues.keys():
        cqo = ChromeCastQueues[key]
        if str(cqo.cast.uuid) == ccast_uuid:
            return cqo
    return None

def GetTotalSeconds (timeDelta):
    try:
        return ((timeDelta.days * 24) * 3600) + timeDelta.seconds
    except:
        return 0

def scrapeMetaDataSMB (location, maxDepth=100, smbConn=None):
    global scrapeProcesState

    if not scrapeProcesState['active']:
        return

    if not validateSMBFileAccessLocation('smb', location):
        return

    try:
        _, _, server, shareName, filePath = parseSMBConfigString(location)
        if not smbConn:
            username, password = matchSMBCredentialsConfigString(location)
            conn = SMBConnection(username=username, password=password, my_name="", remote_name="", use_ntlm_v2=True)
            conn.connect(server)
        else:
            conn = smbConn

        scrapeProcesState['file_path'] = rtnNoPasswordSMBPath(location)

        for fattrib in (smb.SMBConnection.SMB_FILE_ATTRIBUTE_DIRECTORY,
                        smb.SMBConnection.SMB_FILE_ATTRIBUTE_INCL_NORMAL | smb.SMBConnection.SMB_FILE_ATTRIBUTE_ARCHIVE | smb.SMBConnection.SMB_FILE_ATTRIBUTE_READONLY | smb.SMBConnection.SMB_FILE_ATTRIBUTE_SYSTEM):
            flist = conn.listPath(service_name=shareName, path=filePath, search=fattrib)
            flist.sort(key=lambda x: x.filename)
            for file in flist:
                if file.filename in ('.', '..'):
                    continue

                full_path = rtnNoPasswordSMBPath(location).rstrip('\\') + '\\' + file.filename
                if file.isDirectory:
                    full_path += '\\'
                    if maxDepth > 0:
                        scrapeMetaDataSMB(location=full_path, maxDepth=maxDepth - 1, smbConn=conn)
                    continue

                if not scrapeProcesState['active']:
                    return

                scrapeProcesState['file_path'] = rtnNoPasswordSMBPath(location)

                # determine if this a somewhat supported file, and add to queue
                if getCastMimeType(file.filename, testForKnownExt=True) and (not DB.ExistMetadataCache (full_path, 'smb')):
                    scrapeProcesState['processing_filename'] = file.filename
                    getMediaMetaDataSMB(location=full_path, smbConn=smbConn)

                scrapeProcesState['processing_filename'] = ''

    except Exception as e:
        logging.error(f"{e} scrapeMetaDataSMB [2] Failed loading file @ {server}\\{shareName}\\{filePath}")
    finally:
        scrapeProcesState['file_path'] = scrapeProcesState['processing_filename'] = ''
        try:
            if not smbConn:
                conn.close()
        except:
            pass

def scrapeMetaDataFile (location, maxDepth=100):
    global scrapeProcesState

    if not scrapeProcesState['active']:
        return

    if not validateSMBFileAccessLocation('file', location):
        return

    try:
        scrapeProcesState['file_path'] = location

        fileList = []
        dList = [d for d in os.listdir(location) if os.path.isdir(location.rstrip(os.sep) + os.sep + d)]
        dList.sort()

        for d in dList:
            full_path = location.rstrip(os.sep) + os.sep + d
            if maxDepth > 0:
                scrapeMetaDataFile(location=full_path, maxDepth=maxDepth - 1)
                continue
            else:
                continue

        fList = [f for f in os.listdir(location) if os.path.isfile(location.rstrip(os.sep) + os.sep + f)]
        fList.sort()
        for f in fList:
            if not scrapeProcesState['active']:
                return

            full_path = location.rstrip(os.sep) + os.sep + f
            scrapeProcesState['file_path'] = location

            # determine if this a somewhat supported file, and add to queue
            if getCastMimeType(f, testForKnownExt=True) and (not DB.ExistMetadataCache (full_path, 'file')):
                scrapeProcesState['processing_filename'] = f
                getMediaMetaDataFile(location=full_path)
            scrapeProcesState['processing_filename'] = ''
    except Exception as e:
        logging.error(f"{e} scrapeMetaDataFile Failed loading file @ {location}")
    finally:
        scrapeProcesState['file_path'] = scrapeProcesState['processing_filename'] = ''

scrapeProcesState = {
    'next_process_event' : '',
    'active' : False,
    'file_path' : '',
    'processing_filename' : '',
    'metadata_num' : -1
}
def scraperProcess ():
    global scrapeProcesState
    if scrapeProcesState['active']:
        logging.info("scraperProcess:: scrapper is already running, exiting!")
        return
    try:
        scrapeProcesState['active'] = True
        for fileInfo in GF.Config.getSettingList('slinger/FILE_MUSIC_PATH'):
            logging.info(f"Starting to scrape @ {fileInfo}")
            scrapeMetaDataFile (location=fileInfo)

        for shareInfo in GF.Config.getSettingList('slinger/SMB_MUSIC_UNCPATH'):
            logging.info(f"Starting to scrape @ {shareInfo}")
            scrapeMetaDataSMB(location=shareInfo)
    except Exception as e:
        logging.error(f"scraperProcess : {str(e)}")
    finally:
        scrapeProcesState['active'] = False
        scrapeProcesState['file_path'] = scrapeProcesState['processing_filename'] = ''

# ===============================================================================

def searchDirectoriesSMB (location, regex, maxDepth=100, maxResultsLen=1000, resultsList=None, smbConn=None):
    global searchDirectoriesProcesState

    if not searchDirectoriesProcesState['active']:
        return resultsList

    if not resultsList:
        resultsList = []

    if not validateSMBFileAccessLocation('smb', location):
        return resultsList

    try:
        _, _, server, shareName, filePath = parseSMBConfigString(location)
        if not smbConn:
            username, password = matchSMBCredentialsConfigString(location)
            conn = SMBConnection(username=username, password=password, my_name="", remote_name="", use_ntlm_v2=True)
            conn.connect(server)
        else:
            conn = smbConn

        searchDirectoriesProcesState['file_path'] = rtnNoPasswordSMBPath(location)

        for fattrib in (smb.SMBConnection.SMB_FILE_ATTRIBUTE_DIRECTORY,
                        smb.SMBConnection.SMB_FILE_ATTRIBUTE_INCL_NORMAL | smb.SMBConnection.SMB_FILE_ATTRIBUTE_ARCHIVE | smb.SMBConnection.SMB_FILE_ATTRIBUTE_READONLY | smb.SMBConnection.SMB_FILE_ATTRIBUTE_SYSTEM):
            flist = conn.listPath(service_name=shareName, path=filePath, search=fattrib)
            flist.sort(key=lambda x: x.filename)
            for file in flist:
                if len(resultsList) >= maxResultsLen or not searchDirectoriesProcesState['active']:
                    return resultsList

                if file.filename in ('.', '..'):
                    continue

                full_path = rtnNoPasswordSMBPath(location).rstrip('\\') + '\\' + file.filename
                if file.isDirectory:
                    full_path += '\\'
                    if maxDepth > 0:
                        resultsList = searchDirectoriesSMB(location=full_path, regex=regex, maxDepth=maxDepth - 1, maxResultsLen=maxResultsLen, resultsList=resultsList, smbConn=conn)
                    continue

                if not searchDirectoriesProcesState['active']:
                    return resultsList

                searchDirectoriesProcesState['file_path'] = rtnNoPasswordSMBPath(location)

                # determine if this a somewhat supported file, and add to queue
                if (getCastMimeType(file.filename, testForKnownExt=True) and re.search(regex, full_path, re.IGNORECASE)):
                    searchDirectoriesProcesState['processing_filename'] = file.filename
                    searchDirectoriesProcesState['matched'] += 1
                    resultsList.append({'location': full_path, 'type' : 'smb', 'metadata' : getMediaMetaDataSMB(location=full_path) })

                searchDirectoriesProcesState['processing_filename'] = ''

    except Exception as e:
        logging.error(f"{e} searchDirectoriesSMB [2] Failed loading file @ {server}\\{shareName}\\{filePath}")
    finally:
        searchDirectoriesProcesState['file_path'] = searchDirectoriesProcesState['processing_filename'] = ''
        try:
            if not smbConn:
                conn.close()
        except:
            pass
    return resultsList

SearchSem = threading.Semaphore()

def searchDirectoriesFile (location, regex, maxDepth=100, maxResultsLen=1000, resultsList=None):
    global searchDirectoriesProcesState

    if not searchDirectoriesProcesState['active']:
        return resultsList

    if not resultsList:
        resultsList = []

    if not validateSMBFileAccessLocation('file', location):
        return resultsList

    try:
        searchDirectoriesProcesState['file_path'] = location

        fileList = []
        dList = [d for d in os.listdir(location) if os.path.isdir(location.rstrip(os.sep) + os.sep + d)]
        dList.sort()

        for d in dList:
            full_path = location.rstrip(os.sep) + os.sep + d
            if maxDepth > 0:
                resultsList = searchDirectoriesFile(location=full_path, regex = regex, maxDepth=maxDepth - 1, maxResultsLen=maxResultsLen, resultsList=resultsList)
                if len(resultsList) >= maxResultsLen or not searchDirectoriesProcesState['active']:
                    return resultsList
                continue
            else:
                continue

        fList = [f for f in os.listdir(location) if os.path.isfile(location.rstrip(os.sep) + os.sep + f)]
        fList.sort()
        for f in fList:
            if len(resultsList) >= maxResultsLen or not searchDirectoriesProcesState['active']:
                return resultsList

            if not searchDirectoriesProcesState['active']:
                return resultsList

            full_path = location.rstrip(os.sep) + os.sep + f
            searchDirectoriesProcesState['file_path'] = location

            # determine if this a somewhat supported file, and add to queue
            if getCastMimeType(f, testForKnownExt=True) and re.search(regex, full_path, re.IGNORECASE) :
                searchDirectoriesProcesState['processing_filename'] = f
                searchDirectoriesProcesState['matched'] += 1
                resultsList.append({'location': full_path, 'type': 'file', 'metadata': getMediaMetaDataFile(location=full_path)})
            searchDirectoriesProcesState['processing_filename'] = ''
    except Exception as e:
        logging.error(f"{e} scrapeMetaDataFile Failed loading file @ {location}")
    finally:
        searchDirectoriesProcesState['file_path'] = searchDirectoriesProcesState['processing_filename'] = ''
    return resultsList

searchDirectoriesProcesState = {
    'active' : False,
    'matched' : 0,
    'file_path' : '',
    'processing_filename' : ''
}
def AbortSearchDirectories ():
    global  searchDirectoriesProcesState
    searchDirectoriesProcesState['active'] = False
    logging.error("********** ABORT SEARCH *************")

def searchDirectoriesProcess (regex, maxResultsLen=1000):
    global searchDirectoriesProcesState, SearchSem
    results = []

    if not SearchSem.acquire(blocking=False):
        logging.warning(f"********** SEARCH FAILED BLOCKING! *************")
        return None

    try:
        logging.warning(f"********** STARTING SEARCH : {regex} *************")

        if searchDirectoriesProcesState['active']:
            logging.info("searchDirectoriesProcess:: directory search is already running, exiting!")
            return None

        searchDirectoriesProcesState['active'] = True
        searchDirectoriesProcesState['matched'] = 0
        for fileInfo in GF.Config.getSettingList('slinger/FILE_MUSIC_PATH'):
            logging.info(f"Starting to directory search @ {fileInfo}")
            results = searchDirectoriesFile (location=fileInfo, regex=regex, maxResultsLen=maxResultsLen, resultsList=results)

        for shareInfo in GF.Config.getSettingList('slinger/SMB_MUSIC_UNCPATH'):
            logging.info(f"Starting to directory search @ {shareInfo}")
            results = searchDirectoriesSMB (location=shareInfo, regex=regex, maxResultsLen=maxResultsLen, resultsList=results)
    except Exception as e:
        logging.error(f"searchDirectoriesProcess : {str(e)}")
    finally:
        SearchSem.release()
        searchDirectoriesProcesState['active'] = False
        searchDirectoriesProcesState['file_path'] = searchDirectoriesProcesState['processing_filename'] = ''
    return results


def cronScraperProcessing ():
    global exitQueueProcessing, scrapeProcesState
    while (not exitQueueProcessing):
        try:
            # Find the minimum next time from the cron settings
            eventTime = -1
            for s in GF.Config.getSettingList('slinger/SCRAPER_EVENT_TIME'):
                if not s:
                    break
                t = crontab.CronTab(s).next(default_utc=False)
                if (t < eventTime) or (eventTime == -1): eventTime = t

            # if no time schedule define!
            if eventTime < 0:
                scrapeProcesState['next_process_event'] = 'not configured'
                logging.warning("Exiting scraper process, no events defined!")
                break

            scrapeProcesState['next_process_event'] = f"event processing @ {(datetime.now() + timedelta(seconds=int(eventTime))).strftime('%c')}"

            logging.info(f"cronScraperProcessing:: next Event will occur @ {datetime.now() + timedelta(seconds=int(eventTime)) } or in {eventTime} seconds")
            time.sleep(int(eventTime))
            logging.info("cronScraperProcessing:: Event Fired")
            scrapeProcesState['next_process_event'] = 'running event'
            scraperProcess ()
            time.sleep(2)
        except Exception as e:
            logging.error(f"cronScraperProcessing! {e}")
            break

# ====================================================================


threading.Thread(target=chromecastQueueProcessing).start()
threading.Thread(target=cronScraperProcessing).start()