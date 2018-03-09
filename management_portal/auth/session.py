import logging

from twisted.python.components import registerAdapter
from twisted.web.server import Session
from zope.interface import Interface, Attribute, implements

logger = logging.getLogger(__name__)

userDatabase = None


def setUserDatabase(db):
    global userDatabase
    userDatabase = db


def getUserDatabase():
    global userDatabase
    return userDatabase


def getPortalSession(request):
    return IPortalSession(request.getSession())


def getCurrentUser(request):
    ps = IPortalSession(request.getSession())
    return ps.user


def checkCapabilities(request, capList):
    ps = IPortalSession(request.getSession())
    if ps.user is None:
        logger.debug('User is not logged in, so has no capabilities')
        return False

    if ps.user.super_user:
        logger.debug('User %s is super user, so has all capabilities (including requested %s)', ps.user.login_name,
                     capList)
        return True

    for cap in capList:
        if cap not in ps.user.capabilities:
            logger.debug('User %s (capabilities %s) does not have requested capabilities %s', ps.user.login_name,
                         ps.user.capabilities, capList)
            return False
    logger.debug('User %s has requested capabilities %s', ps.user.login_name, capList)
    return True


class IPortalSession(Interface):
    user = Attribute("User currently logged in")


class PortalSession(object):
    implements(IPortalSession)

    def __init__(self, session):
        self.user = None

    def logout(self):
        self.user = None

    def login(self, login_name, password):
        user = getUserDatabase().findUser(login_name)
        if user is None:
            logger.warning('User %s not logged in: user not found', login_name)
            return False

        if not user.checkPassword(password):
            logger.warning('User %s not logged in: password does not match', user.login_name)
            return False

        self.user = user
        logger.info('User %s successfully logged in', user.login_name)
        return True


registerAdapter(PortalSession, Session, IPortalSession)
