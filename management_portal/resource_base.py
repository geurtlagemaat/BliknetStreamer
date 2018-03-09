import json
import platform

import datetime
from twisted.python._url import URL
from twisted.web import http
from twisted.web.resource import Resource
from twisted.web.util import redirectTo


def currentDateTime():
    dt = datetime.datetime.now()
    return "{0:0>2}-{1:0>2}-{2:0>2} {3:0>2}:{4:0>2}:{5:0>2}".format(dt.year, dt.month, dt.day, dt.hour, dt.minute,
                                                                    dt.second)


class PortalResource(Resource):
    """Base class for portal resources, with convenient access to the BSI"""
    isLeaf = True

    def __init__(self, NodeControl):
        Resource.__init__(self)
        self.NodeControl = NodeControl

    def render(self, request):
        """Process request
         
        @type request: twisted.web.http.Request"""
        # Import here to prevent circular import
        from management_portal.auth.decorators import NotAllowed, NotLoggedIn
        try:
            return Resource.render(self, request)
        except NotLoggedIn:
            myTmp = self.redirectRelative(request, '/login?next=' + request.path)
            request.setResponseCode(http.UNAUTHORIZED)
            return myTmp
        except NotAllowed:
            return self.redirectRelative(request, '/')

    def respondWithJSON(self, request, data):
        request.setHeader('Content-Type', 'application/json')
        if isinstance(data, dict):
            data['node'] = platform.node()
            data['dateTime'] = currentDateTime()

        return json.dumps(data, indent=4)

    def redirectRelative(self, request, path):
        url = URL.fromText(request.uri).click(unicode(path))
        return redirectTo(url.asText().encode('utf-8'), request)
