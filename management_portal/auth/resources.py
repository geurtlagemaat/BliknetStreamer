import json

from management_portal.auth.database import CAPABILITIES, UserJSONSerializer
from management_portal.auth.decorators import requiresCapabilities
from management_portal.auth.session import getUserDatabase, getPortalSession
from management_portal.resource_base import PortalResource
from management_portal.template import render


class UsersResource(PortalResource):
    @requiresCapabilities('manage_users')
    def render_GET(self, request):
        users = getUserDatabase().getAllUsers()

        context = {
            'users': users,
            'capabilities': CAPABILITIES,
        }

        return render('users.html', context, request=request)


class UserResource(PortalResource):
    @requiresCapabilities('manage_users')
    def render_GET(self, request):
        login_name = request.args['login_name'][0]
        user = getUserDatabase().findUser(login_name)
        if user is None:
            request.setResponseCode(404, 'User not found')
            return

        return self.respondWithJSON(request, data={
            'user': UserJSONSerializer().serialize(user)
        })

    @requiresCapabilities('manage_users')
    def render_POST(self, request):
        userDict = json.loads(request.args['user'][0])

        password1 = userDict.get('password1', '')
        password2 = userDict.get('password2', '')

        if password1 and password1 != password2:
            return self.respondWithJSON(request, data={
                'error': 'passwords_not_equal',
                'message': 'Wachtwoorden niet gelijk'
            })

        if 'password1' in userDict:
            del userDict['password1']
        if 'password2' in userDict:
            del userDict['password2']

        existingUser = getUserDatabase().findUser(userDict['login_name'])
        if existingUser:
            user = existingUser
            for key, value in userDict.iteritems():
                if key in ['full_name', 'capabilities']:
                    setattr(user, key, value)
        else:
            # New user
            user = UserJSONSerializer().deserialize(userDict)

        if password1:
            user.setPassword(password1)

        getUserDatabase().createOrUpdateUser(user)
        return 'ok'

    @requiresCapabilities('manage_users')
    def render_DELETE(self, request):
        login_name = request.args['login_name'][0]
        user = getUserDatabase().findUser(login_name)
        getUserDatabase().deleteUser(user)
        return 'ok'


class LoginResource(PortalResource):
    isLeaf = True

    def __init__(self, NodeControl, redirect=None):
        self.NodeControl = NodeControl
        self.redirect = redirect

    def render_POST(self, request):
        login_name = request.args['login_name'][0]
        password = request.args['password'][0]
        ps = getPortalSession(request)
        if not ps.login(login_name, password):
            error = 'login_failed'
            return render('login.html', {'error': error}, request=request)
        else:
            nextUrl = self.redirect or '/'
            if 'next' in request.args:
                nextUrl = request.args['next'][0]
            return self.redirectRelative(request, nextUrl)

    def render_GET(self, request):
        nextUrl = None
        if 'next' in request.args:
            nextUrl = request.args['next'][0]
        return render('login.html', {'next': nextUrl}, request=request)


class LogoutResource(PortalResource):
    def __init__(self, NodeControl, redirect=None):
        self.NodeControl = NodeControl
        self.redirect = redirect

    def render_GET(self, request):
        ps = getPortalSession(request)
        ps.logout()
        return self.redirectRelative(request, self.redirect or '/')
