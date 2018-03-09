import os.path
import sqlite3

import mysql.connector

import pychromecast.pychromecast
from CastDevice import CastDevice


class ChromeCastNotFoundException(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

class CastDevices(object):
    def __init__(self, oNodeControl):
        self._NodeControl = oNodeControl
        self._CastDevices = {}

        if self._NodeControl.nodeProps.has_option('Feratel', 'dbtype') and self._NodeControl.nodeProps.get(
                'Feratel', 'dbtype') == "sqllite":
            if not self._NodeControl.nodeProps.has_option('Feratel', 'datafile'):
                self._NodeControl.log.error("No SQLLite datafile location found in configfile")
            elif not os.path.isfile(self._NodeControl.nodeProps.get('Feratel', 'datafile')):
                self._NodeControl.log.error("SQLLite datafile location does not exists")
            else:
                self._DBConn = sqlite3.connect(self._NodeControl.nodeProps.get('Feratel', 'datafile'))
                self._DBCursor = self._DBConn.cursor()
        elif self._NodeControl.nodeProps.has_option('Feratel', 'dbtype') and self._NodeControl.nodeProps.get(
                'Feratel', 'dbtype') == "mysql":
            if not self._NodeControl.nodeProps.has_option('Feratel',
                                                          'host') or not self._NodeControl.nodeProps.has_option(
                'Feratel', 'port') or \
                    not self._NodeControl.nodeProps.has_option('Feratel',
                                                               'db') or not self._NodeControl.nodeProps.has_option(
                'Feratel', 'user') or \
                    not self._NodeControl.nodeProps.has_option('Feratel', 'pw'):
                self._NodeControl.log.error("MySQL config options incomplete (host, port, db, user and pw.")
            else:
                self._DBConn = mysql.connector.connect(host=self._NodeControl.nodeProps.get('Feratel', 'host'),
                                                       port=self._NodeControl.nodeProps.getint('Feratel', 'port'),
                                                       db=self._NodeControl.nodeProps.get('Feratel', 'db'),
                                                       user=self._NodeControl.nodeProps.get('Feratel', 'user'),
                                                       passwd=self._NodeControl.nodeProps.get('Feratel', 'pw'))
                self._DBCursor = self._DBConn.cursor()
        self.doDiscoverCastDevices()

    def doDiscoverCastDevices(self):
        self._CastDevices.clear()
        casts = pychromecast.pychromecast.get_chromecasts(timeout=60)
        for currentCast in casts:
            self._CastDevices[currentCast.device.friendly_name] = CastDevice(currentCast, self._NodeControl)

    def setCommand(self, CastDevice, Command, Random=-1, PlayList=None, AppId=None):
        self._NodeControl.log.debug("setCommand CastDevice: %s." % CastDevice)
        if CastDevice in self._CastDevices:
            if Command == "0" or Command.upper() == "STOP":
                self._NodeControl.log.debug("setCommand CastDevice: %s. to Stop" % CastDevice)
                self._CastDevices[CastDevice].Active = False
            elif Command == "1" or Command.upper() == "PLAY":
                self.randomPlay = Random
                self.playList = PlayList
                self._CastDevices[CastDevice].randomPlay = Random
                self._CastDevices[CastDevice].playList = PlayList
                self._CastDevices[CastDevice].AppId = AppId
                self._CastDevices[CastDevice].Active = True
            elif Command == "99" or Command.upper() == "RESTART":
                self._CastDevices[CastDevice].Active = False
                self._CastDevices[CastDevice].doRestart()
            else:
                self._NodeControl.log.error("Commando: %s niet herkend!" % Command)
                raise Exception("Commando: %s niet herkend!" % Command)
        else:
            self._NodeControl.log.error("Cast Device met naam: %s niet gevonden!" % CastDevice)
            raise ChromeCastNotFoundException("Cast Device met naam: %s niet gevonden!" % CastDevice)

    def getCastDevices(self):
        myDevices = []
        for deviceName, currentCast in self._CastDevices.iteritems():
            myCastDevice = {}
            myCastDevice["devicenaam"] = deviceName
            if currentCast.Active:
                myCastDevice["status"] = "actief"
            else:
                myCastDevice["status"] = "stand-by"
            myCastDevice["playList"] = currentCast.playList
            myDevices.append(myCastDevice)
        return myDevices