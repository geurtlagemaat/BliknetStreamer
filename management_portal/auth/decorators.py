from management_portal.auth.session import checkCapabilities, getCurrentUser


def requiresCapabilities(*capList):
    """Decorator for render method"""

    def wrapper(f):
        def inner(self, request):
            if getCurrentUser(request) is None:
                raise NotLoggedIn('Not logged in')
            if not checkCapabilities(request, capList):
                raise NotAllowed('Access denied')

            return f(self, request)

        return inner

    return wrapper


class NotLoggedIn(Exception):
    pass


class NotAllowed(Exception):
    pass
