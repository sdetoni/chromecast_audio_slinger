import slinger.SlingerGlobalFuncs as SGF
import json
import datetime
import pychromecast
import logging
import urllib
import uuid

self = eval('self'); output = self.output

# enter web socket receive/response loop ...
while True:
    try:
        msg = self.ws_WaitMessage()
    except:
        exit(-1)

    try:
        logging.debug (f"ws_castinfo msg: {msg}")
        postData = json.loads(msg)
    except Exception as e:
        logging.error(f"Error Parsing ws_castinfo request : { e }")
        continue

    if not "ccast_uuid" in postData: postData["ccast_uuid"] = ''
    if not "type"       in postData: postData["type"]       = ''
    if not "name"       in postData: postData["name"]       = ''

    castQueueObj = SGF.getChromecastQueueObj (ccast_uuid=postData["ccast_uuid"])
    if not castQueueObj:
        logging.error(f"{postData['ccast_uuid']} cast object is not matched!")
        continue

    if castQueueObj.isDeviceActive() and (datetime.datetime.now() - castQueueObj.lastUpated).seconds > 5:
        logging.error(f"{postData['ccast_uuid']} cast object update is out of sync and not updated in the last 5 seconds")

    info = { }
    if postData["type"] == "queue_list":
        info = {
                   "type": postData["type"],
                   "data": castQueueObj.queue
               }
    elif postData["type"] == "previous_queue_list":
        info = {
                    "type": postData["type"],
                    "data": castQueueObj.previousQueue
               }
    elif postData["type"] == "complete_status":
        info = {
                    "type" : postData["type"],
                    "data"         : castQueueObj.completeStatus
               }
    elif postData["type"] == "chromecast_status":
        info = {
                    "type" : postData["type"],
                    "data"         : castQueueObj.chromeCastStatus
               }
    elif postData["type"] == "player_status":
        info = {
                    "type" : postData["type"],
                    "data"         : castQueueObj.playerStatus
               }

    output(json.dumps(info, default=lambda o: o.__dict__, indent=4))
