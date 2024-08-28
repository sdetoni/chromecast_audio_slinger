import time
import threading
import slinger.SlingerGlobalFuncs as SGF
import logging
import urllib
import datetime
import random

class SlingerQueueItem:
    def __init__(self, location, type, downloadURL, mimeType, metadata):
        self.location    = location
        self.type        = type
        self.downloadURL = downloadURL
        self.mimeType    = mimeType
        self.metadata    = metadata

class SlingerChromeCastQueue:
    def __init__(self, cast, playListName='', httpObj=None):
        self.cast              = cast
        self.queueChangeNo     = 0
        self.queue             = []
        self.lastUpated        = datetime.datetime.now()
        self.playMode          = 'auto'
        self.shuffleActive     = False
        self.playing_uuid      = None

        self.playerStatus      = None
        self.chromeCastStatus  = None
        self.completeStatus    = None

        self.thisQueueItem     = None

        if playListName:
            self.loadPlaylist (httpObj=httpObj, playListName=playListName, mode = 'replace')

    def _prepNextQueueItem (self):
        if not self.shuffleActive or len(self.queue) <= 0:
            return

        # shuffle the next item with queue to queue item 0
        idx = random.randint(0, len(self.queue)-1)
        if idx <= 0:
            return

        save0 = self.queue[0]
        self.queue[0] = self.queue[idx]
        self.queue[idx] = save0

    def processStatusEvent (self):
        if not self.cast:
            return
        def _myStatusCallback(chromeCastStatus):

            self.chromeCastStatus = chromeCastStatus

            # if no current playing file, then start one up....
            if (not self.chromeCastStatus['status']) and (self.playMode in ('auto')) and (len(self.queue) > 0):
                self._prepNextQueueItem()
                self.thisQueueItem = self.queue[0]
                self.playing_uuid = self.thisQueueItem.metadata["slinger_uuid"]
                self.cast.wait()
                self.cast.media_controller.play_media(self.thisQueueItem.downloadURL, self.thisQueueItem.mimeType, metadata=self.thisQueueItem.metadata, enqueue=False)
                self.delQueuedMediaItem(0)
                logging.info (f"SlingerChromeCastQueue:: starting queued item {SGF.toASCII(str(self.thisQueueItem.metadata))}")
            # if there are more than one queued item in the list, then add the next one to the queue
            elif ((self.chromeCastStatus['status']) and
                  (self.chromeCastStatus['status'][0]['playerState'] in ('IDLE')) and
                  (self.playMode in ('auto')) and
                  (len(self.queue) > 0) and
                  self.queue[0].metadata['slinger_uuid'] != self.cast.media_controller.status.media_metadata['slinger_uuid']):

                self._prepNextQueueItem()
                self.playing_uuid = self.queue[0].metadata['slinger_uuid']
                self.thisQueueItem = self.queue[0]
                self.cast.wait()
                self.cast.media_controller.play_media(self.thisQueueItem.downloadURL, self.thisQueueItem.mimeType, metadata=self.thisQueueItem.metadata, enqueue=True)
                self.delQueuedMediaItem(0)

                logging.info(f"SlingerChromeCastQueue:: playing first queued item {SGF.toASCII(str(self.thisQueueItem.metadata))}")

            # logging.info (f"_myStatusCallback: {self.cast.uuid} callback completed \n {json.dumps(jsonData, indent=4)}")
            #if (("status" in chromeStatus) and (len(chromeStatus['status']) > 0)) and ("items" in chromeStatus['status'][0]):
            #    logging.info(f"_myStatusCallback: {self.cast.uuid} : Item Queue Number : {len(chromeStatus['status'][0]['items'])}")
            self.playerStatus = {
                'filename': (urllib.parse.unquote(self.cast.media_controller.status.content_id.split('location=')[-1]).split('\\')[-1] if self.cast.media_controller.status.content_id else ''),
                'title': self.cast.media_controller.status.title,
                'album_artist': self.cast.media_controller.status.album_artist,
                'album_name': self.cast.media_controller.status.album_name,
                'artist': self.cast.media_controller.status.artist,
                'content_type': self.cast.media_controller.status.content_type,
                'current_time': self.cast.media_controller.status.current_time,
                'duration': self.cast.media_controller.status.duration,
                'playback_rate': self.cast.media_controller.status.playback_rate,
                'playback_state': self.cast.media_controller.status.player_state,
                'volume_level': self.cast.status.volume_level,
                'volume_muted': self.cast.status.volume_muted,
                'supported_media_commands': self.cast.media_controller.status.supported_media_commands,
                'supports_pause': self.cast.media_controller.status.supports_pause,
                'supports_queue_next': self.cast.media_controller.status.supports_queue_next,
                'supports_queue_prev': self.cast.media_controller.status.supports_queue_prev,
                'supports_seek': self.cast.media_controller.status.supports_seek,
                'supports_skip_backward': self.cast.media_controller.status.supports_skip_backward,
                'supports_skip_forward': self.cast.media_controller.status.supports_skip_forward,
                'supports_stream_mute': self.cast.media_controller.status.supports_stream_mute,
                'supports_stream_volume': self.cast.media_controller.status.supports_stream_volume,
                'media_custom_data': self.cast.media_controller.status.media_custom_data,
                'media_metadata': self.cast.media_controller.status.media_metadata,
                'images': self.cast.media_controller.status.images,

                'slinger_queue_changeno': self.queueChangeNo,
                'slinger_shuffle':        self.shuffleActive,
                'slinger_current_media': { 'location' : '', 'type' : ''}
            }

            if self.thisQueueItem:
                self.playerStatus['slinger_current_media'] = {'location': self.thisQueueItem.location, 'type': self.thisQueueItem.type}

            self.completeStatus                             = self.playerStatus.copy()
            self.completeStatus['chrome_status']            = chromeCastStatus
            self.completeStatus['slinger_chromecast_queue'] = self.queue

        # ===================================================================

        # call get chromecast get status, it runs via a separate thread
        self.cast.wait()
        try:
            self.cast.media_controller.update_status(_myStatusCallback)
        except Exception as e:
            logging.error(f'Failed chromecast status : {str(e)}')

            # update the chromecast cache, it a device may have gone offline!
            castList = SGF.getCachedChromeCast(force=True)



        self.lastUpated = datetime.datetime.now()

    def delQueuedMediaItem(self, index = 0):
        if index >= len(self.queue):
            return
        del self.queue[index]
        self.queueChangeNo += 1

    def prependQueueMediaItem (self,location, type, downloadURL, mimeType, metadata):
        self.queue.insert(0, SlingerQueueItem(location, type, downloadURL,mimeType,metadata))
        self.queueChangeNo += 1

    def appendQueueMediaItem (self,location, type, downloadURL, mimeType, metadata):
        self.queue.append(SlingerQueueItem(location, type, downloadURL,mimeType,metadata))
        self.queueChangeNo += 1

    def stop(self):
        self.playMode = 'stopped'
        self.cast.wait()
        self.cast.media_controller.stop()
        self.cast.wait()

    def next(self):
        if (len(self.queue) > 0):
            self.stop()
            self.playMode = 'auto'

    def seek(self, pos):
        self.cast.wait()
        self.cast.media_controller.seek(pos)

    def pause (self):
        self.cast.wait()
        self.cast.media_controller.pause()

    def play (self):
        self.cast.wait()
        self.playMode = 'auto'
        self.cast.media_controller.play()

    def volume(self, level):
        self.cast.wait()
        self.cast.set_volume(level)
        self.cast.wait()
        self.processStatusEvent()

    def mute(self, muted):
        self.cast.wait()
        self.cast.set_volume_muted(muted)
        self.cast.wait()
        self.processStatusEvent()

    def clear (self):
        self.queue = []
        self.queueChangeNo += 1
        self.processStatusEvent()

    def shuffle (self, active):
        self.shuffleActive = active
        self.processStatusEvent()

    def saveToPlayList (self, playListName):
        playListName = playListName.strip()
        SGF.DB.DeletePlayList(playListName)
        SGF.DB.CreatePlayList(playListName)
        for q in self.queue:
            SGF.DB.AddPlayListSong(playListName, q.location, q.type)

    def loadLocation (self, httpObj, location, type, forcePlay):
        downloadURL = SGF.makeDownloadURL(httpObj=httpObj, type=type, location=location)

        if type == 'smb':
            metadata = SGF.getMediaMetaDataSMB(location, httpObj=httpObj)
        elif type == 'file':
            metadata = SGF.getMediaMetaDataFile(location, httpObj=httpObj)

        if not metadata:
            logging.error(f'loadLocation: Failed to get metadata for {downloadURL}, likely bad file access!')
            return False
        try:
            logging.info(f'Queuing item {location}')
        except:
            i = 1
            pass

        if forcePlay:
            self.prependQueueMediaItem(location=location, type=type, downloadURL=downloadURL, mimeType=SGF.getCastMimeType(location), metadata=metadata)
            self.stop()
            shuffleSave = self.shuffleActive
            self.shuffleActive = False
            self.next()
            self.processStatusEvent()
            self.shuffleActive = shuffleSave
        else:
            self.appendQueueMediaItem(location=location, type=type, downloadURL=downloadURL, mimeType=SGF.getCastMimeType(location), metadata=metadata)

    # mode : 'replace', 'append' playlist into queue
    def loadPlaylist (self, httpObj, playListName, mode):
        if not httpObj or not playListName:
            return

        if mode == 'replace':
            self.stop()
            self.clear()

        for row in SGF.DB.GetPlayListSongs(playListName):
            self.cast.wait()
            self.loadLocation(httpObj=httpObj, location=row['location'], type=row['type'], forcePlay=False)

        if mode == 'replace':
            self.next()

        self.processStatusEvent()
