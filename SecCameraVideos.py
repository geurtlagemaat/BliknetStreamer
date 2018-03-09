import os
from glob import glob


class SecCameraVideos(object):
    def __init__(self, oNodeControl):
        self._NodeControl = oNodeControl

    def getVideos(self, SelectedCam):
        myCamVideos = []
        if self._NodeControl.nodeProps.has_option('cameras', 'CameraVideosRoot'):
            CameraVideosRoot = self._NodeControl.nodeProps.get('cameras', 'CameraVideosRoot')
            if SelectedCam is None or len(SelectedCam) == 0:
                if os.path.isdir(CameraVideosRoot):
                    myFiles = [y for x in os.walk(CameraVideosRoot) for y in glob(os.path.join(x[0], '*.*'))]
                    myFiles.sort(key=os.path.getmtime)
                    for myFile in myFiles:
                        myCamVideo = {'cameranaam': os.path.basename(os.path.dirname(myFile)),
                                      'filename': os.path.basename(myFile),
                                      'size': os.path.getsize(myFile)}
                        myCamVideos.append(myCamVideo)
            else:
                myCameraPath = os.path.join(CameraVideosRoot, SelectedCam)
                if os.path.isdir(myCameraPath):
                    myFiles = [y for x in os.walk(myCameraPath) for y in glob(os.path.join(x[0], '*.*'))]
                    myFiles.sort(key=os.path.getmtime)
                    for myFile in myFiles:
                        myCamVideo = {'cameranaam': os.path.basename(os.path.dirname(myFile)),
                                      'filename': os.path.basename(myFile),
                                      'size': os.path.getsize(myFile)}
                        myCamVideos.append(myCamVideo)
        return myCamVideos

    def getCamNames(self):
        dir_list = []
        if self._NodeControl.nodeProps.has_option('cameras', 'CameraVideosRoot'):
            CameraVideosRoot = self._NodeControl.nodeProps.get('cameras', 'CameraVideosRoot')
            # list of all content in a directory, filtered so only directories are returned
            dir_list = [directory for directory in os.listdir(CameraVideosRoot) if
                        os.path.isdir(os.path.join(CameraVideosRoot, directory))]
        return dir_list
