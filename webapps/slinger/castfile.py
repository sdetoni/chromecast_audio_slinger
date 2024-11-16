import logging
import slinger.SlingerGlobalFuncs as SGF
import urllib
import threading

self = eval('self'); output = self.output

postData = self.getCGIParametersFormData ()

if not "type"              in postData: postData["type"]              = ''
if not "location"          in postData: postData["location"]          = ''
if not "force_cast"        in postData: postData["force_cast"]        = ''
if not "directory_load"    in postData: postData["directory_load"]    = ''
if not "ccast_uuid"        in postData: postData["ccast_uuid"]        = ''
if not "max_recurse_depth" in postData: postData["max_recurse_depth"] = '100'
if not "max_queue_len"     in postData: postData["max_queue_len"]     = '1000'


castQueueObj = SGF.getChromecastQueueObj(postData["ccast_uuid"])
if not castQueueObj:
    logging.error(f"{postData['ccast_uuid']} cast object is not matched!")
    exit(0)

if not isinstance(postData["location"], list):
    postData["location"] = [ postData["location"] ]

def backgroundProcess ():
    for loc in postData["location"]:
        # if not location found, and there is a current media file loaded in chrome, then issue a play action.
        if (not loc) and (castQueueObj.cast.media_controller.status.content_id and castQueueObj.cast.media_controller.status.player_is_idle):
            output('ok')
            downloadURL = castQueueObj.cast.media_controller.status.content_id
            mimeType    = castQueueObj.cast.media_controller.status.content_type
            castQueueObj.cast.media_controller.play_media(downloadURL, content_type = mimeType, metadata =  castQueueObj.cast.media_controller.status.media_metadata)
            exit(0)

        # Decode possible unicode string
        loc = SGF.decode_percent_u(loc)

        if not SGF.validateSMBFileAccessLocation(postData["type"].lower(), loc):
            continue

        if postData["directory_load"] == 'true':
            if postData["type"] == 'smb':
                queueFileList = SGF.loadDirectoryQueueSMB(location=loc, maxDepth=int(postData["max_recurse_depth"]), maxQueueLen=int(postData["max_queue_len"]))
            elif postData["type"] == 'file':
                queueFileList = SGF.loadDirectoryQueueFile(location=loc, maxDepth=int(postData["max_recurse_depth"]), maxQueueLen=int(postData["max_queue_len"]))

            for qf in queueFileList:
                logging.info (f"castfile: dir_load : {qf['filename']}")
                if postData['force_cast'].lower() in ('y', 'yes', 'true', 'on'):
                    postData['force_cast'] = ''
                    castQueueObj.loadLocation(self, location=qf["full_path"], type = qf["type"], forcePlay = True)
                else:
                    castQueueObj.loadLocation(self, location=qf["full_path"], type = qf["type"], forcePlay = False)
            logging.info(f"castfile: dir_load: Process Events...")
            castQueueObj.processStatusEvent()
        else:
            if loc:
                if postData['force_cast'].lower() in ('y', 'yes', 'true', 'on'):
                    postData['force_cast'] = ''
                    castQueueObj.loadLocation(self, location=loc, type = postData["type"], forcePlay = True)
                else:
                    castQueueObj.loadLocation(self, location=loc, type = postData["type"], forcePlay = False)

        if (castQueueObj.playMode == 'stopped') and (len(castQueueObj.queue) > 0):
            castQueueObj.next()
            castQueueObj.processStatusEvent()

# Run this process in the background to give an immediate response  other the browser will send multiple
# requests if there is a long enough delay.
threading.Thread(target=backgroundProcess).start()
output('ok')