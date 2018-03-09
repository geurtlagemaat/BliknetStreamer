import mimetypes
import os
import traceback

from twisted.internet import reactor
from twisted.protocols.basic import FileSender
from twisted.python.log import err
from twisted.web import server, resource, static
from twisted.web.error import NoResource
from twisted.web.server import NOT_DONE_YET

from bliknetlib.nodeControl import nodeControl


class getVideo(resource.Resource):
    isLeaf = True

    def __init__(self, NodeControl):
        self.NodeControl = NodeControl
        self._CacheLocation = "cache"
        if self.NodeControl.nodeProps.has_option('streamplayer', 'cacheLocation'):
            self._CacheLocation = self.NodeControl.nodeProps.get('streamplayer', 'cacheLocation')
        self._NASMount = self.getNASLocation()

    def render_GET(self, request):
        # https://stackoverflow.com/questions/1538617/http-download-very-big-file/1657324
        if 'camid' in request.args:
            videoID = request.args.get('camid')[0]
            myEditedFileName = os.path.join(self._CacheLocation, str(videoID) + "-edit.mp4")
            myPlayListFileName = os.path.join(self._CacheLocation, str(videoID) + ".m3u8")
            finalVideoFileToServe = os.path.join(self._CacheLocation, str(videoID) + ".mp4")
            if os.path.isfile(myEditedFileName):
                finalVideoFileToServe = myEditedFileName
            elif os.path.isfile(myPlayListFileName):
                finalVideoFileToServe = myPlayListFileName
            if os.path.isfile(finalVideoFileToServe):
                request.responseHeaders.setRawHeaders("server", ["Bliknet Streamer HTTP Server"])
                # request.responseHeaders.setRawHeaders("server", ["Bliknet Streamer HTTP Server"])
                # request.responseHeaders.setRawHeaders("Content-Type", ["text/vtt;charset=utf-8"])
                request.responseHeaders.setRawHeaders("Access-Control-Allow-Origin", ["*"])
                request.responseHeaders.setRawHeaders("Content-Type", [mimetypes.guess_type(finalVideoFileToServe)[0]])
                request.responseHeaders.setRawHeaders("Content-Length", [os.path.getsize(finalVideoFileToServe)])
                rangedFile = static.File(finalVideoFileToServe, defaultType='video/octet-stream')
                return rangedFile.render_GET(request)
            else:
                return NoResource()

        elif "nasfile" in request.args and self._NASMount is not None:
            NASFileLocation = request.args.get('nasfile')[0]
            myFileName = os.path.join(self._NASMount, str(NASFileLocation))
            if os.path.isfile(myFileName):
                myMimeType = mimetypes.guess_type(myFileName)
                request.responseHeaders.setRawHeaders("server", ["Bliknet Streamer HTTP Server"])
                request.responseHeaders.setRawHeaders("Content-Type", [myMimeType])
                request.responseHeaders.setRawHeaders("Access-Control-Allow-Origin", ["*"])
                request.responseHeaders.setRawHeaders("Content-Length", [os.path.getsize(myFileName)])
                rangedFile = static.File(myFileName, defaultType=myMimeType)
                return rangedFile.render_GET(request)
            else:
                return NoResource()
        else:
            return NoResource()

    def getNASLocation(self):
        if self.NodeControl.nodeProps.has_option('videoserver', 'NASSupport') and \
                self.NodeControl.nodeProps.getboolean('videoserver', 'NASSupport') and \
                self.NodeControl.nodeProps.has_option('videoserver', 'NASRoot') and \
                        len(self.NodeControl.nodeProps.get('videoserver', 'NASRoot')) > 0:
            return self.NodeControl.nodeProps.get('videoserver', 'NASRoot')
        else:
            return None

            """try:
                fp = open(finalVideoFileToServe, 'rb')
                d = FileSender().beginFileTransfer(fp, request)

                def cbFinished(ignored):
                    fp.close()
                    request.finish()

                d.addErrback(err).addCallback(cbFinished)
                return NOT_DONE_YET
            except:
                exception = str(traceback.format_exc())
                self.NodeControl.log.error("Error opening: % s, error: %s ." % (finalVideoFileToServe, exception))
                return None  """


class getSubs(resource.Resource):
    isLeaf = True

    def __init__(self, NodeControl):
        self.NodeControl = NodeControl
        self._CacheLocation = "cache"
        if self.NodeControl.nodeProps.has_option('streamplayer', 'cacheLocation'):
            self._CacheLocation = self.NodeControl.nodeProps.get('streamplayer', 'cacheLocation')

    def render_GET(self, request):
        if 'camid' in request.args:
            videoID = request.args.get('camid')[0]
            myCachedFileName = os.path.join(self._CacheLocation, str(videoID) + ".webvtt")
            request.responseHeaders.setRawHeaders("server", ["Bliknet Streamer HTTP Server"])
            request.responseHeaders.setRawHeaders("Content-Type", ["text/vtt;charset=utf-8"])
            request.responseHeaders.setRawHeaders("Access-Control-Allow-Origin", ["*"])
            request.responseHeaders.setRawHeaders("Content-Length", [os.path.getsize(myCachedFileName)])
            try:
                fp = open(myCachedFileName, 'rb')
                d = FileSender().beginFileTransfer(fp, request)

                def cbFinished(ignored):
                    fp.close()
                    request.finish()

                d.addErrback(err).addCallback(cbFinished)
                return NOT_DONE_YET
            except:
                exception = str(traceback.format_exc())
                self.NodeControl.log.error("Error opening: % s, error: %s ." % (myCachedFileName, exception))
                return None


class getStaticHTML(resource.Resource):
    isLeaf = True

    def __init__(self, NodeControl):
        self.NodeControl = NodeControl
        self._HTMLLocation = "Static"
        if self.NodeControl.nodeProps.has_option('videoserver', 'staticLocation'):
            self._HTMLLocation = self.NodeControl.nodeProps.get('videoserver', 'staticLocation')

    def render_GET(self, request):
        if 'id' in request.args:
            htmlID = request.args.get('id')[0]
            myHTMLFileName = os.path.join(self._HTMLLocation, str(htmlID))
            myMimeType = mimetypes.guess_type(myHTMLFileName)
            request.responseHeaders.setRawHeaders("server", ["Bliknet Streamer HTTP Server"])
            # request.responseHeaders.setRawHeaders("Content-Type", ["text/html;charset=utf-8"])
            request.responseHeaders.setRawHeaders("Content-Type", [myMimeType])
            request.responseHeaders.setRawHeaders("Access-Control-Allow-Origin", ["*"])
            request.responseHeaders.setRawHeaders("Content-Length", [os.path.getsize(myHTMLFileName)])
            rangedFile = static.File(myHTMLFileName, defaultType=myMimeType)  # 'text/html'
            return rangedFile.render_GET(request)

if __name__ == '__main__':
    oNodeControl = nodeControl(r'settings/bliknetnode.conf')
    if oNodeControl.nodeProps.has_option('videoserver', 'videoPort'):
        site = server.Site(getVideo(oNodeControl))
        reactor.listenTCP(oNodeControl.nodeProps.getint('videoserver', 'videoPort'), site)

        site = server.Site(getSubs(oNodeControl))
        reactor.listenTCP(oNodeControl.nodeProps.getint('videoserver', 'subsPort'), site)

        site = server.Site(getStaticHTML(oNodeControl))
        reactor.listenTCP(oNodeControl.nodeProps.getint('videoserver', 'htmlPort'), site)
        reactor.run()
