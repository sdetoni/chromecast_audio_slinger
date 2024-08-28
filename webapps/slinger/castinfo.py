import slinger.SlingerGlobalFuncs as SGF
import json
import datetime
import pychromecast
import logging
import urllib
import uuid

self = eval('self'); output = self.output
postData = self.getCGIParametersFormData ()
if not "ccast_uuid" in postData: postData["ccast_uuid"] = ''
if not "type"       in postData: postData["type"]       = ''
if not "name"       in postData: postData["name"]       = ''


castQueueObj = SGF.getChromecastQueueObj (postData["ccast_uuid"])
if not castQueueObj:
    logging.error(f"{postData['ccast_uuid']} cast object is not matched!")
    exit(0)

if (datetime.datetime.now() - castQueueObj.lastUpated).seconds > 5:
    logging.error(f"{postData['ccast_uuid']} cast object update is out of sync and not updated in the last 5 seconds")

self.do_HEAD(mimetype='application/json', turnOffCache=False, statusCode=200, closeHeader=True)
if postData["type"] == "complete_status":
    output(json.dumps(castQueueObj.completeStatus, default=lambda o: o.__dict__, indent=4))
if postData["type"] == "chromecast_status":
    output(json.dumps(castQueueObj.chromeCastStatus, default=lambda o: o.__dict__, indent=4))
elif postData["type"] == "player_status":
    output(json.dumps(castQueueObj.playerStatus, default=lambda o: o.__dict__, indent=4))
elif postData["type"] == "queue_list":
    output(json.dumps(castQueueObj.queue, default=lambda o: o.__dict__, indent=4))

