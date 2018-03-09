import Queue
import os
import socket
import struct
import traceback
from random import shuffle
from threading import Thread

from twisted.internet import reactor

import FeratalIndexUtils
from FeratelLocations import FeratelLocations, PlayerStatus
from GenericLocations import GenericLocations
from pychromecast.pychromecast.controllers import media
from pychromecast.pychromecast.controllers.blikmedia import BlikMediaController


class CastDevice(object):
    # https://www.reddit.com/r/homeautomation/comments/4fc01z/quick_question_for_openhab_users/d28vnc4/
    def __init__(self, Device, NodeControl):
        self._NodeControl = NodeControl
        self._Device = Device  # ChromeCast object
        self._SubscribedLocations = []  # List met FeratelLocation objects
        self._CurrentPlayingFeratelObject = None

        self._genericPlayIndex = -1
        self._GenericPlayerWatcher = None

        self._CacheIndex = -1;
        self._CashQueue = Queue.Queue()
        self._MaxConcurrent = 25
        self._StartWhenCacheReady = False
        if self._NodeControl.nodeProps.has_option('Feratel', 'maxConcurrent'):
            self._MaxConcurrent = self._NodeControl.nodeProps.getint('Feratel', 'maxConcurrent')
        self._IsCashing = []

        self._Active = False
        self._DeviceName = self._Device.device.friendly_name
        self._Device.media_controller.register_status_listener(self)
        self._Device.register_connection_listener(self)
        #
        self._FeratelMediaController = BlikMediaController()
        self._Device.register_handler(self._FeratelMediaController)
        self._FeratelMediaController.register_status_listener(self)
        #
        self._ReadyToPlay = Queue.Queue()
        self._StreamTimerWatcher = None
        self._PlayTimeoutWatcher = None
        self._MaxPlayingTime = None
        if self._NodeControl.nodeProps.has_option('Feratel', 'maxLength'):
            self._MaxPlayingTime = self._NodeControl.nodeProps.getint('Feratel', 'maxLength')
        #
        self._myIPAdress = 'bliknet.com'
        if NodeControl.nodeProps.has_option('videoserver', 'domain'):
            self._myIPAdress = NodeControl.nodeProps.get('videoserver', 'domain')
        if NodeControl.nodeProps.has_option('videoserver', 'runLocal') and NodeControl.nodeProps.getboolean(
                'videoserver', 'runLocal'):
            self._myIPAdress = self.get_ip_address()

        self._VideoServerPort = 8001
        if NodeControl is not None and NodeControl.nodeProps.has_option('videoserver', 'videoPort'):
            self._VideoServerPort = NodeControl.nodeProps.getint('videoserver', 'videoPort')
        self._SubsServerPort = 8002
        if NodeControl is not None and NodeControl.nodeProps.has_option('videoserver', 'subsPort'):
            self._SubsServerPort = NodeControl.nodeProps.getint('videoserver', 'subsPort')

        self._delayedCaching = 10
        if NodeControl is not None and NodeControl.nodeProps.has_option('Feratel', 'delayedCaching'):
            self._delayedCaching = NodeControl.nodeProps.getint('Feratel', 'delayedCaching')
        self._StreamWatcherInterval = 10
        if NodeControl is not None and NodeControl.nodeProps.has_option('Feratel', 'streamWatcherInt'):
            self._StreamWatcherInterval = NodeControl.nodeProps.getint('Feratel', 'streamWatcherInt')

        self._WaitWhileBufferingAppID = None
        if NodeControl is not None and NodeControl.nodeProps.has_option('Feratel', 'waitAppId'):
            self._WaitWhileBufferingAppID = NodeControl.nodeProps.get('Feratel', 'waitAppId')

        self._minCachedItems = 3
        self._randomPlay = False
        self._playList = ""

        self._AppId = None
        self._NASFileMode = False # TODO opsplitsen van deze module zodat elke mode netjes wordt afgehandeld

    @property
    def AppId(self):
        return self._AppId

    @AppId.setter
    def AppId(self, value):
        self._AppId = value

    @property
    def randomPlay(self):
        return self._randomPlay

    @randomPlay.setter
    def randomPlay(self, value):
        self._randomPlay = value

    @property
    def playList(self):
        return self._playList

    @playList.setter
    def playList(self, value):
        self._playList = value

    @property
    def Active(self):
        return self._Active

    @Active.setter
    def Active(self, value):
        self._NodeControl.log.debug('Change status of device %s to %s.' % (self._DeviceName, value))
        if value and not self._Active:
            self._Active = value
            if self._AppId is not None and self._AppId != "":
                # Launch Chrome Cast App
                self._Device.start_app(app_id=self._AppId)
            elif self._playList == 'Feratel Cameras':
                if self._WaitWhileBufferingAppID is not None:
                    self._Device.start_app(app_id=self._WaitWhileBufferingAppID)
                self._StartWhenCacheReady = True
                myLocations = FeratelLocations(self._NodeControl)
                self._CurrentPlayingFeratelObject = None
                self._CacheIndex = -1
                with self._CashQueue.mutex:
                    self._CashQueue.queue.clear()
                with self._ReadyToPlay.mutex:
                    self._ReadyToPlay.queue.clear()
                self._SubscribedLocations = myLocations.getSubscribedLocations()
                if self.randomPlay:
                    shuffle(self._SubscribedLocations)
                self._NodeControl.log.debug('Start device %s.' % self._DeviceName)
                self._doMonitorCacheQueue()
            else:
                # generic list
                self._genericPlayIndex = -1
                myLocations = GenericLocations(self._NodeControl)
                self._NodeControl.log.debug('Start device %s.' % self._DeviceName)
                self._SubscribedLocations = myLocations.getPlayListItems(self._playList)
                if self.randomPlay:
                    shuffle(self._SubscribedLocations)
                    if len(self._SubscribedLocations) > 0:
                        self._genericPlayIndex = 0
                        self.startGenericItem()
        else:
            self._NodeControl.log.debug('Trying to de-activate.')
            self._Active = value
            self._playList = ''
            self._AppId = None
            if self._StreamTimerWatcher is not None:
                try:
                    self._StreamTimerWatcher.cancel()
                except:
                    pass
            try:
                if self._Device.media_controller.status.player_is_playing:
                    self._Device.media_controller.stop()
                if self._FeratelMediaController.status.player_is_playing:
                    self._FeratelMediaController.stop()
                if self._Device.app_id is not None:
                    self._Device.quit_app()
                self._NodeControl.log.debug('Stopped device %s.' % self._DeviceName)
            except:
                exception = str(traceback.format_exc())
                self.NodeControl.log.error("Error stopping device: % s, error: %s ." % (self._DeviceName, exception))

    def startGenericItem(self):
        self._NASFileMode = False
        myGenericItem = self._SubscribedLocations[self._genericPlayIndex]
        if myGenericItem is not None:
            myUpperStreamURL = myGenericItem.streamUrl.upper()
            if myUpperStreamURL.startswith('CHROMECASTAPPID:'):
                myAppID = myUpperStreamURL.split(":")[1]
                self._Device.start_app(app_id=myAppID)
            elif myUpperStreamURL.startswith('NASFILE:') and self.hasNASMediaSupport():
                myNASFile = os.path.join(self.getNASLocation(), myGenericItem.streamUrl.split(":")[1])
                if os.path.isfile(myNASFile): # alleen voor local mode geldig TODO aanpassen
                    self._NASFileMode = True
                    myURL = "http://%s:%s?nasfile=%s" % (
                        self._myIPAdress, str(self._VideoServerPort), myGenericItem.streamUrl.split(":")[1])

                    self._Device.media_controller.play_media(url=myURL,
                                                             content_type="video/mp4",
                                                             title=myGenericItem.cameraName,
                                                             subtitles=None)
                    # TODO doorschakelen naar volgende
                else:
                    # item not found, select next one
                    if len(self._SubscribedLocations) > 1:
                        self._GenericPlayerWatcher = reactor.callLater(1, self._cbGenericPlayerStop)
            else:
                self._Device.media_controller.play_media(url=myGenericItem.streamUrl,
                                                         content_type="video/mp4",
                                                         title=myGenericItem.cameraName,
                                                         subtitles=None)
                if len(self._SubscribedLocations) > 1:
                    # TODO read time from db
                    self._GenericPlayerWatcher = reactor.callLater(120, self._cbGenericPlayerStop)

    def _cbGenericPlayerStop(self):
        if self._genericPlayIndex < len(self._SubscribedLocations) - 1:
            self._genericPlayIndex += 1
        else:
            self._genericPlayIndex = 0
        if self._Active:
            self.startGenericItem()

    def _doMonitorCacheQueue(self):
        self._NodeControl.log.debug(
            "CashQueue size: {}, ready size {}, current cashing: {}".format(self._CashQueue.qsize(),
                                                                            self._ReadyToPlay.qsize(),
                                                                            len(self._IsCashing)))
        if ((self._CashQueue.qsize() > 0) and
                (len(self._IsCashing) <= self._MaxConcurrent) and \
                    (self._CurrentPlayingFeratelObject is None or
                             self._CurrentPlayingFeratelObject.PlayStatus != PlayerStatus.BUFFERING)):
            FeratelLocationToCache = self._CashQueue.get()
            self._IsCashing.append(FeratelLocationToCache.FeratelCamID)

            myThr = Thread(target=FeratalIndexUtils.parseFeratelPage,
                           args=(FeratelLocationToCache, self._NodeControl, False, self.cbPreParseReady))
            myThr.start()
            """FeratalIndexUtils.parseFeratelPage(FeratelLocation=FeratelLocationToCache,
                                                                       NodeControl=self._NodeControl,
                                                                       IndexOnly=False,
                                                                       CB=self.cbPreParseReady)"""
        if (self._ReadyToPlay.qsize() + self._CashQueue.qsize()) < self._minCachedItems:
            self._SetNextCacheIndex()
            self._CashQueue.put(self._SubscribedLocations[self._CacheIndex])
        if self._Active:
            reactor.callLater(3, self._doMonitorCacheQueue)

    def new_connection_status(self, new_status):
        self._NodeControl.log.debug("new_connection_status: %s" % new_status)

    def new_media_status(self, status):
        print "status: %s" % status
        self._NodeControl.log.debug("status: %s" % status)
        myFeratelObject = self._CurrentPlayingFeratelObject
        if myFeratelObject is not None:
            videoURL = "http://%s:%s?camid=%s" % (self._myIPAdress,
                                                  str(self._VideoServerPort),
                                                  str(myFeratelObject.FeratelCamID))
            if status.content_id == videoURL:
                # check of het om de url gaat die van deze client is
                if status.player_state == media.MEDIA_PLAYER_STATE_PLAYING:
                    myFeratelObject.PlayStatus = PlayerStatus.PLAYING
                elif status.player_state == media.MEDIA_PLAYER_STATE_BUFFERING:
                    myFeratelObject.PlayStatus = PlayerStatus.BUFFERING
                elif status.player_state == media.MEDIA_PLAYER_STATE_PAUSED:
                    pass
                elif status.player_state == media.MEDIA_PLAYER_STATE_IDLE:
                    if myFeratelObject.PlayStatus == PlayerStatus.PLAYING:
                        myFeratelObject.PlayStatus = PlayerStatus.READY
                        if self._Active:
                            self.doStartNextItem()
                elif status.player_state == media.MEDIA_PLAYER_STATE_UNKNOWN:
                    myFeratelObject.PlayStatus = PlayerStatus.UNKNOW

                if ((status.player_state == media.MEDIA_PLAYER_STATE_PLAYING or \
                                 status.player_state == media.MEDIA_PLAYER_STATE_BUFFERING) and
                            status.duration > 0):
                    myFeratelObject.PlayingTime = status.duration
                    if self._PlayTimeoutWatcher is not None:
                        self._PlayTimeoutWatcher.cancel()
                    timeLeft = status.duration;
                    if status.current_time > 0:
                        timeLeft -= status.current_time
                    if self._MaxPlayingTime is not None and timeLeft > self._MaxPlayingTime:
                        timeLeft = self._MaxPlayingTime
                    if timeLeft > 0:
                        self._PlayTimeoutWatcher = reactor.callLater(timeLeft - 3, self._cbPlayTimeOut)
                self._NodeControl.log.debug("Mediastatus update: %s" % status)
        elif self._NASFileMode:
            pass
            """if status.player_state == media.MEDIA_PLAYER_STATE_IDLE:
                if self._Active:
                    if self._genericPlayIndex < len(self._SubscribedLocations) - 1:
                        self._genericPlayIndex += 1
                    else:
                        self._genericPlayIndex = 0
                    if self._Active:
                        self.startGenericItem()  """

    def _cbPlayTimeOut(self):
        # some streams stay in playing status
        # self._Device.media_controller.stop()
        self._FeratelMediaController.stop()

    def _cbStreamWatcher(self):
        if self._Active:
            # starten volgende item wanneer item niet af wil spelen
            myFeratelObject = self._CurrentPlayingFeratelObject
            if myFeratelObject is not None:
                if myFeratelObject.PlayStatus == PlayerStatus.BUFFERING or \
                                myFeratelObject.PlayStatus == PlayerStatus.PLAYING:
                    pass
                else:
                    self.doStartNextItem()

    def doStartNextItem(self):
        self._NASFileMode = False
        if self._ReadyToPlay.qsize() > 0:
            self._CurrentPlayingFeratelObject = self._ReadyToPlay.get()
            if self._CurrentPlayingFeratelObject is not None and self._CurrentPlayingFeratelObject.streamUrl is not None:
                self._NodeControl.log.info("Start playing: %s. " % self._CurrentPlayingFeratelObject.streamUrl)
                videoURL = "http://%s:%s?camid=%s" % (
                self._myIPAdress, str(self._VideoServerPort), str(self._CurrentPlayingFeratelObject.FeratelCamID))
                subsURL = "http://%s:%s?camid=%s" % (
                self._myIPAdress, str(self._SubsServerPort), str(self._CurrentPlayingFeratelObject.FeratelCamID))
                self._StreamDidPlay = False
                self._CurrentPlayingFeratelObject.PlayStatus = PlayerStatus.START_CMD

                self._FeratelMediaController.play_media(url=videoURL, content_type="video/mp4",
                                                        title=self._CurrentPlayingFeratelObject.getCaption(),
                                                        subtitles=subsURL)
                self._StreamTimerWatcher = reactor.callLater(self._StreamWatcherInterval, self._cbStreamWatcher)
            else:
                self._NodeControl.log.info("Not playing, no streamURL found. CamID: %s. " % str(
                    self._CurrentPlayingFeratelObject.FeratelCamID))
                self.doStartNextItem()

    def _SetNextCacheIndex(self):
        if self._CacheIndex < len(self._SubscribedLocations):
            self._CacheIndex = self._CacheIndex + 1
        else:
            self._CacheIndex = 0
        return self._CacheIndex

    def cbPreParseReady(self, FeratelLocation, Succes=True):
        if Succes:
            self._NodeControl.log.info("Preparse of CamID: %s succes." % FeratelLocation.FeratelCamID)
            self._ReadyToPlay.put(FeratelLocation)
            if self._StartWhenCacheReady and self._ReadyToPlay.qsize() >= self._minCachedItems:
                self._StartWhenCacheReady = False
                self.doStartNextItem()
        else:
            self._NodeControl.log.info("Preparse of CamID: %s failed!" % FeratelLocation.FeratelCamID)
        # always remove
        self._IsCashing.remove(FeratelLocation.FeratelCamID)


    @property
    def Device(self):
        return self._Device

    def doRestart(self):
        self._Device.reboot()

    def get_ip_address(self):
        from sys import platform
        if platform == "linux" or platform == "linux2":
            # linux
            if not self._NodeControl.nodeProps.has_option('videoserver', 'internetInterface'):
                self._NodeControl.log.error('No videoserver | internetInterface setting found IP lookup not reliable.')
                return socket.gethostbyname(socket.gethostname())
            else:
                import fcntl
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                return socket.inet_ntoa(fcntl.ioctl(
                    s.fileno(),
                    0x8915,  # SIOCGIFADDR
                    struct.pack('256s', self._NodeControl.nodeProps.get('videoserver', 'internetInterface')[:15])
                )[20:24])
        elif platform == "darwin":
            # haha!
            return socket.gethostbyname(socket.gethostname())
        elif platform == "win32":
            return socket.gethostbyname(socket.gethostname())

    def hasNASMediaSupport(self):
        if self._NodeControl.nodeProps.has_option('videoserver', 'NASSupport') and \
                self._NodeControl.nodeProps.getboolean('videoserver', 'NASSupport') and \
                self._NodeControl.nodeProps.has_option('videoserver', 'NASRoot') and \
                        len(self._NodeControl.nodeProps.get('videoserver', 'NASRoot')) > 0:
            return True
        else:
            return False

    def getNASLocation(self):
        if self._NodeControl.nodeProps.has_option('videoserver', 'NASSupport') and \
                self._NodeControl.nodeProps.getboolean('videoserver', 'NASSupport') and \
                self._NodeControl.nodeProps.has_option('videoserver', 'NASRoot') and \
                        len(self._NodeControl.nodeProps.get('videoserver', 'NASRoot')) > 0:
            return self._NodeControl.nodeProps.get('videoserver', 'NASRoot')
        else:
            return None
