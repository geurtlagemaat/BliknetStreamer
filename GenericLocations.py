import os
import sqlite3
import traceback

import mysql

from FeratelLocations import PlayerStatus


class GenericLocation(object):
    def __init__(self, id=None, streamUrl=None, cameraName=None, gps=None, desiredPlayTime=None):
        self._id = id
        if streamUrl is not None:
            self._streamURL = streamUrl
        else:
            self._streamURL = ""
        if cameraName is not None:
            self._cameraName = cameraName
        else:
            self._cameraName = ""
        if gps is not None:
            self._gps = gps
        else:
            self._gps = ""
        if desiredPlayTime is not None:
            self._desiredPlayTime = desiredPlayTime
        else:
            self._desiredPlayTime = ""
        self._elevation = ""
        self._temp = ""
        self._PlayStatus = PlayerStatus.UNKNOW
        self._PlayingTime = -1

    @property
    def desiredPlayTime(self):
        return self._desiredPlayTime

    @desiredPlayTime.setter
    def desiredPlayTime(self, value):
        self._desiredPlayTime = value

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


class GenericLocations(object):
    def __init__(self, oNodeControl):
        self._NodeControl = oNodeControl
        self._DBConn = None
        self._DBCursor = None

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
            if not self._NodeControl.nodeProps.has_option('database', 'host') or \
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
        self._CheckPlayListTbl()

    def getPlayLists(self):
        myPlayLists = []
        myRecordSet = self._DBCursor.execute(
            'SELECT id, naam, omschrijving FROM PlayLists WHERE parentID = 0')  # WHERE parentID IS NULL OR parentID = ''
        for myItem in myRecordSet:
            myPlayList = {'id': myItem[0], 'naam': myItem[1], 'omschrijving': myItem[2]}
            myPlayLists.append(myPlayList)
        return myPlayLists

    def getPlayListsItems(self):
        # PlayLists and it's children
        myPlayLists = {}
        myRecordSet = self._DBCursor.execute(
            'SELECT id, parentID, naam,omschrijving, url FROM PlayLists')  # WHERE parentID IS NULL OR parentID = ''
        for myItem in myRecordSet:
            if myItem[0] == 1:
                pass  # buildin Feratel List
            elif myItem[1] is None or (myItem[1]) <= 0:
                # a PayList
                myPlayLists[myItem[0]] = {}
                myPlayLists[myItem[0]][0] = {'naam': myItem[2], 'omschrijving': myItem[3], 'url': myItem[4]}
            elif myItem[1] is not None and myItem[1] > 0:
                # a Item
                if myItem[1] in myPlayLists:
                    myPlayLists[myItem[1]][myItem[0]] = {'naam': myItem[2], 'omschrijving': myItem[3], 'url': myItem[4]}
                else:
                    print "parent not found: {} ".format(myItem[1])
        # myPlayLists = collections.OrderedDict(myPlayLists)
        mySortedPlayLists = {}
        for key, PlayList in myPlayLists.iteritems():
            mySortedPlayLists[key] = {}
            for subItem in sorted(PlayList.iterkeys()):
                mySortedPlayLists[key][subItem] = PlayList[subItem]

        # for playListID, playList in mySortedPlayLists.iteritems():
        #    for playListItemID, playListItem in playList.iteritems():
        #        print "playListID {}, playListItemID {}, Naam {}, Omschr {}.".format(playListID,playListItemID,playListItem['naam'],playListItem['omschrijving'])
        return mySortedPlayLists

    def getPlayListItems(self, PlayListItem):
        # get PlayList ItemID
        myPlayListItems = []
        myRecordSet = self._DBCursor.execute('SELECT id FROM PlayLists WHERE naam = "%s" and parentID=0' % PlayListItem)
        PlayListID = None
        for myItem in myRecordSet:
            PlayListID = myItem[0]
        if PlayListID is not None:
            myRecordSet = self._DBCursor.execute(
                'SELECT id,naam,omschrijving,url FROM PlayLists WHERE parentID = %s' % PlayListID)
            for myItem in myRecordSet:
                myGenericLocation = GenericLocation(id=myItem[0],
                                                    streamUrl=myItem[3],
                                                    cameraName=myItem[1],
                                                    gps=None,
                                                    desiredPlayTime=None)
                myPlayListItems.append(myGenericLocation)
        return myPlayListItems

    def addItem(self, ItemName, ItemOmschr, ItemUrl, ParentID):
        myParentID = 0
        if ParentID is not None and ParentID.isdigit():
            myParentID = ParentID
        try:
            self._DBCursor.execute('INSERT INTO PlayLists (naam, omschrijving, url, parentID) VALUES (?,?,?,?)', \
                                   (ItemName, ItemOmschr, ItemUrl, myParentID))
            self._DBConn.commit()
        except Exception:
            print traceback.format_exc()

    def delItem(self, ItemID):
        self._DBCursor.execute('DELETE FROM PlayLists WHERE id=%s' % ItemID)
        self._DBConn.commit()

    def updateItem(self, ItemID, Name, Omschr, Url):
        try:
            if Url is not None and len(Url) > 0:
                sql = "UPDATE PlayLists SET naam='%s', omschrijving='%s', url='%s' WHERE id=%s" % (
                Name, Omschr, Url, ItemID)
            else:
                sql = "UPDATE PlayLists SET naam='%s', omschrijving='%s' WHERE id=%s" % (Name, Omschr, ItemID)
            self._DBCursor.execute(sql)
            self._DBConn.commit()
        except Exception:
            print traceback.format_exc()

    def _CheckPlayListTbl(self):
        self._DBCursor.execute(
            "CREATE TABLE IF NOT EXISTS `PlayLists` ( `id` INTEGER PRIMARY KEY AUTOINCREMENT, `naam` TEXT, `omschrijving` TEXT, `url` TEXT, `parentID` INTEGER)")
        myRecordSet = self._DBCursor.execute(
            "SELECT naam,omschrijving FROM PlayLists WHERE naam = 'Feratel Cameras'").fetchone()
        if myRecordSet is None:
            self._DBCursor.execute(
                'INSERT INTO PlayLists (naam, omschrijving,parentID) VALUES (?,?,?)',
                ('Feratel Cameras', 'Ingebouwde lijst, zie Feratel Cameras voor selectiemogelijkheden', 0))
            self._DBConn.commit()
