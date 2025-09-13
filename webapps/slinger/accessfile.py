import glob
import re
import io
import logging
import os
import tempfile
import time
import subprocess
import threading
import daemon.GlobalFuncs as GF
from pyffmpeg import FFmpeg
from smb.SMBConnection import SMBConnection


import slinger.SlingerGlobalFuncs     as SGF
from pathlib import Path
import shutil
import hashlib

self    = eval('self'); output = self.output
postData = self.getCGIParametersFormData ()

if not "type"       in postData: postData["type"]       = ''
if not "location"   in postData: postData["location"]   = ''
if not "ccast_uuid" in postData: postData["ccast_uuid"] = ''

# dump headers
#logging.error ("*************************")
#for header in self.headers:
#    logging.warning (f"{header} : {self.headers[header]}")
#logging.error ("*************************")

fileStartPos = 0
fileEndPos   = -1
# parse file position header: Range : bytes=131072-
if 'Range' in self.headers:      
    pos   = self.headers['Range']
    parms = pos.split('=')
    if (len(parms) == 2) and (parms[0].lower() == 'bytes'):
        bpos = parms[1].split('-')
        try:
            fileStartPos = int(bpos[0])
            if len(bpos) == 2 and bpos[1].strip() != '':
                fileEndPos = int(bpos[1].strip())
        except:
            pass
    logging.debug (f"Range HEADER: {self.headers['Range']}")  
    logging.debug (f"Range fileStartPos {fileStartPos} fileEndPos {fileEndPos}")  

if not SGF.validateSMBFileAccessLocation(postData["type"].lower(), postData["location"]):
    output("no")
    exit(0)

#'''/***********
#HTTP/1.1 206 Partial Content
#Content-Range: bytes 0-1023/146515
#Content-Length: 1024
#**************/
#'''
# limit the number of con-current downloads to prevent DDOS type effect.
retry = 5
while SGF.CUR_CONCURRENT_ACCESSFILE_NO > SGF.MAX_CONCURRENT_ACCESSFILE_NO:
    retry -= 1
    if retry < 0:
        logging.error("TIMEOUT waiting for CUR_CONCURRENT_ACCESSFILE_NO.")
        logging.error(f"CUR_CONCURRENT_ACCESSFILE_NO = {SGF.CUR_CONCURRENT_ACCESSFILE_NO} MAX_CONCURRENT_ACCESSFILE_NO = {SGF.MAX_CONCURRENT_ACCESSFILE_NO}")
        exit(0)
    time.sleep(200)

logging.info(f"accessfile.py: CUR_CONCURRENT_ACCESSFILE_NO = {SGF.CUR_CONCURRENT_ACCESSFILE_NO} MAX_CONCURRENT_ACCESSFILE_NO = {SGF.MAX_CONCURRENT_ACCESSFILE_NO}")

def cacheStoreTranscoding (transcodedData, fileExt, origLocation):
    if len(transcodedData) <= 0:
        return

    cacheLoc = GF.Config.getSetting('slinger/TC_CACHE_LOCATION', '')
    if not cacheLoc:
        return
    if not Path(cacheLoc).is_dir():
        logging.error("Transcoding TC_CACHE_LOCATION is not a directory!")
        logging.error(f"'{GF.Config.getSetting('slinger/TC_CACHE_LOCATION')}' is invalid!")
        return

    # parse and convert to into byte size
    try:
        maxSizeCFG = GF.Config.getSetting('slinger/TC_CACHE_MAX_SIZE', '10MB')
        match = re.compile(r"(\d+)\s*([A-Za-z]+)*").match(maxSizeCFG)
        if not match:
            raise Exception("Parse error")
        cacheSize, cacheSizeUnit = match.groups()
        if cacheSizeUnit.lower() == 'tb':
            cacheSize = int(cacheSize) * (((1024*1024)*1024)*1024)
        elif cacheSizeUnit.lower() == 'gb':
            cacheSize = int(cacheSize) * ((1024*1024)*1024)
        elif cacheSizeUnit.lower() == 'mb':
            cacheSize = int(cacheSize) * (1024*1024)
        elif cacheSizeUnit.lower() == 'bb':
            cacheSize = int(cacheSize) * 1024
    except:
        cacheSize = 0

    if cacheSize <= 0:
        logging.error(f"Unexpected value for setting TC_CACHE_MAX_SIZE: {maxSizeCFG}")
        logging.error(f"Expected values for setting TC_CACHE_MAX_SIZE like 10MB 10TB 10MB 10KB etc")
        logging.error(f"Aborted cache store of transcoding")
        return

    logging.info(f"Transcoding Cache maxsize as : {maxSizeCFG} --> {cacheSize}")

    if len(transcodedData) > cacheSize:
        logging.warning(f"Transcoding is not able to fix in current max cache size for: {origLocation}")
        logging.warning(f"Transcoding size {len(transcodedData)} does not fit into {cacheSize}")
        return

    # read file location to determine used directory size, recursively
    dirUsageSize = sum(f.stat().st_size for f in Path(cacheLoc).rglob('*') if f.is_file())
    diskSizeInfo = shutil.disk_usage(cacheLoc)
    if (cacheSize-(diskSizeInfo.free) >= 0):
        logging.error(f"Cache max size exceeds the available disk size! disk size avail {diskSizeInfo.free} is less than cache max size {cacheSize}")
        logging.error(f"Reduce cache size or free up disk!")
        logging.error(f"Aborting storing this transcoding file!")
        return

    if dirUsageSize + len(transcodedData) > cacheSize:
        for file in sorted(glob.glob(cacheLoc + os.sep + '*'), key=os.path.getmtime):
            os.unlink(file)
            dirUsageSize = sum(f.stat().st_size for f in Path(cacheLoc).rglob('*') if f.is_file())
            if dirUsageSize + len(transcodedData) < cacheSize:
                break

    cacheFilename     = hashlib.sha256(origLocation.encode()).hexdigest() + '.' + fileExt
    cacheFullFilename = cacheLoc + os.sep + cacheFilename
    with open(cacheFullFilename, "wb") as cf:
        cf.write(transcodedData)

    # set the creation & modification time
    nowTime = time.time()
    os.utime(cacheFullFilename, (nowTime, nowTime))
    logging.info (f"Transcoding Cache wrote {origLocation} -> {cacheFullFilename} as {len(transcodedData)} bytes")

def cacheGetTranscode (location, ccast_uuid):
    cacheLoc = GF.Config.getSetting('slinger/TC_CACHE_LOCATION', '')
    if not cacheLoc:
        return
    if not Path(cacheLoc).is_dir():
        logging.error("Transcoding TC_CACHE_LOCATION is not a directory!")
        logging.error(f"'{GF.Config.getSetting('slinger/TC_CACHE_LOCATION')}' is invalid!")
        return

    cacheFileMatch = ''
    for file in glob.glob(cacheLoc + os.sep + hashlib.sha256(location.encode()).hexdigest() + '.*'):
        # update the change/modified file time for use in least recently used algorithm
        logging.info (f"Transcoded Cache file matched: {location}  -->  {file}")
        nowTime = time.time()
        os.utime(file, (nowTime, nowTime))
        SGF.getChromecastQueueObj(ccast_uuid=ccast_uuid).setTranscodingStatus('')
        return file
    return ''

# ------------------------------------------------------------------------------------------------------

class readerToHTTP:
    def __init__(self, httpObj=None):
        self.httpObj      = httpObj

    def write(self, data):
        self.httpObj.outputRaw(data)

    def close(self):
        pass

# ------------------------------------------------------------------------------------------------------

# NOTE! transcoding using name pipes DOES NOT work fully. The issue is not with the named pipes but how
# ffmpeg reads and generates its files. Input files are not just streamed in, but have random I/O with in the file to read meta-data.
# Output files from ffmpeg also have some level of re-write to the output file metadata (file size info etc). Thus, for a consistent trancoded output
# temporary files are used.
def processTranscoding (httpObj, ccast_uuid, location, type):
    if not location:
        return

    tmpTransCodeFile   = None
    tmpSrcLocationFile = None

    def cleanupTempfiles ():
        nonlocal tmpTransCodeFile, tmpSrcLocationFile
        # clean up temp files...
        if tmpTransCodeFile and os.path.exists(tmpTransCodeFile.name):
            try:
                tmpTransCodeFile.close()
                os.unlink(tmpTransCodeFile.name)
                tmpTransCodeFile = None
            except Exception as e:
                logging.error(f"Failed to remove temp transcoding file: {e}")

        if tmpSrcLocationFile and os.path.exists(tmpSrcLocationFile.name):
            try:
                tmpSrcLocationFile.close()
                os.unlink(tmpSrcLocationFile.name)
                tmpSrcLocationFile = None
            except Exception as e:
                logging.info(f"Failed to SMB src transcoding file: {e}")

    try:
        logging.info("Starting Transcoding...")

        fmExe = GF.Config.getSetting('slinger/TC_FFMPEG_EXE_OVERRIDE')
        if fmExe:
            FFMPEG_EXE = os.path.abspath(fmExe)
            logging.info(f"Using ffmpeg @ {FFMPEG_EXE}")
        else:
            FFMPEG_EXE = FFmpeg().get_ffmpeg_bin()

        if type == 'smb':
            # download file into a temporary file
            _, _, server, shareName, filePath = SGF.parseSMBConfigString(location)
            username, password                = SGF.matchSMBCredentialsConfigString(location)
            ccfilename                        = filePath.split(r'\\')[-1]
            srcExt                            = ccfilename.split('.')[-1].lower()
            tmpSrcLocationFile                = tempfile.NamedTemporaryFile(dir=SGF.getTempDirectoryLocation(), suffix='.' + srcExt, delete=False)

            # download source file
            try:
                conn = SMBConnection(username=username, password=password, my_name="", remote_name="", use_ntlm_v2=True)
                assert conn.connect(server)

                # send file to destination
                file_attr = conn.getAttributes(shareName, filePath)
                try:
                    logging.info(f'{SGF.toASCII(postData["location"])} :: {str(file_attr)}')
                except:
                    pass

                logging.info(f"Downloading {location}  --->  {tmpSrcLocationFile.name}")
                file_attributes, _ = conn.retrieveFile(shareName, filePath, tmpSrcLocationFile)
                logging.info("Finished SMB download")
                location = tmpSrcLocationFile.name
            finally:
                conn.close()

        elif type == 'file':
            filePath = location
            ccfilename = os.path.basename(filePath)

        tmpFileExt       = GF.Config.getSetting('slinger/TC_FFMPEG_AUDIO_OUT_FORMAT', 'flac')
        tmpTransCodeFile = tempfile.NamedTemporaryFile(dir=SGF.getTempDirectoryLocation(), suffix='.' + tmpFileExt, delete=False)

        # Use ffmpeg to convert .dsf to 24-bit 96kHz .flac
        ffmpeg_command = ([FFMPEG_EXE,
                           "-y",  # overwrite without asking
                           "-i", location,
                           # Default 24-bit, 32-bit to FLAC
                           "-sample_fmt", GF.Config.getSetting('slinger/TC_FFMPEG_SAMPLE_FORMAT', "s32"),
                           "-ar",         GF.Config.getSetting('slinger/TC_FFMPEG_SAMPLE_FREQ', "96000"),
                           "-c:a",        GF.Config.getSetting('slinger/TC_FFMPEG_AUDIO_OUT_FORMAT', 'flac'),
                           ] +            GF.Config.getSettingList('slinger/TC_FFMPEG_OTHER_AUDIO_CFG', '-compression_level 0') + [ tmpTransCodeFile.name]
                          )

        logging.info(ffmpeg_command)
        cco  = SGF.getChromecastQueueObj(ccast_uuid=ccast_uuid)
        proc = None
        try:
            #subprocess.run(ffmpeg_command, check=True)
            proc = subprocess.Popen(ffmpeg_command)

            # terminate any previous running transcoding, if any. There can (should) be only one!
            if cco:
                cco.killTranscodingProc()

            if cco:
                cco.setTranscodingProc(proc)

            # check if this process was abnormally terminated, if so, exit and don't return anything!
            rtnCode = proc.wait()
            if rtnCode != 0:
                logging.error(f"Exiting transcoding, return code: {rtnCode}")
                return

            # clear trancoding process obj
            if cco:
                cco.killTranscodingProc()

            transcodedData = b''
            with open(tmpTransCodeFile.name, 'rb') as file:
                    transcodedData = file.read()
        except subprocess.CalledProcessError as e:
            logging.error(f"Exiting transcoding, process error : {e}")
            return
        finally:
            if cco:
                if cco.transcodingProcess == proc:
                    cco.setTranscodingStatus('')
            cleanupTempfiles()

        # output transcode data as .flac
        # store this file in the cache... if it has been defined.
        threading.Thread(target=cacheStoreTranscoding, kwargs={'transcodedData':transcodedData, 'fileExt':tmpFileExt, 'origLocation':location}).start()

        ext        = ccfilename.split('.')[-1].lower()
        ccfilename = re.sub(ext + '$', tmpFileExt, ccfilename)
        httpObj.do_HEAD(mimetype=httpObj.isMimeType(ccfilename), turnOffCache=False, statusCode=200,
                        closeHeader=True,
                        otherHeaderDict={'Content-Disposition': f'attachment; filename="{ccfilename}"'})

        logging.info(f"Writing transcoded output of {len(transcodedData)} bytes")
        httpObj.outputRaw (transcodedData)
    finally:
        cleanupTempfiles()

def sendStandardFile (httpObj, location, fileStartPos, fileEndPos):
    # send file to destination
    try:
        scode = 206

        # read file to send to chromecast
        fObj = open(location, mode='rb')
        fObj.seek(0, io.SEEK_END)
        fileSize = fObj.tell()
        readLen = fileSize-1

        if fileEndPos > 0:
            readLen = fileEndPos - fileStartPos
            
        fObj.seek(fileStartPos)
        try:
            logging.info(f'Sending file @ location={SGF.toASCII(location)} :: filesize={fileSize}')
        except:
            pass

        # set response header
        httpObj.protocol_version = "HTTP/1.1"
        httpObj.do_HEAD(mimetype=httpObj.isMimeType(postData["location"]), turnOffCache=False, statusCode=scode, closeHeader=True,
                     otherHeaderDict={'Content-Disposition': f'attachment; filename="{os.path.basename(fObj.name).encode("utf-8")}"',
                                      'Content-Range': f'bytes {fileStartPos}-{readLen}/{fileSize}',
                                      'Content-Length': str(readLen)})

        logging.info(f"Transferring file @ :::: fileStartPos {fileStartPos}, fileEndPos {fileEndPos}, readLen {readLen} : filesize {fileSize} ")
        # write output
        chunkSize = 4096
        actualReadlen = readLen+1
        while True:
            if chunkSize > actualReadlen:
                chunkSize = actualReadlen
            chunk = fObj.read(chunkSize)
            if not chunk:
                break
            httpObj.outputRaw(chunk)
            actualReadlen -= len(chunk)
            if actualReadlen <= 0:
                break

    except Exception as e:
        httpObj.do_HEAD(mimetype='application/octet-stream', turnOffCache=False, statusCode=404, closeHeader=True)
        logging.error(f'{e} Failed loading file @ {SGF.toASCII(postData["location"])}')
        output(e)
    finally:
        try:
            fObj.close()
        except:
            pass

# ------------------------------------------------------------------------------------------------------

try:
    SGF.CUR_CONCURRENT_ACCESSFILE_NO += 1
    ########## SMB Network Send File ##########
    if (SGF.getCastMimeType(postData["location"]).lower() == SGF.AUDIO_TRANSCODE) and postData["location"] != '':
        filename = cacheGetTranscode(postData["location"], ccast_uuid=postData["ccast_uuid"])
        if not filename:
            processTranscoding(httpObj=self, ccast_uuid=postData["ccast_uuid"], location=postData["location"], type=postData["type"].lower())
        else:
            sendStandardFile(httpObj=self, location=filename,fileStartPos=fileStartPos, fileEndPos=fileEndPos)

    elif postData["type"].lower() == 'smb' and postData["location"] != '':
        # read file locations
        _, _, server, shareName, filePath = SGF.parseSMBConfigString(postData["location"])
        username, password = SGF.matchSMBCredentialsConfigString(postData["location"])
        try:
            conn = SMBConnection(username=username, password=password, my_name="", remote_name="")
            assert conn.connect(server)

            # send file to destination
            try:
                file_attr = conn.getAttributes(shareName, filePath)
                try:
                    logging.info(f'{SGF.toASCII(postData["location"])} :: {str(file_attr)}')
                except:
                    pass

                readLen  = file_attr.file_size - 1
                fileSize = file_attr.file_size
                scode    = 206
                    
                if fileEndPos > 0:
                    readLen = fileEndPos - fileStartPos                

                ccfilename = os.path.basename(filePath.split(r'\\')[-1])
                self.protocol_version = "HTTP/1.1"
                self.do_HEAD(mimetype=self.isMimeType(filePath.split('.')[-1].lower()), turnOffCache=False, statusCode=scode,
                             closeHeader=True,
                             otherHeaderDict={'Content-Disposition': f'attachment; filename="{ccfilename.encode("utf-8")}"',
                                              'Content-Range': f'bytes {fileStartPos}-{readLen}/{fileSize}',
                                              'Content-Length': str(readLen)})
                
                logging.info(f"Transferring SMB file @ fileStartPos {fileStartPos}, readLen {readLen} : filesize {fileSize} ")
                smbReader = readerToHTTP(httpObj=self)
                file_attributes, readFileSize = conn.retrieveFileFromOffset(shareName, filePath, smbReader, offset=fileStartPos, max_length=readLen+1)

            except Exception as e:
                self.do_HEAD(mimetype='application/octet-stream', turnOffCache=False, statusCode=404, closeHeader=True)
                logging.error(f"{e} [2] Failed loading file @ {server}\\{shareName}\\{filePath}")
                output(str(e))
        except Exception as e:
            self.do_HEAD(mimetype='application/octet-stream', turnOffCache=False, statusCode=404, closeHeader=True)
            logging.error(f"{e} [1] Failed loading file @ {server}\\{shareName}\\{filePath}")
            output(str(e))
        finally:
            conn.close()
    ########## Local File System Send File ##########
    elif postData["type"].lower() == 'file' and postData["location"] != '':
        sendStandardFile(httpObj = self, location = postData["location"],fileStartPos=fileStartPos, fileEndPos=fileEndPos)
finally:
    SGF.CUR_CONCURRENT_ACCESSFILE_NO -= 1
