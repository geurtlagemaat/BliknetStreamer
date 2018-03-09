import json
import logging

from management_portal.lib.pbkdf2 import crypt

logger = logging.getLogger(__name__)


class Capability(object):
    name = ''
    description = ''

    def __init__(self, name, description):
        self.name = name
        self.description = description


CAPABILITIES = [
    Capability('manage_users', 'Gebruikers beheren'),
    Capability('view_messages', 'Messages bekijken'),
    Capability('config', 'Configuratie bekijken'),
    Capability('operational', 'Operaties')
]

"""Capability('start_ops_batch', 'OPS-batch starten'),
    Capability('view_correlation', 'Correlatiegegevens bekijken'),
    Capability('view_migration', 'Migratie-instellingen bekijken'),
    Capability('edit_migration', 'Migratie-instellingen aanpassen'), """


class User(object):
    login_name = ''
    full_name = ''
    password_hash = ''
    super_user = False

    capabilities = ['', '']

    def __init__(self, login_name, full_name=None, password_hash=None,
                 capabilities=[], super_user=False):
        self.login_name = login_name
        self.full_name = full_name
        self.password_hash = password_hash
        self.capabilities = capabilities
        self.super_user = super_user

    def setPassword(self, password):
        self.password_hash = crypt(password)

    def checkPassword(self, password):
        return self.password_hash == crypt(password, self.password_hash)

    def __eq__(self, other):
        return self.login_name == other.login_name

    def __ne__(self, other):
        return self.login_name != other.login_name

    def __repr__(self):
        return u'User(login_name=%s)' % self.login_name

    def getCapabilityDescriptions(self):
        capDescs = []
        for c in CAPABILITIES:
            if c.name in self.capabilities:
                capDescs.append(c.description)
        return capDescs


class UserDatabase(object):
    def getAllUsers(self):
        pass

    def findUser(self, login_name):
        pass

    def createOrUpdateUser(self, user):
        pass

    def deleteUser(self, user):
        pass


class JSONFileUserDatabase(UserDatabase):
    def __init__(self, filePath):
        self.filePath = filePath

    def _getUserList(self):
        try:
            with open(self.filePath, 'r') as f:
                ser = UserJSONSerializer()
                userList = []
                try:
                    userDictList = json.load(f)
                except ValueError:
                    logger.warning('Could not load user list from %s; returning empty list', self.filePath)
                    return []
                else:
                    for userDict in userDictList:
                        user = ser.deserialize(userDict)
                        userList.append(user)
                    logger.debug('Read %d users from %s', len(userList), self.filePath)
                    return userList
        except IOError:
            logger.warning('File %s could not be read; returning empty list', self.filePath)
            return []

    def _saveUserList(self, userList):
        with open(self.filePath, 'w') as f:
            ser = UserJSONSerializer()
            userDictList = []
            for user in userList:
                userDict = ser.serialize(user)
                userDictList.append(userDict)

            json.dump(userDictList, f, indent=4, sort_keys=True)
            logger.info('Wrote %d users to %s', len(userDictList), self.filePath)

    def getAllUsers(self):
        l = self._getUserList()
        l.sort(key=lambda u: u.login_name)
        return l

    def findUser(self, login_name):
        for user in self._getUserList():
            if user.login_name == login_name:
                return user

    def createOrUpdateUser(self, user):
        l = self._getUserList()

        try:
            idx = l.index(user)
        except ValueError:
            l.append(user)
            logger.info('Adding new user %s', user.login_name)
        else:
            l[idx] = user
            logger.info('Updating existing user %s', user.login_name)

        self._saveUserList(l)

    def deleteUser(self, user):
        l = self._getUserList()
        l.remove(user)
        logger.info('Removing user %s', user.login_name)
        self._saveUserList(l)


class UserJSONSerializer(object):
    def serialize(self, user):
        return user.__dict__

    #         return {
    #             'login_name': user.login_name,
    #             'full_name': user.full_name,
    #             'password_hash': user.password_hash,
    #             'capabilities': user.capabilities,
    #             'super_user': user.super_user
    #         }

    def deserialize(self, data):
        return User(**data)


def checkAdminUser(userDatabase):
    if not userDatabase.findUser('admin'):
        login_name = 'admin'
        password = 'admin'
        u = User(login_name=login_name, full_name='admin', super_user=True)
        u.setPassword(password)
        userDatabase.createOrUpdateUser(u)
        logger.warning('Created management portal super user "%s", password "%s"', login_name, password)
