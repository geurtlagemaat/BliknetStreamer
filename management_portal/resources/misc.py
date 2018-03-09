from management_portal.auth import requiresCapabilities
from management_portal.resource_base import PortalResource
from management_portal.template import render


class OperationalResource(PortalResource):
    @requiresCapabilities('operational')
    def render_GET(self, request):
        return render('operational.html', request=request)

class ConfigResource(PortalResource):
    @requiresCapabilities('config')
    def render_GET(self, request):
        return render('config.html', request=request)

class FeratelHistoryResource(PortalResource):
    @requiresCapabilities('config')
    def render_GET(self, request):
        return render('feratelHistory.html', request=request)

class ManagePlaylists(PortalResource):
    @requiresCapabilities('config')
    def render_GET(self, request):
        return render('manageplaylists.html', request=request)


class SecCams(PortalResource):
    @requiresCapabilities('operational')
    def render_GET(self, request):
        return render('securityCamVideos.html', request=request)
