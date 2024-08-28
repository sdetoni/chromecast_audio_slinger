import logging
import daemon.GlobalFuncs         as GF
import slinger.SlingerGlobalFuncs as SGF
from smb.SMBConnection import SMBConnection
import tempfile

self = eval('self'); output = self.output

postData = self.getCGIParametersFormData ()

if not "type"     in postData: postData["type"]     = ''
if not "location" in postData: postData["location"] = ''

if not SGF.validateSMBFileAccessLocation(postData["type"].lower(), postData["location"]):
    output("no")
    exit(0)

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

            file_obj = tempfile.NamedTemporaryFile()
            file_attributes, filesize = conn.retrieveFile(shareName, filePath, file_obj)
            file_obj.seek(0)
            f = SGF.toASCII(file_attr.filename)

            self.do_HEAD(mimetype=self.isMimeType(postData["location"]), turnOffCache=False, statusCode=200,
                         closeHeader=True,
                         otherHeaderDict={'Content-Disposition': f'attachment; filename="{f}"'})
            self.outputRaw(file_obj.read())
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
        fObj = open(postData["location"], mode='rb')

        try:
            logging.info (f'{SGF.toASCII(postData["location"])}')
        except:
            pass


        self.do_HEAD(mimetype=self.isMimeType (postData["location"]), turnOffCache=False, statusCode=200, closeHeader=True,
                     otherHeaderDict= {'Content-Disposition' : f'attachment; filename="{fObj.name}"'})
        self.outputRaw(fObj.read())
    except Exception as e:
        self.do_HEAD(mimetype='application/octet-stream', turnOffCache=False, statusCode=404, closeHeader=True)
        logging.error(f'{e} Failed loading file @ {SGF.toASCII(postData["location"])}')
        output(e)
    finally:
        try:
            fObj.close()
        except:
            pass
