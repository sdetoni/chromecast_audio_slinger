import re
import io
import logging
import os
import tempfile
import time
import subprocess
import daemon.GlobalFuncs as GF
from pyffmpeg import FFmpeg
from smb.SMBConnection import SMBConnection
import slinger.SlingerGlobalFuncs as SGF

self    = eval('self'); output = self.output
postData = self.getCGIParametersFormData ()

if not "type"     in postData: postData["type"]     = ''
if not "location" in postData: postData["location"] = ''

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

# ------------------------------------------------------------------------------------------------------

# NOTE! transcoding using name pipes DOES NOT work fully. The issue is not with the named pipes but how
# ffmpeg reads and generates its files. Input files are not just streamed in, but have random I/O with in the file to read meta-data.
# Output files from ffmpeg also have some level of re-write to the output file metadata (file size info etc). Thus, for a consistent trancoded output
# temporary files are used.
def processTranscoding (httpObj, location, type, fileStartPos, fileEndPos):
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

        tmpTransCodeFile = tempfile.NamedTemporaryFile(dir=SGF.getTempDirectoryLocation(), suffix='.' + GF.Config.getSetting('slinger/TC_FFMPEG_AUDIO_OUT_FORMAT', 'flac'), delete=False)

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
        subprocess.run(ffmpeg_command, check=True)

        ##################################################

        transcodedData = b''
        with open(tmpTransCodeFile.name, 'rb') as file:
                transcodedData = file.read()

        cleanupTempfiles()

        # output transcode data as .flac
        readLen  = len(transcodedData)
        fileSize = len(transcodedData)
        scode = 200
        if fileStartPos > 0:
            scode = 206

        if fileEndPos > 0:
            readLen = fileEndPos - fileStartPos

        ext        = ccfilename.split('.')[-1].lower()
        ccfilename = re.sub(ext + '$', 'flac', ccfilename)
        httpObj.do_HEAD(mimetype=httpObj.isMimeType(ccfilename), turnOffCache=False, statusCode=scode,
                        closeHeader=True,
                        otherHeaderDict={'Content-Disposition': f'attachment; filename="{ccfilename}"',
                                         'Content-Range': f'bytes {fileStartPos}-{readLen}/{fileSize}',
                                         'Content-Length': str(readLen)})

        if (fileStartPos > 0) or (readLen < fileSize):
            transcodedData = transcodedData[fileStartPos:readLen]

        logging.info(f"Writing transcoded output of {len(transcodedData)} bytes")
        httpObj.outputRaw (transcodedData)

    finally:
        cleanupTempfiles()

# ------------------------------------------------------------------------------------------------------

class readerToHTTP:
    def __init__(self, chunk_size=4096, fileStartPos=0, readLen=-1, httpObj=None):
        self.chunk_size = chunk_size
        self.httpObj      = httpObj
        self.fileStartPos = fileStartPos
        self.readLen      = readLen

    def write(self, data):
        if self.readLen == 0:
            return

        if self.fileStartPos > 0:
            if len(data) <= self.fileStartPos:
                self.fileStartPos -= len(data)
                return
            else:
                data = data[self.fileStartPos:]
                self.fileStartPos = 0

        if self.readLen == 0:
            return

        if self.readLen > 0:
            if len(data) > self.readLen:
                data = data[:self.readLen]
            self.readLen -= len(data)
        self.httpObj.outputRaw(data)

    def close(self):
        pass

# ------------------------------------------------------------------------------------------------------

try:
    SGF.CUR_CONCURRENT_ACCESSFILE_NO += 1
    ########## SMB Network Send File ##########
    if (SGF.getCastMimeType(postData["location"]).lower() == SGF.AUDIO_TRANSCODE) and postData["location"] != '':
        processTranscoding(httpObj=self, location=postData["location"], type=postData["type"].lower(), fileStartPos=fileStartPos, fileEndPos=fileEndPos)

    elif postData["type"].lower() == 'smb' and postData["location"] != '':
        # read file locations
        _, _, server, shareName, filePath = SGF.parseSMBConfigString(postData["location"])
        username, password = SGF.matchSMBCredentialsConfigString (postData["location"])
        try:
            conn = SMBConnection(username=username, password=password, my_name="", remote_name="", use_ntlm_v2=True)
            assert conn.connect(server)

            # send file to destination
            try:
                file_attr = conn.getAttributes(shareName, filePath)
                try:
                    logging.info (f'{SGF.toASCII(postData["location"])} :: {str(file_attr) }')
                except:
                    pass

                readLen  = file_attr.file_size
                fileSize = file_attr.file_size
                scode = 200
                if fileStartPos > 0:
                    scode = 206

                if fileEndPos > 0:
                    readLen = fileEndPos - fileStartPos

                ccfilename = filePath.split(r'\\')[-1]
                self.do_HEAD(mimetype=self.isMimeType(filePath.split('.')[-1].lower()), turnOffCache=False, statusCode=scode,
                             closeHeader=True,
                             otherHeaderDict={'Content-Disposition': f'attachment; filename="{ccfilename.encode("utf-8")}"',
                                              'Content-Range': f'bytes {fileStartPos}-{readLen}/{fileSize}',
                                              'Content-Length': str(readLen)})

                logging.info("Transferring SMB file ... ")

                smbReader = readerToHTTP (httpObj=self, fileStartPos=fileStartPos, readLen=readLen)
                file_attributes, _ = conn.retrieveFile(shareName, filePath, smbReader)

            except Exception as e:
                self.do_HEAD(mimetype='application/octet-stream', turnOffCache=False, statusCode=404, closeHeader=True)
                logging.error(f"{e} [2] Failed loading file @ {server}\\{shareName}\\{filePath}")
                output(e)
        except Exception as e:
            self.do_HEAD(mimetype='application/octet-stream', turnOffCache=False, statusCode=404, closeHeader=True)
            logging.error(f"{e} [1] Failed loading file @ {server}\\{shareName}\\{filePath}")
            output(e)
        finally:
            conn.close()
    ########## Local File System Send File ##########
    elif postData["type"].lower() == 'file' and postData["location"] != '':
        # send file to destination
        try:
            scode = 200
            if fileStartPos > 0:
                scode = 206

            # read file to send to chromecast
            fObj = open(postData["location"], mode='rb')
            fObj.seek(0, io.SEEK_END)
            fileSize = fObj.tell()
            readLen = fileSize

            if fileEndPos > 0:
                readLen = fileEndPos - fileStartPos
            fObj.seek(fileStartPos)
            try:
                logging.info (f'location={SGF.toASCII(postData["location"])} :: filesize={fileSize}')
            except:
                pass

            # set response header
            self.do_HEAD(mimetype=self.isMimeType (postData["location"]), turnOffCache=False, statusCode=scode, closeHeader=True,
                         otherHeaderDict= {'Content-Disposition' : f'attachment; filename="{os.path.basename(fObj.name).encode("utf-8")}"',
                                           'Content-Range' : f'bytes {fileStartPos}-{readLen}/{fileSize}',
                                           'Content-Length' : str(readLen)})

            # write output
            self.outputRaw(fObj.read(readLen))
        except Exception as e:
            self.do_HEAD(mimetype='application/octet-stream', turnOffCache=False, statusCode=404, closeHeader=True)
            logging.error(f'{e} Failed loading file @ {SGF.toASCII(postData["location"])}')
            output(e)
        finally:
            try:
                fObj.close()
            except:
                pass

finally:
    SGF.CUR_CONCURRENT_ACCESSFILE_NO -= 1
