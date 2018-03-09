import logging
import os

import management_portal.auth.resources as auth_resources
import management_portal.resources.config_resources as config_resources
import management_portal.resources.misc as misc_resources
import management_portal.resources.operational as operational_resources
from management_portal.auth import JSONFileUserDatabase, setUserDatabase, \
    getPortalSession, checkAdminUser
from management_portal.resource_base import PortalResource
from management_portal.template import render
from twisted.internet import reactor
from twisted.web.resource import Resource
from twisted.web.server import Site
from twisted.web.static import File

logger = logging.getLogger(__name__)

SCRIPT_DIR = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))

# The following resources are registered below the root (e.g. /operational)
RESOURCES = {
    # Main pages
    'operational': misc_resources.OperationalResource,
    'config': misc_resources.ConfigResource,
    'feratelHistory': misc_resources.FeratelHistoryResource,
    'managePlaylists': misc_resources.ManagePlaylists,
    'seccams': misc_resources.SecCams,

    'showCams': config_resources.ShowCams,
    'showFeratelHistory': config_resources.ShowFeratelHistory,
    'sendCastCommand': operational_resources.CastCommandGateway,
    'getCastDevices': operational_resources.GetCastDevices,
    'doFeratelIndex': operational_resources.DoFeratelIndex,
    'doRefreshCastDevices': operational_resources.DoRefreshCastDevices,

    'updateCamSubscription': config_resources.UpdateCamSubscription,
    'updateGPS': config_resources.UpdateGPS,

    'getSecCamNames': operational_resources.GetSecCameraNames,
    'getSecCamVideos': operational_resources.GetSecCameraVideoIndex,

    'getPlayListItems': config_resources.GetPlayListItems,
    'addPlayListItem': config_resources.AddPlayListItem,
    'updatePlayListItem': config_resources.UpdatePlayListItem,
    'delPlayListItem': config_resources.DelPlayListItem,

    'login': auth_resources.LoginResource,
    'logout': auth_resources.LogoutResource,
    'users': auth_resources.UsersResource,
    'user': auth_resources.UserResource
}


def startPortal(NodeControl, listenPort=None, listenAddress='', userDatabasePath=None):
    """Start the management portal on the given port and address"""
    if listenPort is None:
        listenPort = 8890

    createAdminUser = False
    if not os.path.exists(userDatabasePath):
        createAdminUser = True

    userDatabase = JSONFileUserDatabase(userDatabasePath)
    setUserDatabase(userDatabase)

    if createAdminUser:
        checkAdminUser(userDatabase)

    logger.info('Starting management portal on address %s, port %d; using user database %s', listenAddress, listenPort,
                userDatabasePath)
    portalResource = ManagementPortalResource(NodeControl=NodeControl, subResources=RESOURCES)
    site = Site(portalResource)
    reactor.listenTCP(listenPort, site, interface=listenAddress)  # @UndefinedVariable


class ManagementPortalResource(Resource):
    """Root resource for the management portal"""
    # This resource contains subresources
    isLeaf = False

    def __init__(self, NodeControl, subResources):
        Resource.__init__(self)
        self.NodeControl = NodeControl

        # Serve static files from the static dir
        staticFilesDir = os.path.join(SCRIPT_DIR, 'static')
        self.putChild('static', File(staticFilesDir))

        # Register subresources
        for name, resourceClass in subResources.iteritems():
            kwargs = {}
            if issubclass(resourceClass, PortalResource):
                kwargs = {'NodeControl': NodeControl}
            self.putChild(name, resourceClass(**kwargs))

    def getChild(self, name, request):
        if name == '':
            return self
        return Resource.getChild(self, name, request)

    def render_GET(self, request):
        ps = getPortalSession(request)
        return render('welcome.html', {'user': ps.user}, request=request)
