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

self = eval('self'); output = self.output

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

def processTranscoding (location, type): # return updatedLocation, updatedType, transcoded
    transCoded = False

    # determine if this file needs to be transcoded to FLAC, and update the source file location to the transcoded file location.
    if (SGF.getCastMimeType(location).lower() == SGF.AUDIO_TRANSCODE):
        fmExe = GF.Config.getSetting('slinger/TC_FFMPEG_EXE_OVERRIDE')
        if fmExe:
            FFMPEG_EXE = os.path.abspath(fmExe)
            logging.info(f"Using ffmpeg @ {FFMPEG_EXE}")
        else:
            FFMPEG_EXE = FFmpeg().get_ffmpeg_bin()

        # Create a temporary file for the transcoded output
        tmp_transfile = tempfile.NamedTemporaryFile(suffix='.' + GF.Config.getSetting('slinger/TC_FFMPEG_AUDIO_OUT_FORMAT', 'flac'), delete=False)

        # Use ffmpeg to convert .dsf to 24-bit 96kHz .flac
        ffmpeg_command = ([ FFMPEG_EXE,
                            "-y",  # overwrite without asking
                            "-i", location,
                            # Default 24-bit, 32-bit to FLAC
                            "-sample_fmt", GF.Config.getSetting('slinger/TC_FFMPEG_SAMPLE_FORMAT', "s32"),
                            "-ar", GF.Config.getSetting('slinger/TC_FFMPEG_SAMPLE_FREQ', "96000"),
                            "-c:a", GF.Config.getSetting('slinger/TC_FFMPEG_AUDIO_OUT_FORMAT', 'flac'),
                          ] + GF.Config.getSettingList('slinger/TC_FFMPEG_OTHER_AUDIO_CFG', '-compression_level 0') + [ tmp_transfile.name])
        subprocess.run (ffmpeg_command, check=True)
        location = tmp_transfile.name
        transCoded = True
    return location, type, transCoded

# ------------------------------------------------------------------------------------------------------

try:
    SGF.CUR_CONCURRENT_ACCESSFILE_NO += 1
    ########## SMB Network Send File ##########
    if postData["type"].lower() == 'smb' and postData["location"] != '':
        # read file locations
        _, _, server, shareName, filePath = SGF.parseSMBConfigString(postData["location"])
        username, password = SGF.matchSMBCredentialsConfigString (postData["location"])
        try:
            conn = SMBConnection(username=username, password=password, my_name="", remote_name="", use_ntlm_v2=True)
            assert conn.connect(server)

            # send file to destination
            transcoded = False
            try:
                file_attr = conn.getAttributes(shareName, filePath)
                try:
                    logging.info (f'{SGF.toASCII(postData["location"])} :: {str(file_attr) }')
                except:
                    pass

                scode = 200
                if fileStartPos > 0:
                    scode = 206

                ext = filePath.split('.')[-1].lower()
                src_tmpfile = tempfile.NamedTemporaryFile(suffix='.' + ext,delete=False)
                # src_tmpfile.name

                logging.info("Transferring SMB file ... ")
                file_attributes, _ = conn.retrieveFile(shareName, filePath, src_tmpfile)

                # transcode file if needed ...
                send_filepath, postData["type"], transcoded = processTranscoding(src_tmpfile.name, type=postData["type"])

                fObj = open(send_filepath, mode='rb')
                fObj.seek(0, io.SEEK_END)
                fileSize = fObj.tell()
                readLen = fileSize

                if fileEndPos > 0:
                    readLen = fileEndPos - fileStartPos
                fObj.seek(fileStartPos)
                ccfilename = re.sub(ext+'$', send_filepath.split('.')[-1].lower(), file_attr.filename)
                self.do_HEAD(mimetype=self.isMimeType(send_filepath), turnOffCache=False, statusCode=scode,
                             closeHeader=True,
                             otherHeaderDict={'Content-Disposition': f'attachment; filename="{ccfilename.encode("utf-8")}"',
                                              'Content-Range' : f'bytes {fileStartPos}-{readLen}/{fileSize}',
                                              'Content-Length' : str(readLen)})

                self.outputRaw(fObj.read(readLen))
            except Exception as e:
                self.do_HEAD(mimetype='application/octet-stream', turnOffCache=False, statusCode=404, closeHeader=True)
                logging.error(f"{e} [2] Failed loading file @ {server}\\{shareName}\\{filePath}")
                output(e)
            finally:
                try:
                    fObj.close()
                except:
                    pass

                try:
                    os.remove(src_tmpfile)
                except:
                    pass

                try:
                    # Clean up the temporary transcoded file
                    if transcoded and os.path.exists(send_filepath):
                        os.remove(send_filepath)
                except:
                    pass

        except Exception as e:
            self.do_HEAD(mimetype='application/octet-stream', turnOffCache=False, statusCode=404, closeHeader=True)
            logging.error(f"{e} [1] Failed loading file @ {server}\\{shareName}\\{filePath}")
            output(e)
        finally:
            conn.close()
    ########## Local File System Send File ##########
    elif postData["type"].lower() == 'file' and postData["location"] != '':
        # send file to destination
        transcoded = False
        try:
            scode = 200
            if fileStartPos > 0:
                scode = 206

            # transcode file if needed ...
            postData["location"],postData["type"],transcoded = processTranscoding (location=postData["location"], type=postData["type"])

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

            try:
                # Clean up the temporary transcoded file
                if transcoded and os.path.exists(postData["location"]):
                    os.remove(postData["location"])
            except:
                pass

finally:
    SGF.CUR_CONCURRENT_ACCESSFILE_NO -= 1