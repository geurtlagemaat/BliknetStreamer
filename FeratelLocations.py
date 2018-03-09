import Queue
import time
import os.path
import sqlite3
import thread
import mysql.connector
from twisted.internet import reactor
import traceback
from enum import Enum
import FeratalIndexUtils

class PlayerStatus(Enum):
    UNKNOW = 0
    START_CMD = 1
    BUFFERING = 2
    PLAYING = 3
    READY = 4

class FeratelLocation(object):
    def __init__(self, id=None, streamUrl=None, url=None, country=None, region=None,
                 city=None, cameraName=None, gps=None, FeratelCamID=None, subscribed=0): # visited isCamPage=None, subTitleUrl=None
        self._id = id
        if streamUrl is not None:
            self._streamURL = streamUrl
        else:
            self._streamURL = ""
        if url is not None:
            self._url = url
        else:
            self._url = ""
        if country is not None:
            self._country = country
        else:
            self._country = ""
        if region is not None:
            self._region = region
        else:
            self._region = ""
        if city is not None:
            self._city = city
        else:
            self._city = ""
        self._subscribed = subscribed
        if cameraName is not None:
            self._cameraName = cameraName
        else:
            self._cameraName = ""
        if gps is not None:
            self._gps = gps
        else:
            self._gps = ""
        self._elevation = ""
        self._temp = ""
        self._recorded = ""
        if FeratelCamID is not None:
            self._FeratelCamID = FeratelCamID
        else:
            self._FeratelCamID = ""
        self._PlayStatus = PlayerStatus.UNKNOW
        self._PlayingTime = -1

    @property
    def PlayingTime(self):
        return self._PlayingTime

    @PlayingTime.setter
    def PlayingTime(self, value):
        self._PlayingTime = value

    @property
    def PlayStatus(self):
        return self._PlayStatus

    @PlayStatus.setter
    def PlayStatus(self, value):
        self._PlayStatus = value

    @property
    def FeratelCamID(self):
        return self._FeratelCamID

    @FeratelCamID.setter
    def FeratelCamID(self, value):
        if len(value) > 0:
            self._FeratelCamID = value.strip()
        else:
            self._FeratelCamID = value

    @property
    def gps(self):
        return self._gps

    @gps.setter
    def gps(self, value):
        if len(value) > 0:
            self._gps = value.strip()
        else:
            self._gps = value

    @property
    def cameraName(self):
        return self._cameraName

    @cameraName.setter
    def cameraName(self, value):
        self._cameraName = self._washName(value)

    @property
    def elevation(self):
        return self._elevation

    @elevation.setter
    def elevation(self, value):
        self._elevation = value

    @property
    def temp(self):
        return self._temp

    @temp.setter
    def temp(self, value):
        self._temp = value

    @property
    def recorded(self):
        return self._recorded

    @recorded.setter
    def recorded(self, value):
        if len(value) > 0:
            self._recorded = value.strip()
        else:
            self._recorded = value

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = value

    @property
    def streamUrl(self):
        return self._streamURL

    @streamUrl.setter
    def streamUrl(self, value):
        self._streamURL = value

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, value):
        self._url = value

    @property
    def country(self):
        return self._country

    @country.setter
    def country(self, value):
        self._country = self._washName(value)

    @property
    def region(self):
        return self._region

    @region.setter
    def region(self, value):
        self._region = self._washName(value)

    @property
    def city(self):
        return self._city

    @city.setter
    def city(self, value):
        self._city = self._washName(value)

    @property
    def subscribed(self):
        return self._subscribed

    @subscribed.setter
    def subscribed(self, value):
        self._subscribed = value

    def toDict(self):
        myCamDict = {}
        myCamDict['id'] = self.id
        myCamDict['url'] = self.url
        myCamDict['streamurl'] = self.streamUrl
        myCamDict['country'] = self.country
        myCamDict['region'] = self.region
        myCamDict['city'] = self.city
        myCamDict['cameraname'] = self.cameraName
        myCamDict['temp'] = self.temp
        myCamDict['elevation'] = self.elevation
        myCamDict['subscribed'] = self.subscribed
        myCamDict['FeratelCamID'] = self._FeratelCamID
        myCamDict['gps'] = self._gps
        return myCamDict

    def getMetaFromLocation(self, OldFeratelLocation):
        if ( ( (self.country is None) or (len(self.country)==0) ) and
             ( (OldFeratelLocation.country) is not None and (len(OldFeratelLocation.country)>0) ) ):
            self.country = OldFeratelLocation.country
        if (((self.region is None) or (len(self.region) == 0)) and
                ((OldFeratelLocation.region) is not None and (len(OldFeratelLocation.region) > 0))):
            self.region = OldFeratelLocation.region
        if (((self.city is None) or (len(self.city) == 0)) and
                ((OldFeratelLocation.city) is not None and (len(OldFeratelLocation.city) > 0))):
            self.city = OldFeratelLocation.city
        if (((self.cameraName is None) or (len(self.cameraName) == 0)) and
                ((OldFeratelLocation.cameraName) is not None and (len(OldFeratelLocation.cameraName) > 0))):
            self.cameraName = OldFeratelLocation.cameraName
        if ( ( (self.gps is None) or (len(self.gps)==0) ) and
             ( (OldFeratelLocation.gps) is not None and (len(OldFeratelLocation.gps)>0) ) ):
            self.gps = OldFeratelLocation.gps
        if ( ( (self.elevation is None) or (len(self.elevation)==0) ) and
             ( (OldFeratelLocation.elevation) is not None and (len(OldFeratelLocation.elevation)>0) ) ):
            self.elevation = OldFeratelLocation.elevation
        self.subscribed = OldFeratelLocation.subscribed

    def getCaption(self):
        myCaption = ""
        if len(self.cameraName) > 0:
            myCaption = myCaption + self.cameraName
        elif len(self.city) > 0:
            myCaption = myCaption + self.city
        return myCaption

    def getAllInfo(self):
        def _addSpacer(value, Needed):
            if Needed:
                return value + ", "
            else:
                return value

        myInfo = ""
        bSpaceNeeded = False
        if len(self.country) > 0:
            myInfo = myInfo + self.country
            bSpaceNeeded = True
        if len(self.region) > 0:
            myInfo = _addSpacer(myInfo, bSpaceNeeded)
            myInfo = myInfo + self.region
            bSpaceNeeded = True
        if len(self.city) > 0:
            myInfo = _addSpacer(myInfo, bSpaceNeeded)
            myInfo = myInfo + self.city
            bSpaceNeeded = True
        if len(self.cameraName) > 0:
            myInfo = _addSpacer(myInfo, bSpaceNeeded)
            myInfo = myInfo + self.cameraName
            bSpaceNeeded = True
        if len(self.recorded) > 0:
            myInfo = _addSpacer(myInfo, bSpaceNeeded)
            myInfo = myInfo + "(" + self.recorded + ")"
            bSpaceNeeded = True
        if len(self.temp) > 0:
            myInfo = _addSpacer(myInfo, bSpaceNeeded)
            myInfo = myInfo + self.temp
            bSpaceNeeded = True
        if len(self.elevation) > 0:
            myInfo = _addSpacer(myInfo, bSpaceNeeded)
            myInfo = myInfo + self.elevation
        return myInfo

    def getLocationInfo(self):
        myInfo = ""
        bSpaceNeeded = False

        def _addSpacer(value, Needed):
            if Needed:
                return value + ", "
            else:
                return value

        if len(self.country) > 0:
            myInfo = myInfo + self.country
            bSpaceNeeded = True
        if len(self.region) > 0:
            myInfo = _addSpacer(myInfo, bSpaceNeeded)
            myInfo = myInfo + self.region
            bSpaceNeeded = True
        if len(self.city) > 0:
            myInfo = _addSpacer(myInfo, bSpaceNeeded)
            myInfo = myInfo + self.city
            bSpaceNeeded = True
        if len(self.cameraName) > 0:
            myInfo = _addSpacer(myInfo, bSpaceNeeded)
            myInfo = myInfo + self.cameraName
        return myInfo

    def getRecordDateTimeInfo(self):
        def _addSpacer(value, Needed):
            if Needed:
                return value + ", "
            else:
                return value

        myInfo = ""
        bSpaceNeeded = False
        if len(self.cameraName) > 0:
            myInfo = myInfo + self.cameraName
            bSpaceNeeded = True
        if len(self.recorded) > 0:
            myInfo = _addSpacer(myInfo, bSpaceNeeded)
            myInfo = myInfo + "(" + self.recorded + ")"
        return myInfo

    def getTempHeightInfo(self):
        def _addSpacer(value, Needed):
            if Needed:
                return value + ", "
            else:
                return value

        myInfo = ""
        bSpaceNeeded = False
        if len(self.temp.strip()) > 0:
            myInfo = myInfo + self.temp
            bSpaceNeeded = True
        if len(self.elevation) > 0:
            myInfo = _addSpacer(myInfo, bSpaceNeeded)
            myInfo = myInfo + self.elevation
        return myInfo

    def _washName(self, value):
        if value is not None and len(value) > 0:
            sTmp = value.strip()
            if len(sTmp) > 0:
                return "%s%s" % (sTmp[0].upper(), sTmp[1:])
        else:
            return value

class FeratelLocations(object):
    FERATELWEBTVURL = "https://webtv.feratel.com/webtv/?cam=%s"
    FERATELLOCATIONTBLNAME = "FeratelLocations"
    NEW_FERATELLOCATIONTBLNAME = "NewFeratelLocations"

    def __init__(self, oNodeControl):
        self._NodeControl = oNodeControl
        self._DBConn = None
        self._DBCursor = None
        self._Subscriptions = []
        # indexing things
        self._IndexingQueue = Queue.Queue()
        self._CurrentIndexID = 0
        self._MaxConcurrentIndex = 25
        if self._NodeControl.nodeProps.has_option('Feratel', 'maxConcurrentIndexing'):
            self._MaxConcurrentIndex = self._NodeControl.nodeProps.getint('Feratel', 'maxConcurrentIndexing')
        self._IndexTimeOut = 60
        if self._NodeControl.nodeProps.has_option('Feratel', 'indexTimeOut'):
            self._IndexTimeOut = self._NodeControl.nodeProps.getint('Feratel', 'indexTimeOut')
        self._MaxCamID = 16000 # TODO: settings 16000
        # database things
        if self._NodeControl.nodeProps.has_option('database', 'dbtype') and \
           self._NodeControl.nodeProps.get('database', 'dbtype') == "sqllite":
            if not self._NodeControl.nodeProps.has_option('database', 'datafile'):
                self._NodeControl.log.error("No SQLLite datafile location found in configfile")
            elif not os.path.isfile(self._NodeControl.nodeProps.get('database', 'datafile')):
                self._NodeControl.log.error("SQLLite datafile location does not exists")
            else:
                self._DBConn = sqlite3.connect(self._NodeControl.nodeProps.get('database', 'datafile'))
                self._DBCursor = self._DBConn.cursor()
        elif self._NodeControl.nodeProps.has_option('database', 'dbtype') and \
             self._NodeControl.nodeProps.get('database', 'dbtype') == "mysql":
            if not self._NodeControl.nodeProps.has_option('database','host') or \
               not self._NodeControl.nodeProps.has_option('database', 'port') or \
               not self._NodeControl.nodeProps.has_option('database', 'db') or \
               not self._NodeControl.nodeProps.has_option('database', 'user') or \
               not self._NodeControl.nodeProps.has_option('database', 'pw'):
                self._NodeControl.log.error("MySQL config options incomplete (host, port, db, user and pw.")
            else:
                self._DBConn = mysql.connector.connect(host=self._NodeControl.nodeProps.get('database', 'host'),
                                                       port=self._NodeControl.nodeProps.getint('database', 'port'),
                                                       db=self._NodeControl.nodeProps.get('database', 'db'),
                                                       user=self._NodeControl.nodeProps.get('database', 'user'),
                                                       passwd=self._NodeControl.nodeProps.get('database', 'pw'))
                self._DBCursor = self._DBConn.cursor()
        # self._CheckPlayListTbl();

    def doIndex(self):
        self._CreateFeratelHistoryTbl()
        self._GetNewTempTable()
        self._doMonitorIndexingQueue()
        """ for i in range(1, iToCamID):
            cando, multi threading, maar hoe deferred en threading te combineren? 
            # https://stackoverflow.com/questions/5442910/python-multiprocessing-pool-map-for-multiple-arguments/5443941#5443941   """

    def _doMonitorIndexingQueue(self):
        while ( (self._IndexingQueue.qsize() < self._MaxConcurrentIndex) and
                (self._CurrentIndexID < self._MaxCamID) ):
            if self._CurrentIndexID < self._MaxCamID:
                self._CurrentIndexID +=1
                sCamID = format(self._CurrentIndexID, '04')
                baseURL = self.FERATELWEBTVURL % sCamID
                self._IndexingQueue.put(self._CurrentIndexID)
                # print "start parsing: %s " % str(sCamID)
                self._NodeControl.log.info("start parsing: %s " % str(sCamID))
                # thread.start_new_thread(
                FeratalIndexUtils.parseFeratelPage(FeratelLocation(url=baseURL, FeratelCamID=sCamID),
                                                                           NodeControl=self._NodeControl,
                                                                           IndexOnly=True,
                                                                           CB=self.cbParseFeratelPage)
                # myDeferred = FeratalIndexUtils.parseFeratelPage(
                #    FeratelLocation(url=baseURL, FeratelCamID=sCamID),
                #    NodeControl=self._NodeControl,
                #    IndexOnly=True)
                # myDeferred.addTimeout(60, reactor)
                # myDeferred.addCallback(self.cbParseFeratelPage)
                # myDeferred.addErrback(self.ebPrintError)
            else:
                # queue is max, schedule
                if self._CurrentIndexID < self._MaxCamID:
                    reactor.callLater(3, self._doMonitorIndexingQueue)
        if self._CurrentIndexID >= self._MaxCamID:
            # check deleted cams
            # print "check deleted cams"
            self._NodeControl.log.info("check deleted cams")
            oldCamsList = self.getAllAvailCameras()
            for oldCam in oldCamsList:
                OldCamID = oldCam['FeratelCamID']
                NewFeratelLocation = self.getLocationByCamID(OldCamID, FromTable=self.NEW_FERATELLOCATIONTBLNAME)
                if NewFeratelLocation is None:
                    # gone!
                    OldFeratelLocation = FeratelLocation(url=oldCam['FeratelCamID'], country=oldCam['country'],
                                                         region=oldCam['region'], city=oldCam['city'],
                                                         cameraName=oldCam['cameraname'], gps=oldCam['gps'],
                                                         FeratelCamID=oldCam['FeratelCamID'])
                    self._AddHistoryEvent(FeratelLocation=OldFeratelLocation, Event="Camera niet meer gevonden")
            self._NodeControl.log.debug("Indexing done!")

    def cbParseFeratelPage(self, FeratelLocation):
        # store results when done
        # print "Parsing done for: %s " % str(FeratelLocation.FeratelCamID)
        self._NodeControl.log.info("Parsing done for: %s " % str(FeratelLocation.FeratelCamID))
        if not self._IndexingQueue.empty():
            self._IndexingQueue.get()
        if len(FeratelLocation.streamUrl) > 0:
            # get prev info
            oldFeratelLocation = self.getLocationByCamID(FeratelLocation.FeratelCamID)
            if oldFeratelLocation is not None:
                FeratelLocation.getMetaFromLocation(oldFeratelLocation)
            else:
                self._AddHistoryEvent(FeratelLocation=FeratelLocation, Event="Nieuwe camera")
            try:
                self._DBCursor.execute(
                    'INSERT INTO NewFeratelLocations (url, isCam,streamUrl,country,region,city,camname,gps,feratelcamid,subscribed) VALUES (?,?,?,?,?,?,?,?,?,?)',
                    (FeratelLocation.url, 1, FeratelLocation.streamUrl, FeratelLocation.country, FeratelLocation.region,
                     FeratelLocation.city, FeratelLocation.cameraName, FeratelLocation.gps, FeratelLocation.FeratelCamID,
                     FeratelLocation.subscribed) )
                self._DBConn.commit()
            except Exception:
                self._NodeControl.error(traceback.format_exc())


    """def ebPrintError(self, failure):
        if not self._IndexingQueue.empty():
            self._IndexingQueue.get()
        self._NodeControl.log.debug("error while indexing, error %s." % str(failure)) """

    def getAllAvailCameras(self):
        myCams = []
        myRecordSet = self._DBCursor.execute(
            "SELECT id,url,isCam,streamUrl,country,region,city,camname,gps,feratelcamid, subscribed FROM '%s' GROUP BY country, region, city, camname" % self.FERATELLOCATIONTBLNAME)
        for myItem in myRecordSet:
            self._NodeControl.log.debug('Found location. id: %s, url %s.' % (myItem[0], myItem[1]))
            myLocation = FeratelLocation(id=myItem[0], streamUrl=myItem[3], url=myItem[1], \
                                         country=myItem[4], region=myItem[5], city=myItem[6], cameraName=myItem[7],
                                         gps=myItem[8], FeratelCamID=myItem[9], subscribed=myItem[10])
            myCams.append(myLocation.toDict())
        return myCams

    def getFeratelIndexHistory(self):
        myHistory = []
        myRecordSet = self._DBCursor.execute('SELECT id,url,feratelcamid,caption,updateDate,event FROM FeratelHistory')
        for myItem in myRecordSet:
            histEvent = {}
            histEvent['id']=myItem[0]
            histEvent['url'] = myItem[1]
            histEvent['feratelcamid'] = myItem[2]
            histEvent['caption'] = myItem[3]
            histEvent['updateDate'] = myItem[4]
            histEvent['event'] = myItem[5]
            myHistory.append(histEvent)
        return myHistory

    def getSubscribedLocations(self):
        mySubscriptions = []
        myRecordSet = self._DBCursor.execute(
            'SELECT id,url,isCam,streamUrl,country,region,city,camname,gps,feratelcamid,subscribed FROM %s WHERE subscribed = 1 GROUP BY country, region, city, camname' % self.FERATELLOCATIONTBLNAME)
        for myItem in myRecordSet:
            myLocation = FeratelLocation(id=myItem[0], streamUrl=myItem[3], url=myItem[1],
                                         country=myItem[4], region=myItem[5], city=myItem[6], cameraName=myItem[7],
                                         gps=myItem[8], FeratelCamID=myItem[9], subscribed=myItem[10])
            mySubscriptions.append(myLocation)
        return mySubscriptions

    # setters vanuit het portal
    def setSubscription(self, id, subscribed):
        sql = "UPDATE %s SET subscribed=%s WHERE id=%s" % (self.FERATELLOCATIONTBLNAME, subscribed, id)
        self._DBCursor.execute(sql)
        self._DBConn.commit()

    def setGpsData(self, id, gps):
        sql = "UPDATE %s SET gps=%s WHERE id=%s" % (self.FERATELLOCATIONTBLNAME, gps, id)
        self._DBCursor.execute(sql)
        self._DBConn.commit()

    def getLocationByCamID(self, CamID, FromTable=None):
        SelectedTable = self.FERATELLOCATIONTBLNAME
        if FromTable is not None:
            SelectedTable = FromTable
        mySQL = 'SELECT id,url,isCam,streamUrl,country,region,city,camname,gps,feratelcamid,subscribed FROM %s WHERE feratelcamid = %s' % (SelectedTable, str(
            CamID))
        try:
            myRecordSet = self._DBCursor.execute(mySQL).fetchone()
            if myRecordSet is not None:
                self._NodeControl.log.debug(
                    'Found by CAMID %s,location. id: %s, url %s.' % (CamID, myRecordSet[0], myRecordSet[1]))
                myLocation = FeratelLocation(id=myRecordSet[0], streamUrl=myRecordSet[3], url=myRecordSet[1],
                                             country=myRecordSet[4], region=myRecordSet[5], city=myRecordSet[6],
                                             cameraName=myRecordSet[7],
                                             gps=myRecordSet[8], FeratelCamID=myRecordSet[9], subscribed=myRecordSet[10])
                return myLocation
            else:
                return None
        except Exception:
            self._NodeControl.error(traceback.format_exc())

    # utils
    def swapTempToDefTable(self):
        sql = "SELECT name FROM sqlite_master WHERE type = 'table' AND name = '%s'" % self.NEW_FERATELLOCATIONTBLNAME
        NewTableExists = self._DBCursor.execute(sql).fetchone()
        if NewTableExists:
            self._DBCursor.executescript("DROP TABLE IF EXISTS '%s' " % self.FERATELLOCATIONTBLNAME)
            self._DBCursor.execute("ALTER TABLE %s RENAME TO %s" % (self.NEW_FERATELLOCATIONTBLNAME, self.FERATELLOCATIONTBLNAME))

    def _GetNewTempTable(self):
        self._DBCursor.executescript("DROP TABLE IF EXISTS '%s' " % self.NEW_FERATELLOCATIONTBLNAME)
        self._CreateFeratelLocationTbl(self.NEW_FERATELLOCATIONTBLNAME)

    def _CreateFeratelLocationTbl(self, TableName):
        sql = "CREATE TABLE IF NOT EXISTS `%s` ( `id` INTEGER PRIMARY KEY AUTOINCREMENT, `url` TEXT, `isCam` INTEGER NOT NULL DEFAULT 0, `streamUrl` TEXT, `country` TEXT, `region` TEXT, `city` TEXT, `camname` TEXT, `gps` TEXT, `feratelcamid` TEXT, `subscribed` INTEGER NOT NULL DEFAULT 0 )" % TableName
        self._DBCursor.execute(sql)

    def _CreateFeratelHistoryTbl(self):
        sql = "CREATE TABLE IF NOT EXISTS `FeratelHistory` ( `id` INTEGER PRIMARY KEY AUTOINCREMENT, `url` TEXT, `feratelcamid` TEXT, `caption` TEXT, `updateDate` TEXT, `event` TEXT )"
        self._DBCursor.execute(sql)

    def _AddHistoryEvent(self, FeratelLocation, Event):
        self._DBCursor.execute(
            'INSERT INTO FeratelHistory (url, feratelcamid, caption, updateDate, event) VALUES (?,?,?,?,?)',
            (FeratelLocation.url, FeratelLocation.FeratelCamID, FeratelLocation.getCaption(), time.strftime("%c"), Event))
        self._DBConn.commit()