__author__ = 'geurt'

import os
import traceback

import datetime

try:
    import RPi.GPIO as GPIO
except:
    pass

from twisted.internet import reactor
from twisted.internet import task
from twisted.web import server

import management_portal.portal_resource
from CastDevices import ChromeCastNotFoundException
from FeratelLocations import FeratelLocations
from StreamerNodeControl import StreamerNodeControl
from VideoServer import getVideo, getSubs, getStaticHTML

oNodeControl = None


def switchChannels(channel):
    oNodeControl.log.debug("Button press, button: %s." % channel)
    if oNodeControl.nodeProps.has_option('buttonControls', 'defaultChromeCast'):
        defaultChromeCast = oNodeControl.nodeProps.get('buttonControls', 'defaultChromeCast')
        oNodeControl.log.debug("default ChromeCast: %s." % defaultChromeCast)
        myCastCommands = oNodeControl.getCastDevices
        # huidige mode uitzetten
        oNodeControl.log.debug("Stopping current App.")
        try:
            myCastCommands.setCommand(CastDevice=defaultChromeCast,
                                      Command="STOP", Random=None, PlayList=None, AppId=None)
        except ChromeCastNotFoundException:
            oNodeControl.log.debug("Default Chrome Cast not found, discover network again.")
            myCastCommands.doDiscoverCastDevices()
            myCastCommands.setCommand(CastDevice=defaultChromeCast,
                                      Command="STOP", Random=None, PlayList=None, AppId=None)

        oNodeControl.log.debug("Stopping current App. done")
        if channel == 4:
            oNodeControl.log.debug("Inside press, button: %s." % channel)
            btn1AppID = None
            if oNodeControl.nodeProps.has_option('buttonControls', 'btn1AppID'):
                btn1AppID = oNodeControl.nodeProps.get('buttonControls', 'btn1AppID')
                oNodeControl.log.debug("Starting button 4 appId: %s" % btn1AppID)
                myCastCommands.setCommand(CastDevice=defaultChromeCast,
                                          Command="PLAY",
                                          Random=True,
                                          PlayList=None,
                                          AppId=btn1AppID)
            else:
                oNodeControl.log.warning("no buttonControls | btn1AppID setting found")
        if channel == 17:
            oNodeControl.log.debug("Starting button 17 App: Feratel Cameras")
            myCastCommands.setCommand(CastDevice=defaultChromeCast,
                                      Command="PLAY",
                                      Random=True,
                                      PlayList="Feratel Cameras",
                                      AppId=None)
            if oNodeControl.nodeProps.has_option('buttonControls', 'FeratelTimeOut'):
                oNodeControl.log.debug(
                    "Setting Feratel TimeOut to: %s." % oNodeControl.nodeProps.get('buttonControls', 'FeratelTimeOut'))
                reactor.callLater(oNodeControl.nodeProps.getint('buttonControls', 'FeratelTimeOut'),
                                  eFeratelTimeOutEvent)
        if channel == 27:
            oNodeControl.log.debug("Starting button 27 App: Rondje Water-Nederland")
            myCastCommands.setCommand(CastDevice=defaultChromeCast,
                                      Command="PLAY",
                                      Random=True,
                                      PlayList="Rondje Water-Nederland",
                                      AppId=None)
            if oNodeControl.nodeProps.has_option('buttonControls', 'FeratelTimeOut'):
                oNodeControl.log.debug(
                    "Setting Feratel TimeOut to: %s." % oNodeControl.nodeProps.get('buttonControls', 'FeratelTimeOut'))
                reactor.callLater(oNodeControl.nodeProps.getint('buttonControls', 'FeratelTimeOut'),
                                  eFeratelTimeOutEvent)
    else:
        oNodeControl.log.warning("no buttonControls | defaultChromeCast device setting found!")


def eFeratelTimeOutEvent():
    reactor.callFromThread(switchChannels, 4)


def eBtnPressEvent(channel):
    # see https://stackoverflow.com/questions/28184155/twisted-python-sending-message-via-gpio-that-isnt-received-until-the-enter-ke
    reactor.callFromThread(switchChannels, channel)


def setupGPIO(NodeControl):
    if os.name == 'posix':
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(4, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(4, GPIO.RISING, callback=eBtnPressEvent, bouncetime=1000)
        GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(17, GPIO.RISING, callback=eBtnPressEvent, bouncetime=1000)
        GPIO.setup(27, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(27, GPIO.RISING, callback=eBtnPressEvent, bouncetime=1000)

def IndexEvent(NodeControl):
    try:
        myLocations = FeratelLocations(NodeControl)
        myLocations.doIndex()
    except Exception:
        oNodeControl.log.error("Error indexing Feratel Locations:%s." % traceback.format_exc())

if __name__ == '__main__':
    now = datetime.datetime.now()
    oNodeControl = StreamerNodeControl(r'settings/bliknetnode.conf')
    oNodeControl.log.info("BliknetNode: %s starting at: %s." % (oNodeControl.nodeID, now))
    if oNodeControl.nodeProps.has_option('buttonControls', 'buttonControls') and oNodeControl.nodeProps.getboolean(
            'buttonControls', 'buttonControls'):
        setupGPIO(oNodeControl)
    if oNodeControl.nodeProps.has_option('Feratel', 'index') and oNodeControl.nodeProps.getboolean('Feratel', 'index'):
        iIndexInt = 86400
        if oNodeControl.nodeProps.has_option('Feratel', 'indexInterval'):
            iIndexInt = oNodeControl.nodeProps.getint('Feratel', 'indexInterval')
        oNodeControl.log.info("Feratel index task active, interval: %s" % str(iIndexInt))
        l = task.LoopingCall(IndexEvent, oNodeControl)
        l.start(iIndexInt)
    else:
        oNodeControl.log.info("Feratel index task not active.")

    if (oNodeControl.mqttClient != None):
        pass

    if oNodeControl.nodeProps.has_option('servicePortal', 'startPortal') and \
            oNodeControl.nodeProps.getboolean('servicePortal', 'startPortal'):
        oNodeControl.log.info("Service portal active")
        sUserPortalDB = ""
        if not oNodeControl.nodeProps.has_option('servicePortal', 'userDatabase'):
            oNodeControl.log.error("Can not start Service portal: [servicePortal], [userDatabase] not found")
        else:
            sUserPortalDB = oNodeControl.nodeProps.get('servicePortal', 'userDatabase')
            iPortalPort = 81
            try:
                if oNodeControl.nodeProps.has_option('servicePortal', 'portalPort'):
                    iPortalPort = oNodeControl.nodeProps.getint('servicePortal', 'portalPort')
                    management_portal.portal_resource.startPortal(NodeControl=oNodeControl, listenPort=iPortalPort,
                                                                  listenAddress='', userDatabasePath=sUserPortalDB)
            except Exception:
                oNodeControl.log.error("Error reading [servicePortal],[portalPort]: %s " % traceback.format_exc())

    if oNodeControl.nodeProps.has_option('videoserver', 'videoPort'):
        site = server.Site(getVideo(oNodeControl))
        reactor.listenTCP(oNodeControl.nodeProps.getint('videoserver', 'videoPort'), site)

    if oNodeControl.nodeProps.has_option('videoserver', 'subsPort'):
        site = server.Site(getSubs(oNodeControl))
        reactor.listenTCP(oNodeControl.nodeProps.getint('videoserver', 'subsPort'), site)

    if oNodeControl.nodeProps.has_option('videoserver', 'htmlPort'):
        site = server.Site(getStaticHTML(oNodeControl))
        reactor.listenTCP(oNodeControl.nodeProps.getint('videoserver', 'htmlPort'), site)

    oNodeControl.log.info("Starting reactor")
    reactor.run()
    oNodeControl.log.info("Shutting down, ready, bye!")

"""
CANDO: 
Cando, eigen splash screen, zie https://github.com/home-assistant/home-assistant/blob/dev/homeassistant/components/media_player/cast.py
Eigen videos
Status en Splash screens
SSL: http://twistedmatrix.com/documents/12.3.0/core/howto/ssl.html en http://www.homecomputerlab.com/creating-a-self-signed-ssl-certificate
Skyline videos: https://www.skylinewebcams.com/  
MQTT interface
"""
