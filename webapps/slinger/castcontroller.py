import logging
import slinger.SlingerGlobalFuncs as SGF
import threading
import json
import time
import pychromecast

self = eval('self'); output = self.output

postData = self.getCGIParametersFormData ()
if not "ccast_uuid" in postData: postData["ccast_uuid"] = ''
if not "action"     in postData: postData["action"]     = ''
if not "val1"       in postData: postData["val1"]       = ''

castQueueObj = SGF.getChromecastQueueObj(postData["ccast_uuid"])
if not castQueueObj:
    logging.error(f"{postData['ccast_uuid']} cast object is not matched!")
    exit(0)

if postData["action"] == "stop":
    castQueueObj.stop()
    output("stop")
elif postData["action"] == "queue_next":
    castQueueObj.next()
    output ("queue_next")
elif postData["action"] == "seek":
    castQueueObj.seek(int(postData["val1"]))
    output (f"seek {int(postData['val1'])}")
elif postData["action"] == "pause":
    castQueueObj.pause()
    output (f"pause")
elif postData["action"] == "play":
    castQueueObj.play()
    output (f"play")
elif postData["action"] == "mute":
    logging.info (f'mute { postData["val1"] }')
    castQueueObj.mute(postData["val1"].strip().lower() == 'true')
    output (f"mute {postData['val1']}")
elif postData["action"] == "volume":
    logging.info (f"Volume Level {castQueueObj.cast.status.volume_level}" )
    castQueueObj.volume(float(postData["val1"]))
    output(f"volume {float(postData['val1'])}")
elif postData["action"] == "shuffle":
    logging.info (f'shuffle { postData["val1"] }')
    castQueueObj.shuffle(postData["val1"].strip().lower() == 'true')
    output (f"shuffle {postData['val1']}")
elif postData["action"] == "queue_clear":
    castQueueObj.clear()
    output(f"queue_clear")
elif postData["action"] == "save_queue_to_playlist" and postData['val1'] != '':
    castQueueObj.saveToPlayList(postData['val1'])
    output(f"save_queue_to_playlist {postData['val1']}")
elif postData["action"] in ("play_playlist_replace", "play_playlist_append"):
    mode = 'replace'
    if postData["action"] == "play_playlist_append":
        mode = 'append'
    def bgloadPlaylist(httpObj, playListName, mode):
        castQueueObj.loadPlaylist(httpObj, playListName, mode)

    threading.Thread(target=bgloadPlaylist, args=(self,postData['val1'], mode)).start()
    output(f"{postData['action']} {postData['val1']}")
elif (postData["action"] == 'clear_metadata_cache'):
    SGF.DB.ClearMetadataCache()
    output("ok")
elif (postData["action"] == 'play_queued_item_at_index'):
    castQueueObj.playQueueItemAt(int(postData['val1']))
    output("ok")
elif (postData["action"] == 'stop_metadata_scraper'):
    if SGF.scrapeProcesState['active']:
        SGF.scrapeProcesState['active'] = False
        time.sleep(1)
    SGF.scrapeProcesState['metadata_num'] = SGF.DB.CountMetadataCache()
    output(json.dumps(SGF.scrapeProcesState, default=lambda o: o.__dict__, indent=4))
elif (postData["action"] == 'status_metadata_scraper'):
    SGF.scrapeProcesState['metadata_num'] = SGF.DB.CountMetadataCache()
    output(json.dumps(SGF.scrapeProcesState, default=lambda o: o.__dict__, indent=4))
elif (postData["action"] == 'start_metadata_scraper'):
    if not SGF.scrapeProcesState['active']:
        threading.Thread(target=SGF.scraperProcess).start()
        time.sleep(1)
    SGF.scrapeProcesState['metadata_num'] = SGF.DB.CountMetadataCache()
    output(json.dumps(SGF.scrapeProcesState, default=lambda o: o.__dict__, indent=4))
elif (postData["action"] == 'get_artwork_files'):

    pass

#requested_volume = float(sys.argv[1]) if len(sys.argv) > 1 else None
#if requested_volume != None:
#    cast.set_volume(requested_volume)
#else:
#    print cast.status.volume_level