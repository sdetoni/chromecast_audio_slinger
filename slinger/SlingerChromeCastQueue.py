import copy
import time
import daemon.GlobalFuncs as GF
import slinger.SlingerGlobalFuncs as SGF
import logging
import urllib
import datetime
import random
import threading
import pathlib
import slinger.nanodlna.dlna as dlna

TRANSCODING='transcoding'

class SlingerQueueItem:
    def __init__(self, location, type, downloadURL, mimeType, metadata):
        self.location    = location
        self.type        = type
        self.downloadURL = downloadURL
        self.mimeType    = mimeType
        self.metadata    = metadata

# ===========================================================================================

class SlingerChromeCastQueue:
    def __init__(self, cast, playListName='', httpObj=None):
        self.cast              = cast
        self.queueChangeNo     = 0
        self.queue             = []
        self.lastUpated        = datetime.datetime.now()
        self.playMode          = 'auto'
        self.comms_state       = 'OK'
        self.shuffleActive     = False
        self.playing_uuid      = None

        self.playerStatus      = None
        self.chromeCastStatus  = {}
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

        self.transcodingStatus  = ''
        self.transcodingProcess = None

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
            return

        self.playing_uuid  = queueItem.metadata['slinger_uuid']
        self.thisQueueItem = queueItem

        # test if this a transcoding type, set the current status early for chromecast devices as status reqs are usually blocked once casting starts
        if self.thisQueueItem.mimeType.lower() in (SGF.AUDIO_TRANSCODE,):
            self.setTranscodingStatus(status=TRANSCODING)
            self.playerStatus['slinger_current_media']['location'] = self.thisQueueItem.location
            self.playerStatus['slinger_current_media']['type']     = self.thisQueueItem.type


        self.cast.wait()
        self.cast.media_controller.play_media(self.thisQueueItem.downloadURL, self.thisQueueItem.mimeType, metadata=self.thisQueueItem.metadata, enqueue=False)

    def setTranscodingStatus (self, status):
        self.transcodingStatus = status
        self.playerStatus['slinger_current_media']['transcoding'] = status

    def setTranscodingProc(self, proc):
        self.transcodingProcess = proc
        self.setTranscodingStatus(status=TRANSCODING)

    def killTranscodingProc(self):
        proc = self.transcodingProcess
        self.transcodingProcess = None
        self.setTranscodingStatus('')

        # if process is still running!
        if (proc) and (not proc.poll()):
            try:
                logging.warning(f"Terminating transcoding process: {proc}")
                proc.kill()
            except:
                pass

    def wakeNow (self):
        self.processStatusEventInt           = 0
        self.processStatusEventIntKeepActive = self.activeBeforeSeleep
        if isinstance(self.cast, SlingerLocalPlayer):
            self.cast.wakeNow()

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
            if not chromeCastStatus:
                return

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
                'filename': (urllib.parse.unquote(self.cast.media_controller.status.content_id.split('location=')[-1]).split('&')[0].split('\\')[-1] if self.cast.media_controller.status.content_id else ''),
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
                'slinger_current_media': { 'location' : '', 'type' : '', 'transcoding': ''}
            }

            if self.thisQueueItem:
                self.playerStatus['slinger_current_media']['location']     = self.thisQueueItem.location
                self.playerStatus['slinger_current_media']['type']         = self.thisQueueItem.type

            self.playerStatus['slinger_current_media']['transcoding']  = self.transcodingStatus

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
            self.comms_state = 'OK'
        except Exception as e:
            logging.error(f'Failed chromecast status : {str(e)}')

            # update the chromecast cache, it a device may have gone offline!
            if self.comms_state == 'OK':
                self.comms_state = 'FAILED'
                castList = SGF.getCachedChromeCast(force=True)

        self.lastUpated = datetime.datetime.now()

        if self.isDeviceActive():
            self.processStatusEventInt = 1
            self.processStatusEventIntKeepActive = self.activeBeforeSeleep
        elif self.processStatusEventIntKeepActive < 0: # go into select mode ...
            self.processStatusEventInt = self.sleepBeforeWake
            logging.warning(f"*** processStatusEvent : hibernate mode activated for {self.processStatusEventInt} secs ***")

    def delQueuedMediaItem(self, index = 0):
        if index >= len(self.queue):
            return
        del self.queue[index]
        self.queueChangeNo += 1
        self.wakeNow()

    def isDeviceActive (self):
        try:
            # The extended media status information.
            # It is used to broadcast additional player states
            # beyond the four main ones, namely
            # IDLE, PLAYING, PAUSED, and BUFFERING.
            # Currently, it is used only to signal the initial loading of a media item.
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
        # do not HTTPS download link as the cert is likely self-signed in this type application!
        downloadURL = SGF.makeDownloadURL(httpObj=httpObj, type=type, location=location, chromecastHTTPDownland=True, ccast_uuid=str(self.cast.uuid))

        metadata = None
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
        return True

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

# ===========================================================================================

class SlingerLocalPlayer:
    class FakeMediaController:
        def __init__(self):
            self.qparent = None
            self.playback_state = 'UNKNOWN'

        def play_media(self, *args, **kwargs):
            self.playback_state = 'PLAYING'
            pass

        def stop (self, *args, **kwargs):
            self.playback_state = 'IDLE'
            pass

        def seek (self, pos):
            pass

        def pause (self, *args, **kwargs):
            self.playback_state = 'PAUSED'
            pass

        def update_status (self, callback_function_param):
            if not callback_function_param or not self.qparent:
                return

            def _dummyCallback():
                time.sleep(0.2)

                # if not recently submitted queued item in the last 1 second (try and prevent race conditions), then allow it to continue
                if ((not self.qparent.submittedQueueItem) or ((datetime.datetime.now() - self.qparent.submittedQueueItem).total_seconds() >= 1.0)):
                    # if no current playing file, then start one up....
                    if (self.playback_state in ('IDLE') and (self.qparent.playMode in ('auto')) and (len(self.qparent.queue) > 0)):
                        self.qparent._prepNextQueueItem()
                        self.qparent._playQueueItem(self.qparent.queue[0])
                        self.qparent.delQueuedMediaItem(0)
                        logging.info(f"SlingerChromeCastQueue:: starting queued item {SGF.toASCII(str(self.qparent.thisQueueItem.metadata))}")
                        self.qparent.submittedQueueItem = datetime.datetime.now()
                else:
                    logging.warning(f"SlingerChromeCastQueue:: queue playing code bypassed due to race conditions!")

                self.qparent.playerStatus = {
                    'filename':     self.qparent.thisQueueItem.location.split('&')[0].split('\\')[-1] if self.qparent.thisQueueItem else '',
                    'title':        self.qparent.thisQueueItem.metadata['title']        if self.qparent.thisQueueItem else '',
                    'album_artist': self.qparent.thisQueueItem.metadata['albumArtist']  if self.qparent.thisQueueItem else '',
                    'album_name':   self.qparent.thisQueueItem.metadata['albumName']    if self.qparent.thisQueueItem else '',
                    'artist':       self.qparent.thisQueueItem.metadata['artist']       if self.qparent.thisQueueItem else '',
                    'content_type': self.qparent.thisQueueItem.mimeType                 if self.qparent.thisQueueItem else '',
                    'current_time': -1,
                    'duration': -1,
                    'playback_rate': -1,
                    'playback_state': self.playback_state,
                    'volume_level': self.qparent.cast.status.volume_level,
                    'volume_muted': self.qparent.cast.muted,
                    'supported_media_commands': None,
                    'supports_pause': True,
                    'supports_queue_next': True,
                    'supports_queue_prev': False,
                    'supports_seek': True,
                    'supports_skip_backward': False,
                    'supports_skip_forward': False,
                    'supports_stream_mute': True,
                    'supports_stream_volume': True,
                    'media_custom_data': False,
                    'media_metadata': self.qparent.thisQueueItem.metadata if self.qparent.thisQueueItem else '',
                    'images': None,

                    'slinger_queue_changeno': self.qparent.queueChangeNo,
                    'slinger_shuffle': self.qparent.shuffleActive,
                    'slinger_current_media': {'location': '', 'type': '', 'transcoding': ''},
                    'slinger_sleeping_sec':0,
                }

                if self.qparent.thisQueueItem:
                    self.qparent.playerStatus['slinger_current_media']['location']    = self.qparent.thisQueueItem.location
                    self.qparent.playerStatus['slinger_current_media']['type']        = self.qparent.thisQueueItem.type

                self.qparent.playerStatus['slinger_current_media']['transcoding'] = self.qparent.transcodingStatus

                self.qparent.completeStatus = self.qparent.playerStatus.copy()
                self.qparent.completeStatus['slinger_chromecast_queue'] = self.qparent.queue

                callback_function_param(None)

            # use a delayed callback to handle variable synchronisation issue.
            threading.Thread(target=_dummyCallback).start()

    class FakeCast:
        pass

    # -==============================================-

    def __init__(self, uuid=SGF.LOCAL_PLAYER):
        self.uuid_unique_instance = None
        self.media_controller     = SlingerLocalPlayer.FakeMediaController()
        self.uuid                 = uuid

        self.cast                 = SlingerLocalPlayer.FakeCast()
        self.cast.uuid            = uuid

        self.chromeCastStatus     = { }
        self.cast_info            = SlingerLocalPlayer.FakeCast()
        self.cast_info.host       = 'LOCAL_PLAYER'

        self.status               = SlingerLocalPlayer.FakeCast()
        self.status.volume_level  = 1.0
        self.muted                = False

    def wakeNow (self):
        def ignoreCallback (p):
            pass
        self.media_controller.update_status(ignoreCallback)
    def queueParent (self, qp):
        self.qparent = qp
        self.media_controller.qparent = qp
        self.wakeNow()

    def wait (self):
        pass

    def set_volume(self, level):
        self.status.volume_level = level

    def set_volume_muted (self, muted):
        self.muted = muted

# ===========================================================================================

class SlingerDLNAPlayer:
    class FakeMediaController:
        def __init__(self):
            self.qparent = None
            self.playback_state = 'UNKNOWN'

        def play_media(self, *args, **kwargs):
            if (self.playback_state in 'PAUSED'):
                dlna.resume(self.qparent.cast.dlna_dev)
                self.playback_state = 'PLAYING'
            else:
                self.stop()
                #files_urls= {"file_video" : args[0], "type_video" : args[1]}
                #dlna.play (files_urls, self.qparent.cast.dlna_dev)
                idHash = SGF.DB.GetIDHash(self.qparent.thisQueueItem.location)
                md = SGF.DB.GetCachedMetadataByIDHash(idHash)
                # parse 'http://192.168.20.16:8008/slinger/accessfile.py?type=file&location=D%3A%5Cmusic%5Csdm.wav&ccast_uuid=c37fc1cc-d384-5748-a1db-750f22c6d7c1
                # into http://192.168.20.16:8008/slinger
                # and build hased url as urls with ?parameters will fail the DLNA parsing on some devices, so encode them into a HASH ID type url like:
                #    http://192.168.20.16:8008/slinger/DLHASH_d4e5991d75f6908206babd5a55f9695d99150e9f4f01b6630a442fa2e74c1551.flac
                #    http://192.168.20.16:8008/slinger/DLHASH_ART_d4e5991d75f6908206babd5a55f9695d99150e9f4f01b6630a442fa2e74c1551.jpg
                url     = f"{args[0].split('?')[0].rsplit('/', 1)[0]}/DLHASH_{idHash}{pathlib.Path(self.qparent.thisQueueItem.location).suffix}"
                art_url = self.qparent.thisQueueItem.metadata["album_art_location"]
                if art_url:
                    art_url = f"{args[0].split('?')[0].rsplit('/', 1)[0]}/DLHASH_ART_{idHash}{pathlib.Path(art_url).suffix}"

                dlna.play(self.qparent.cast.dlna_dev, url=url, mime_type=args[1], title=kwargs["metadata"]["title"], creator=kwargs["metadata"]["artist"], album=kwargs["metadata"]["album_name"], art_url=art_url)
                self.playback_state = 'PLAYING'

        def stop (self, *args, **kwargs):
            self.playback_state = 'IDLE'
            dlna.stop(self.qparent.cast.dlna_dev)

        def seek (self, pos):
            self.playback_state = 'IDLE'
            dlna.seek(self.qparent.cast.dlna_dev, pos)

        def pause (self, *args, **kwargs):
            self.playback_state = 'PAUSED'
            dlna.pause(self.qparent.cast.dlna_dev)

        def update_status (self, callback_function_param):
            if not callback_function_param or not self.qparent:
                return

            if self.qparent.haltProcEvents:
               return

            self.qparent.processStatusEventInt           -= 1
            self.qparent.processStatusEventIntKeepActive -= 1

            # logging.info (f"processStatusEventInt:{self.processStatusEventInt}  self.processStatusEventIntKeepActive:{self.processStatusEventIntKeepActive}")
            if (self.qparent.processStatusEventInt >= 0) and (self.qparent.processStatusEventIntKeepActive < 0) and self.qparent.playerStatus:
                self.qparent.playerStatus['slinger_sleeping_sec'] = self.qparent.processStatusEventInt
                self.qparent.chromeCastStatus['slinger_sleeping_sec'] = self.qparent.processStatusEventInt
                self.qparent.completeStatus['slinger_sleeping_sec'] = self.qparent.processStatusEventInt
                return

            def _dummyCallback():
                dlnaPlayStatus = dlna.get_playback_info (self.qparent.cast.dlna_dev)
                dlnaDevStatus  = dlna.get_play_status   (self.qparent.cast.dlna_dev)

                if not dlnaPlayStatus or not dlnaDevStatus:
                    if self.qparent.comms_state == 'OK':
                        self.qparent.comms_state = 'FAILED'
                        SGF.getCachedDLNA(force=True, wait=True)
                    return
                self.qparent.comms_state = 'OK'

                # convert from 00:00:00 (hours, min, secs) to total seconds
                td = dlnaPlayStatus["Body"]["GetPositionInfoResponse"]["TrackDuration"].split(":")
                at = dlnaPlayStatus["Body"]["GetPositionInfoResponse"]["AbsTime"].split(":")
                self.qparent.chromeCastStatus = {
                    "dlnaPlayStatus" : dlnaPlayStatus,
                    "dlnaDevStatus"  : dlnaDevStatus,
                    "duration"       : ((int(td[0]) * 60)*60) + (int(td[1])*60) + int(td[2]),
                    "current_time"   : ((int(at[0]) * 60)*60) + (int(at[1])*60) + int(at[2].split('.')[0])
                  }

                # if not recently submitted queued item in the last 1 second (try and prevent race conditions), then allow it to continue
                if ((not self.qparent.submittedQueueItem) or ((datetime.datetime.now() - self.qparent.submittedQueueItem).total_seconds() >= 1.0)):
                    # if no current playing file, then start one up....
                    if (self.playback_state in ('IDLE') and (self.qparent.playMode in ('auto')) and (len(self.qparent.queue) > 0)):
                        self.qparent._prepNextQueueItem()
                        self.qparent._playQueueItem(self.qparent.queue[0])
                        self.qparent.delQueuedMediaItem(0)
                        logging.info(f"SlingerChromeCastQueue:: starting queued item {SGF.toASCII(str(self.qparent.thisQueueItem.metadata))}")
                        self.qparent.submittedQueueItem = datetime.datetime.now()
                else:
                    logging.warning(f"SlingerChromeCastQueue:: queue playing code bypassed due to race conditions!")

                self.qparent.playerStatus = {
                    'filename':     self.qparent.thisQueueItem.location.split('&')[0].split('\\')[-1] if self.qparent.thisQueueItem else '',
                    'title':        self.qparent.thisQueueItem.metadata['title']        if self.qparent.thisQueueItem else '',
                    'album_artist': self.qparent.thisQueueItem.metadata['albumArtist']  if self.qparent.thisQueueItem else '',
                    'album_name':   self.qparent.thisQueueItem.metadata['albumName']    if self.qparent.thisQueueItem else '',
                    'artist':       self.qparent.thisQueueItem.metadata['artist']       if self.qparent.thisQueueItem else '',
                    'content_type': self.qparent.thisQueueItem.mimeType                 if self.qparent.thisQueueItem else '',
                    'current_time': self.qparent.chromeCastStatus["current_time"],
                    'duration':     self.qparent.chromeCastStatus["duration"],
                    'playback_rate': -1,
                    'playback_state': self.playback_state,
                    'volume_level': self.qparent.cast.status.volume_level,
                    'volume_muted': self.qparent.cast.muted,
                    'supported_media_commands': None,
                    'supports_pause': True,
                    'supports_queue_next': True,
                    'supports_queue_prev': False,
                    'supports_seek': True,
                    'supports_skip_backward': False,
                    'supports_skip_forward': False,
                    'supports_stream_mute': True,
                    'supports_stream_volume': True,
                    'media_custom_data': False,
                    'media_metadata': self.qparent.thisQueueItem.metadata if self.qparent.thisQueueItem else '',
                    'images': None,

                    'slinger_queue_changeno': self.qparent.queueChangeNo,
                    'slinger_shuffle': self.qparent.shuffleActive,
                    'slinger_current_media': {'location': '', 'type': '', 'transcoding': ''},
                    'slinger_sleeping_sec':0,
                }

                if self.qparent.thisQueueItem:
                    self.qparent.playerStatus['slinger_current_media']['location']    = self.qparent.thisQueueItem.location
                    self.qparent.playerStatus['slinger_current_media']['type']        = self.qparent.thisQueueItem.type

                self.qparent.playerStatus['slinger_current_media']['transcoding'] = self.qparent.transcodingStatus

                self.qparent.completeStatus = self.qparent.playerStatus.copy()
                self.qparent.completeStatus['slinger_chromecast_queue'] = self.qparent.queue

                # set current sleep info
                self.qparent.playerStatus['slinger_sleeping_sec']     = self.qparent.processStatusEventInt
                self.qparent.chromeCastStatus['slinger_sleeping_sec'] = self.qparent.processStatusEventInt
                self.qparent.completeStatus['slinger_sleeping_sec']   = self.qparent.processStatusEventInt

                callback_function_param(None)

            # use a delayed callback to handle variable synchronisation issue.
            threading.Thread(target=_dummyCallback).start()

            if self.playback_state not in ('IDLE', 'UNKNOWN'):
                self.qparent.processStatusEventInt = 1
                self.qparent.processStatusEventIntKeepActive = self.qparent.activeBeforeSeleep
            elif self.qparent.processStatusEventIntKeepActive < 0: # go into select mode ...
                self.qparent.processStatusEventInt = self.qparent.sleepBeforeWake
                logging.warning(f"*** processStatusEvent : hibernate mode activated for {self.qparent.processStatusEventInt} secs ***")
    class FakeCast:
        pass

    # -==============================================-

    def __init__(self, device):
        self.dlna_dev = copy.deepcopy(device)
        self.dlna_dev["uuid"]     = str(self.dlna_dev["uuid"])

        self.uuid_unique_instance = None
        self.media_controller     = SlingerDLNAPlayer.FakeMediaController()
        self.uuid                 = device["uuid"]

        self.cast                 = SlingerDLNAPlayer.FakeCast()
        self.cast.uuid            = device["uuid"]

        self.cast_info            = SlingerDLNAPlayer.FakeCast()
        self.cast_info.host       = 'LOCAL_PLAYER'

        self.status               = SlingerDLNAPlayer.FakeCast()
        self.status.volume_level  = 1.0
        self.muted                = False

    def wakeNow (self):
        def ignoreCallback (p):
            pass
        self.qparent.processStatusEventInt           = 0
        self.qparent.processStatusEventIntKeepActive = self.qparent.activeBeforeSeleep
        self.media_controller.update_status(ignoreCallback)

    def queueParent (self, qp):
        self.qparent = qp
        self.media_controller.qparent = qp
        self.wakeNow()

    def wait (self):
        pass

    def set_volume(self, level):
        dlna.volume(self.dlna_dev, int(level * 100))
        self.status.volume_level = level

    def set_volume_muted (self, muted):
        self.muted = muted
        dlna.muted(self.dlna_dev, muted)
