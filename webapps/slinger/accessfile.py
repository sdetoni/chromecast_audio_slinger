import logging
import io
import daemon.GlobalFuncs         as GF
import slinger.SlingerGlobalFuncs as SGF
from smb.SMBConnection import SMBConnection
import tempfile

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

if postData["type"].lower() == 'smb' and postData["location"] != '':
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

            scode = 200
            if fileStartPos > 0:
                scode = 206

            file_obj = tempfile.NamedTemporaryFile()
            file_attributes, fileSize = conn.retrieveFile(shareName, filePath, file_obj)
            readLen = fileSize
            file_obj.seek(fileStartPos)
            if fileEndPos > 0:
                readLen = fileEndPos - fileStartPos
            f = SGF.toASCII(file_attr.filename)

            self.do_HEAD(mimetype=self.isMimeType(postData["location"]), turnOffCache=False, statusCode=scode,
                         closeHeader=True,
                         otherHeaderDict={'Content-Disposition': f'attachment; filename="{f}"',
                                          'Content-Range' : f'bytes {fileStartPos}-{readLen}/{fileSize}',
                                          'Content-Length' : str(readLen)})

            self.outputRaw(file_obj.read(readLen))
        except Exception as e:
            self.do_HEAD(mimetype='application/octet-stream', turnOffCache=False, statusCode=404, closeHeader=True)
            logging.error(f"{e} [2] Failed loading file @ {server}\\{shareName}\\{filePath}")
            output(e)
        finally:
            try:
                file_obj.close()
            except:
                pass
    except Exception as e:
        self.do_HEAD(mimetype='application/octet-stream', turnOffCache=False, statusCode=404, closeHeader=True)
        logging.error(f"{e} [1] Failed loading file @ {server}\\{shareName}\\{filePath}")
        output(e)
    finally:
        conn.close()
elif postData["type"].lower() == 'file' and postData["location"] != '':
    # send file to destination
    try:
        scode = 200
        if fileStartPos > 0:
            scode = 206

        fObj = open(postData["location"], mode='rb')
        fObj.seek(0, io.SEEK_END)
        fileSize = fObj.tell()
        readLen = fileSize
        if fileEndPos > 0:
            readLen = fileEndPos - fileStartPos
        fObj.seek(fileStartPos)
        try:
            logging.info (f'{SGF.toASCII(postData["location"])}')
        except:
            pass

        self.do_HEAD(mimetype=self.isMimeType (postData["location"]), turnOffCache=False, statusCode=scode, closeHeader=True,
                     otherHeaderDict= {'Content-Disposition' : f'attachment; filename="{fObj.name}"',
                                       'Content-Range' : f'bytes {fileStartPos}-{readLen}/{fileSize}',
                                       'Content-Length' : str(readLen)})
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
