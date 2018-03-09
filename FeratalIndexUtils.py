import os
import subprocess
import traceback
import requests
from bs4 import BeautifulSoup

# import urllib
# from twisted.internet import defer

def parseFeratelPage(FeratelLocation, NodeControl, IndexOnly=False, CB=None):
    # TODO: complete rework, exception handling etc.
    NodeControl.log.info("Start stream url %s lookup" % FeratelLocation.url)
    cacheSucces = False
    myReqHeaders = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'}
    r = requests.get(url=FeratelLocation.url, headers=myReqHeaders, timeout=20)
    if r is None or r.text is None or len(r.text)==0:
        if CB is not None:
            CB(FeratelLocation=FeratelLocation, Succes=cacheSucces)
        return

    data = r.text
    soup = BeautifulSoup(data, "html.parser")
    for sourceElem in soup.find_all("source", src=True):
        srcAttr = sourceElem["src"];
        if len(srcAttr) > 0:
            NodeControl.log.info("Found stream source: %s." % srcAttr)
            FeratelLocation.streamUrl = srcAttr
            FeratelLocation.isCamPage = True
            infoCounter = 0
            for tdElem in soup.find_all("td", {"class": "webcaminfo"}):
                if infoCounter == 0:
                    if len(tdElem.contents[1]) > 0:
                        FeratelLocation.recorded = tdElem.contents[1].strip()
                    else:
                        FeratelLocation.recorded = tdElem.contents[1]
                elif infoCounter == 1:
                    FeratelLocation.cameraName = tdElem.contents[1]
                elif infoCounter == 2:
                    if len(tdElem.contents) == 3:
                        FeratelLocation.elevation = tdElem.contents[2].getText()
                elif infoCounter == 3:
                    FeratelLocation.city = tdElem.contents[1]
                    pass
                elif infoCounter == 4:
                    FeratelLocation.region = tdElem.contents[1]
                    pass
                elif infoCounter == 5:
                    FeratelLocation.country = tdElem.contents[1]
                    pass
                infoCounter = infoCounter + 1
            if len(FeratelLocation.country) == 0:
                # alternate location lookup
                navLink = soup.find("a", {"class": "standort_txt_link TxtColor3"}, href=True)
                if navLink is not None:
                    hrefAttr = navLink["href"];
                    if len(hrefAttr) > 0:
                        startAdresssing = False;
                        adresPartCounter = 0;
                        urlTokens = hrefAttr.split("/")
                        for urlToken in urlTokens:
                            if urlToken.lower() == "webcam":
                                startAdresssing = True;
                            elif startAdresssing:
                                if adresPartCounter == 0:
                                    FeratelLocation.country = urlToken
                                elif adresPartCounter == 1:
                                    if ".html" in urlToken:
                                        FeratelLocation.city = urlToken.split('.')[0]
                                    else:
                                        FeratelLocation.region = urlToken
                                elif adresPartCounter == 2:
                                    if ".html" in urlToken:
                                        FeratelLocation.city = urlToken.split('.')[0]
                                    else:
                                        FeratelLocation.city = urlToken
                                adresPartCounter += 1
                    FeratelLocation.cameraName = navLink.getText()

            infoCounter = 0
            for tdElem in soup.find_all("td", {"class": "p_livebild_txt"}):
                if infoCounter == 0:
                    if len(tdElem.contents[0]) > 0:
                        FeratelLocation.temp = tdElem.contents[0].getText()
                if infoCounter == 1:
                    if len(tdElem.contents[0]) > 0:
                        if len(FeratelLocation.recorded) > 0:
                            FeratelLocation.recorded = FeratelLocation.recorded + " - " + tdElem.contents[
                                0].getText().strip()
                        else:
                            FeratelLocation.recorded = tdElem.contents[0].getText().strip()
                infoCounter = infoCounter + 1
            # getting gps
            mytdElem = soup.find("td", {"colspan": "3"}, onclick=True, style=True)
            if mytdElem is not None:
                onstyleAttr = mytdElem["style"]
                secondHalf = onstyleAttr.split("markers=color:red|", 1)[1]
                gpsLoc = secondHalf.split("&", 1)[0]
                if len(gpsLoc) > 0:
                    FeratelLocation.gps = gpsLoc

    if IndexOnly:
        CB(FeratelLocation=FeratelLocation)
        return
    else:
        myCacheLocation = "cache"
        if NodeControl.nodeProps.has_option('streamplayer', 'cacheLocation'):
            myCacheLocation = NodeControl.nodeProps.get('streamplayer', 'cacheLocation')
        myCachedFileName = os.path.join(myCacheLocation, str(FeratelLocation.FeratelCamID))
        NodeControl.log.info("Starting download: %s." % FeratelLocation.streamUrl)
        # feratelURL = urllib.URLopener()
        # feratelURL.retrieve(FeratelLocation.streamUrl, myCachedFileName + ".mp4")
        downloadfile(myCachedFileName + ".mp4", FeratelLocation.streamUrl, NodeControl)
        if not os.path.isfile(myCachedFileName + ".mp4"):
            NodeControl.log.info("Download: %s failed!" % FeratelLocation.streamUrl)
            CB(FeratelLocation=FeratelLocation, Succes=cacheSucces)
            return
        NodeControl.log.info("Download: %s done" % FeratelLocation.streamUrl)
        cacheSucces = True
        if NodeControl.nodeProps.has_option('Feratel', 'addMaps') and \
                NodeControl.nodeProps.getboolean('Feratel', 'addMaps'):
            if len(FeratelLocation.gps) > 0:
                gpsDir = FeratelLocation.gps.replace(".", "-").replace(",", "_").replace(" ", "")
                gpsLocation = os.path.join(myCacheLocation, 'maps', gpsDir)
                mapMoviePath = os.path.join(gpsLocation, 'maps.mp4')

                if not os.path.isdir(gpsLocation) or not os.path.isfile(mapMoviePath):
                    if not os.path.isdir(gpsLocation):
                        os.makedirs(gpsLocation)
                    myMapScale = [7, 9, 11, 13, 17]  # , 13, 17
                    mapFileList = os.path.join(gpsLocation, "mapFileList.txt")
                    fileMapFileList = open(mapFileList, "w+")
                    for i, scaleFactor in enumerate(myMapScale):
                        myURL = "http://maps.googleapis.com/maps/api/staticmap?zoom=%s&maptype=map&size=1280x720&markers=color:red|%s&sensor=false" % (
                            scaleFactor, FeratelLocation.gps)
                        f = open(os.path.join(gpsLocation, 'map-%s.png' % (i)), 'wb')
                        if isLinux():
                            myFullPath = os.path.join('map-%s.png' % (i))
                        else:
                            myFullPath = os.path.join(gpsLocation, 'map-%s.png' % (i))
                        myTmp = myFullPath.replace("\\", "/")
                        fileMapFileList.write("file %s\n" % myTmp)
                        f.write(requests.get(myURL, timeout=20).content)
                        f.close()
                    fileMapFileList.close()

                    try:
                        myArgs = ['ffmpeg', '-y', '-r', '1/6', '-f', 'concat', '-safe', '0', '-i', mapFileList, '-c:v',
                                  'libx264', '-vf', 'fps=25,format=yuv420p', mapMoviePath]
                        myProc = subprocess.Popen(myArgs, stdout=subprocess.PIPE)
                        out, err = myProc.communicate()
                        if err is not None:
                            NodeControl.log.error("error: %s" % err)
                    except Exception:
                        NodeControl.log.error("error: %s" % traceback.format_exc())
                if mapMoviePath is not None and os.path.isfile(mapMoviePath):
                    finalFileName = myCachedFileName + "-edit.mp4"

                    try:
                        mapsVideo = os.path.join(gpsLocation, "maps.mp4")
                        mapsVideoTmp = os.path.join(gpsLocation, "maps.ts")
                        mainVideo = os.path.join(myCacheLocation, '%s.mp4' % str(FeratelLocation.FeratelCamID))
                        mainVideoTmp = os.path.join(myCacheLocation, '%s.ts' % str(FeratelLocation.FeratelCamID))
                        myArgs = ['ffmpeg', '-i', mapsVideo, '-c', 'copy', '-bsf:v', 'h264_mp4toannexb', '-f', 'mpegts',
                                  '-y', mapsVideoTmp]
                        myProc = subprocess.Popen(myArgs, stdout=subprocess.PIPE)
                        out, err = myProc.communicate()
                        if err is not None:
                            NodeControl.log.error("error: %s" % err)
                        myArgs = ['ffmpeg', '-i', mainVideo, '-c', 'copy', '-bsf:v', 'h264_mp4toannexb', '-f', 'mpegts',
                                  '-y', mainVideoTmp]
                        myProc = subprocess.Popen(myArgs, stdout=subprocess.PIPE)
                        out, err = myProc.communicate()
                        if err is not None:
                            NodeControl.log.error("error: %s" % err)
                        myArgs = ['ffmpeg', '-i', 'concat:%s|%s' % (mapsVideoTmp, mainVideoTmp), '-c', 'copy', '-bsf:a',
                                  'aac_adtstoasc', '-y', finalFileName]
                        myProc = subprocess.Popen(myArgs, stdout=subprocess.PIPE)
                        out, err = myProc.communicate()
                        if err is not None:
                            NodeControl.log.error("error: %s" % err)
                    except Exception:
                        NodeControl.log.error("error: %s" % traceback.format_exc())

        if NodeControl.nodeProps.has_option('templates', 'feratelSubtitles'):
            webvttTemplate = NodeControl.nodeProps.get('templates', 'feratelSubtitles')
            if os.path.isfile(webvttTemplate):
                with open(webvttTemplate) as f:
                    subsTemplate = f.readlines()
                    f.close()
                    subtitleFile = open(myCachedFileName + ".webvtt", "w")
                    for line in subsTemplate:
                        subtitleFile.write("%s" % line)
                    subtitleFile.write("00:01.000 --> 00:10.000\n")
                    subtitleFile.write("%s\n" % FeratelLocation.getLocationInfo().encode('utf8'))
                    subtitleFile.write("00:11.000 --> 00:20.000\n")
                    subtitleFile.write("%s\n" % FeratelLocation.getRecordDateTimeInfo().encode('utf8'))
                    subtitleFile.write("00:21.000 --> 00:30.000\n")
                    subtitleFile.write("%s\n" % FeratelLocation.getTempHeightInfo().encode('utf8'))
                    subtitleFile.write("00:31.000 --> 00:40.000\n")
                    subtitleFile.write("%s\n" % FeratelLocation.getLocationInfo().encode('utf8'))
                    subtitleFile.write("00:41.000 --> 00:45.000\n")
                    subtitleFile.write("%s\n" % FeratelLocation.getRecordDateTimeInfo().encode('utf8'))
                    subtitleFile.write("00:46.000 --> 00:50.000\n")
                    subtitleFile.write("%s\n" % FeratelLocation.getTempHeightInfo().encode('utf8'))
                    subtitleFile.close()
    if CB is not None:
        CB(FeratelLocation=FeratelLocation, Succes=cacheSucces)

def downloadfile(fileLocation, url, NodeControl):
    try:
        r = requests.get(url, timeout=20)
        if r is not None:
            f = open(fileLocation, 'wb')
            for chunk in r.iter_content(chunk_size=255):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
            f.close()
    except Exception:
        NodeControl.log.error("error: %s" % traceback.format_exc())

def isLinux():
    return os.name == 'posix'
