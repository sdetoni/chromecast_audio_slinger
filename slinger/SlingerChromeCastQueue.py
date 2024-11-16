import time
import daemon.GlobalFuncs as GF
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

        self.submittedQueueItem = None

        if playListName:
            self.loadPlaylist (httpObj=httpObj, playListName=playListName, mode = 'replace')

        self.processStatusEventInt           = 0
        self.processStatusEventIntKeepActive = 0

        self.activeBeforeSeleep = GF.Config.getSettingValue('slinger/QUEUE_PROCESS_ACTIVE_BEFORE_SLEEP')
        self.sleepBeforeWake    = GF.Config.getSettingValue('slinger/QUEUE_PROCESS_SLEEP_BEFORE_WAKE')

        self.haltProcEvents = False

        if self.cast:
            self.processStatusEvent(wakeNow=True)

    def _moveToTopQueueItem (self, idx):
        if idx >= len(self.queue):
            return False

        saveIdx = self.queue[idx]
        del self.queue[idx]
        self.queue.insert(0,saveIdx )
        return True

    def _prepNextQueueItem (self):
        if not self.shuffleActive or len(self.queue) <= 0:
            return

        # shuffle the next item with queue to queue item 0
        self._moveToTopQueueItem(random.randint(0, len(self.queue) - 1))

    def _playQueueItem (self, queueItem):
        if not queueItem:
            return;

        self.playing_uuid =  queueItem.metadata['slinger_uuid']
        self.thisQueueItem = queueItem
        self.cast.wait()
        self.cast.media_controller.play_media(self.thisQueueItem.downloadURL, self.thisQueueItem.mimeType, metadata=self.thisQueueItem.metadata, enqueue=False)

    def wakeNow (self):
        self.processStatusEventInt           = 0
        self.processStatusEventIntKeepActive = self.activeBeforeSeleep

    def processStatusEvent (self, wakeNow=False):
        if not self.cast:
            return

        if self.haltProcEvents:
            return

        if wakeNow:
            self.wakeNow()

        self.processStatusEventInt           -= 1
        self.processStatusEventIntKeepActive -= 1

        # logging.info (f"processStatusEventInt:{self.processStatusEventInt}  self.processStatusEventIntKeepActive:{self.processStatusEventIntKeepActive}")
        if (self.processStatusEventInt >= 0) and (self.processStatusEventIntKeepActive < 0) and self.playerStatus:
            self.playerStatus['slinger_sleeping_sec']     = self.processStatusEventInt
            self.chromeCastStatus['slinger_sleeping_sec'] = self.processStatusEventInt
            self.completeStatus['slinger_sleeping_sec']   = self.processStatusEventInt
            return

        def _myStatusCallback(chromeCastStatus):
            self.chromeCastStatus = chromeCastStatus

            # if not recently submitted queued item in the last 1 second (try and prevent race conditions), then allow it to continue
            if( (not self.submittedQueueItem) or ((datetime.datetime.now() - self.submittedQueueItem).total_seconds() >= 1.0)):
                # if no current playing file, then start one up....
                if (not self.chromeCastStatus['status']) and (self.playMode in ('auto')) and (len(self.queue) > 0):
                    self._prepNextQueueItem()
                    self._playQueueItem (self.queue[0])
                    self.delQueuedMediaItem(0)
                    logging.info (f"SlingerChromeCastQueue:: starting queued item {SGF.toASCII(str(self.thisQueueItem.metadata))}")
                    self.submittedQueueItem = datetime.datetime.now()
                # if there are more than one queued item in the list, then add the next one to the queue
                elif ((self.chromeCastStatus['status']) and
                      (self.chromeCastStatus['status'][0]['playerState'] in ('IDLE')) and
                      (self.playMode in ('auto')) and
                      (len(self.queue) > 0) and
                      self.queue[0].metadata['slinger_uuid'] != self.cast.media_controller.status.media_metadata['slinger_uuid']):
                    self._prepNextQueueItem()
                    self._playQueueItem (self.queue[0])
                    self.delQueuedMediaItem(0)
                    self.submittedQueueItem = datetime.datetime.now()
                    logging.info(f"SlingerChromeCastQueue:: playing first queued item {SGF.toASCII(str(self.thisQueueItem.metadata))}")
            else:
                logging.warning(f"SlingerChromeCastQueue:: queue playing code bypassed due to race conditions!")

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

            # set current sleep info
            self.playerStatus['slinger_sleeping_sec']     = self.processStatusEventInt
            self.chromeCastStatus['slinger_sleeping_sec'] = self.processStatusEventInt
            self.completeStatus['slinger_sleeping_sec']   = self.processStatusEventInt

        # ===================================================================

        # call get chromecast get status, it runs via a separate thread
        self.cast.wait()
        try:
            self.cast.media_controller.update_status(callback_function_param=_myStatusCallback)
        except Exception as e:
            logging.error(f'Failed chromecast status : {str(e)}')

            # update the chromecast cache, it a device may have gone offline!
            castList = SGF.getCachedChromeCast(force=True)

        self.lastUpated = datetime.datetime.now()

        if self.isDeviceActive():
            self.processStatusEventInt = 1
            self.processStatusEventIntKeepActive = self.activeBeforeSeleep
        elif self.processStatusEventIntKeepActive < 0: # go into select mode ...
            self.processStatusEventInt = self.sleepBeforeWake
            logging.warn(f"*** processStatusEvent : hibernate mode activated for {self.processStatusEventInt} secs ***")

    def delQueuedMediaItem(self, index = 0):
        if index >= len(self.queue):
            return
        del self.queue[index]
        self.queueChangeNo += 1

    def isDeviceActive (self):
        try:
            # The extended media status information.
            # It is used to broadcast additional player states
            # beyond the four main ones, namely
            # IDLE, PLAYING, PAUSED, and BUFFERING.
            # Currently it is used only to signal the initial loading of a media item.
            # In that case MediaStatus#playerState is IDLE,
            # but ExtendedMediaStatus#playerState is LOADING.

            if self.chromeCastStatus \
               and self.chromeCastStatus['status'] \
               and (self.chromeCastStatus['status'][0]['playerState'] in ('PLAYING', 'BUFFERING')):
                return True
        except:
            pass
        return False

    def prependQueueMediaItem (self,location, type, downloadURL, mimeType, metadata):
        self.queue.insert(0, SlingerQueueItem(location, type, downloadURL,mimeType,metadata))
        self.queueChangeNo += 1
        self.wakeNow()
    def appendQueueMediaItem (self,location, type, downloadURL, mimeType, metadata):
        self.queue.append(SlingerQueueItem(location, type, downloadURL,mimeType,metadata))
        self.queueChangeNo += 1
        self.wakeNow()

    def stop(self):
        self.playMode = 'stopped'
        self.cast.wait()
        self.cast.media_controller.stop()
        self.cast.wait()
        self.processStatusEvent(wakeNow=True)

    def next(self):
        if (len(self.queue) > 0):
            self.stop()
            self.playMode = 'auto'

    def seek(self, pos):
        self.cast.wait()
        self.cast.media_controller.seek(pos)
        self.cast.wait()
        self.processStatusEvent(wakeNow=True)

    def pause (self):
        self.cast.wait()
        self.cast.media_controller.pause()
        self.cast.wait()
        self.processStatusEvent(wakeNow=True)

    def play (self):
        try:
            slinger_uuid = self.chromeCastStatus['status'][0]['media']['metadata']['slinger_uuid']
        except:
            slinger_uuid = ''

        if slinger_uuid:
            self.cast.wait()
            self.cast.media_controller.play()
            self.cast.wait()
            self.wakeNow()
            self.playMode = 'auto'
        elif self.thisQueueItem:
            self.haltProcEvents = True
            self.playMode       = 'auto'
            self.queueChangeNo += 1
            self._playQueueItem(self.thisQueueItem)
            self.haltProcEvents = False
            self.processStatusEvent(wakeNow=True)
        else:
            self.next()

    def volume(self, level):
        self.cast.wait()
        self.cast.set_volume(level)
        self.cast.wait()
        self.processStatusEvent(wakeNow=True)

    def mute(self, muted):
        self.cast.wait()
        self.cast.set_volume_muted(muted)
        self.cast.wait()
        self.processStatusEvent(wakeNow=True)

    def clear (self):
        self.queue = []
        self.queueChangeNo += 1
        self.processStatusEvent(wakeNow=True)

    def shuffle (self, active):
        self.shuffleActive = active
        self.processStatusEvent(wakeNow=True)

    def playQueueItemAt (self, idx):
        self.haltProcEvents = True
        self.playMode = 'auto'
        qi = self.queue[idx]
        del self.queue[idx]
        self.queueChangeNo += 1
        self._playQueueItem(qi)
        self.haltProcEvents = False
        self.processStatusEvent(wakeNow=True)

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
            logging.info(f'Queuing (force play "{forcePlay}") item {SGF.toASCII(location)}')
        except:
            pass

        if forcePlay:
            self.haltProcEvents = True
            self.playMode = 'auto'
            self.queueChangeNo += 1
            self._playQueueItem(SlingerQueueItem(location=location, type=type, downloadURL=downloadURL, mimeType=SGF.getCastMimeType(location), metadata=metadata))
            self.haltProcEvents = False
            self.processStatusEvent(wakeNow=True)
        else:
            self.appendQueueMediaItem(location=location, type=type, downloadURL=downloadURL, mimeType=SGF.getCastMimeType(location), metadata=metadata)

    # mode : 'replace', 'append' playlist into queue
    def loadPlaylist (self, httpObj, playListName, mode):
        if not httpObj or not playListName:
            return
        try:
            self.haltProcEvents = True
            if mode == 'replace':
                self.stop()
                self.cast.wait()
                self.cast.wait()
                self.cast.wait()
                self.clear()

            for row in SGF.DB.GetPlayListSongs(playListName):
                self.loadLocation(httpObj=httpObj, location=row['location'], type=row['type'], forcePlay=False)

            if mode == 'replace':
                time.sleep(1)
                self.next()

            self.haltProcEvents = False
            self.processStatusEvent(wakeNow=True)
        finally:
            self.haltProcEvents = False
