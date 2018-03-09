import logging

from FeratelLocations import FeratelLocations
from GenericLocations import GenericLocations
from management_portal.auth import requiresCapabilities
from management_portal.resource_base import PortalResource
from management_portal.template import render

logger = logging.getLogger(__name__)

class ShowCams(PortalResource):
    @requiresCapabilities('config')
    def render_GET(self, request):
        template = 'fragments/showcams_fragment.html'
        # data here
        myLocations = FeratelLocations(self.NodeControl)
        allCams = myLocations.getAllAvailCameras();
        myRenderedCams = render(template, {'myCams': allCams})
        return self.respondWithJSON(request, {
            'rendered': myRenderedCams
        })


class ShowFeratelHistory(PortalResource):
    @requiresCapabilities('config')
    def render_GET(self, request):
        template = 'fragments/showFeratelHistory_fragment.html'
        myLocations = FeratelLocations(self.NodeControl)
        myRenderedCams = render(template, {'myHist': myLocations.getFeratelIndexHistory()})
        return self.respondWithJSON(request, {
            'rendered': myRenderedCams
        })

class UpdateCamSubscription(PortalResource):
    @requiresCapabilities('config')
    def render_GET(self, request):
        camID = int(request.args.get('id', ['0'])[0])
        subscribed = int(request.args.get('subscribed', ['0'])[0])
        myLocations = FeratelLocations(self.NodeControl)
        myLocations.setSubscription(id=camID, subscribed=subscribed)
        data = {
            'message': 'Subscription updated...'
        }
        return self.respondWithJSON(request, data)


class UpdateGPS(PortalResource):
    @requiresCapabilities('config')
    def render_GET(self, request):
        camID = int(request.args.get('id', ['0'])[0])
        gps = (request.args.get('gps', ['0'])[0])
        myLocations = FeratelLocations(self.NodeControl)
        myLocations.setGpsData(id=camID, gps=gps)
        data = {
            'message': 'GPS Location updated...'
        }
        return self.respondWithJSON(request, data)


class GetPlayListItems(PortalResource):
    @requiresCapabilities('config')
    def render_GET(self, request):
        template = 'fragments/showPlaylists_fragment.html'
        myRenderedCams = render(template, {'playLists': GenericLocations(self.NodeControl).getPlayListsItems()})
        return self.respondWithJSON(request, {
            'rendered': myRenderedCams
        })


class UpdatePlayListItem(PortalResource):
    @requiresCapabilities('config')
    def render_GET(self, request):
        ItemID = ''
        if 'id' in request.args:
            ItemID = (request.args.get('id', ['0'])[0])
        ItemName = ''
        if 'name' in request.args:
            ItemName = (request.args.get('name', ['0'])[0])
        ItemOmschr = ''
        if 'omschr' in request.args:
            ItemOmschr = (request.args.get('omschr', ['0'])[0])
        ItemUrl = ''
        if 'url' in request.args:
            ItemUrl = (request.args.get('url', ['0'])[0])
        if ((len(ItemName) > 0) and (len(ItemID) > 0)):
            GenericLocations(self.NodeControl).updateItem(ItemID=ItemID, Name=ItemName, Omschr=ItemOmschr, Url=ItemUrl)
            data = {
                'message': 'Item %s updated' % ItemName
            }
        else:
            data = {
                'message': 'No item changed, no name of id found'
            }
        return self.respondWithJSON(request, data)


class DelPlayListItem(PortalResource):
    @requiresCapabilities('config')
    def render_GET(self, request):
        ItemID = ""
        if "id" in request.args:
            ItemID = (request.args.get('id', ['0'])[0])
        if (len(ItemID) > 0):
            GenericLocations(self.NodeControl).delItem(ItemID=ItemID)
            data = {
                'message': 'Item %s Deleted' % ItemID
            }
        else:
            data = {
                'message': 'no item deleted, no item found'
            }
        return self.respondWithJSON(request, data)


class AddPlayListItem(PortalResource):
    @requiresCapabilities('config')
    def render_GET(self, request):
        NewItemName = ""
        if "name" in request.args:
            NewItemName = (request.args.get('name', ['0'])[0])
        NewItemOmschr = ""
        if "omschr" in request.args:
            NewItemOmschr = (request.args.get('omschr', ['0'])[0])
        NewItemUrl = ""
        if "url" in request.args:
            NewItemUrl = (request.args.get('url', ['0'])[0])
        ParentID = ""
        if "parentid" in request.args:
            ParentID = (request.args.get('parentid', ['0'])[0])
        if (len(NewItemName) > 0):
            GenericLocations(self.NodeControl).addItem(ItemName=NewItemName, ItemOmschr=NewItemOmschr, \
                                                       ItemUrl=NewItemUrl, ParentID=ParentID, )
            data = {
                'message': 'Item %s added' % NewItemName
            }
        else:
            data = {
                'message': 'No item added, no name of parentid found'
            }
        return self.respondWithJSON(request, data)
