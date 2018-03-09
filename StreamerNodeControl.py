from CastDevices import CastDevices
from bliknetlib import nodeControl

class StreamerNodeControl(nodeControl.nodeControl):
    def __init__(self, propertiesfile):
        nodeControl.nodeControl.__init__(self, propertiesfile)
        self._CastDevices = CastDevices(self)

    @property
    def getCastDevices(self):
        return self._CastDevices
