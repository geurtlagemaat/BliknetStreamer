import logging
import traceback

from FeratelLocations import FeratelLocations
from GenericLocations import GenericLocations
from SecCameraVideos import SecCameraVideos
from management_portal.auth import requiresCapabilities
from management_portal.resource_base import PortalResource
from management_portal.template import render
from twisted.internet import reactor

logger = logging.getLogger(__name__)
# TODO, afstemmen met de NodeControl logger

class CastCommandGateway(PortalResource):
    @requiresCapabilities('operational')
    def render_GET(self, request):
        logger.info('Received ToggleFeratelPlay command')
        try:
            targetDevice = request.args.get('devicename')[0]
            cmd = request.args.get('cmd')[0]
            randomParam = False
            if 'random' in request.args and request.args.get('random')[0] == '1':
                randomParam = True
            playlistParam = None
            if 'playlist' in request.args:
                playlistParam = request.args.get('playlist')[0]
            myCastCommands = self.NodeControl.getCastDevices
            myCastCommands.setCommand(CastDevice=targetDevice,
                                      Command=cmd,
                                      Random=randomParam,
                                      PlayList=playlistParam,
                                      AppId=None)
            data = {
                'message': 'CastCommandGateway, Cast Device: %s, status is %s...' % (targetDevice, cmd)
            }
            return self.respondWithJSON(request, data)
        except:
            exception = str(traceback.format_exc())
            data = {
                'message': 'Error during ToggleFeratelPlay: ' + exception
            }
            return self.respondWithJSON(request, data)

class GetCastDevices(PortalResource):
    @requiresCapabilities('operational')
    def render_GET(self, request):
        logger.info('Received GetCastDevices command')
        castDevices = self.NodeControl.getCastDevices.getCastDevices()
        myLocations = GenericLocations(self.NodeControl)
        playLists = myLocations.getPlayLists()
        template = 'fragments/showCastDevices_fragment.html'
        myRenderedCastDevices = render(template, {'myCastDevices': castDevices, 'playLists': playLists})
        return self.respondWithJSON(request, {
            'rendered': myRenderedCastDevices
        })


class DoRefreshCastDevices(PortalResource):
    # doDiscoverCastDevices
    @requiresCapabilities('operational')
    def render_GET(self, request):
        logger.info('Received DoRefreshCastDevices')
        try:
            self.NodeControl.getCastDevices.doDiscoverCastDevices()
            castDevices = self.NodeControl.getCastDevices.getCastDevices()
            myLocations = GenericLocations(self.NodeControl)
            playLists = myLocations.getPlayLists()
            template = 'fragments/showCastDevices_fragment.html'
            myRenderedCastDevices = render(template, {'myCastDevices': castDevices, 'playLists': playLists})
            return self.respondWithJSON(request, {
                'rendered': myRenderedCastDevices
            })
        except:
            exception = str(traceback.format_exc())
            data = {
                'message': 'Error during DoRefreshCastDevices: ' + exception
            }
            return self.respondWithJSON(request, data)

class DoFeratelIndex(PortalResource):
    @requiresCapabilities('operational')
    def render_GET(self, request):
        logger.info('Received DoFeratelIndex')
        try:
            myLocations = FeratelLocations(self.NodeControl)
            myLocations.doIndex()
            data = {
                'message': 'FeratelIndex gereed!'
            }
            return self.respondWithJSON(request, data)
        except:
            exception = str(traceback.format_exc())
            data = {
                'message': 'Error during DoFeratelIndex: ' + exception
            }
            return self.respondWithJSON(request, data)

class GetSecCameraVideoIndex(PortalResource):
    @requiresCapabilities('operational')
    def render_GET(self, request):
        logger.info('Received GetSecCameraVideoIndex')
        try:
            SelectedCam = None
            if 'selcam' in request.args:
                SelectedCam = request.args.get('selcam')[0]
            myCamVideos = SecCameraVideos(self.NodeControl)
            videos = myCamVideos.getVideos(SelectedCam)
            template = 'fragments/showCamVideos_fragment.html'
            myRenderedCamVideos = render(template, {'myCamVideos': videos})
            return self.respondWithJSON(request, {
                'rendered': myRenderedCamVideos
            })
        except:
            exception = str(traceback.format_exc())
            data = {
                'message': 'Error during GetSecCameraVideoIndex: ' + exception
            }
            return self.respondWithJSON(request, data)

class GetSecCameraNames(PortalResource):
    @requiresCapabilities('operational')
    def render_GET(self, request):
        logger.info('Received GetSecCameraNames')
        try:
            myCamVideos = SecCameraVideos(self.NodeControl)
            CamNames = myCamVideos.getCamNames()
            template = 'fragments/showCamNames_fragment.html'
            myRenderedCamNames = render(template, {'myCamNames': CamNames})
            return self.respondWithJSON(request, {
                'rendered': myRenderedCamNames
            })
        except:
            exception = str(traceback.format_exc())
            data = {
                'message': 'Error during GetSecCameraNames: ' + exception
            }
            return self.respondWithJSON(request, data)