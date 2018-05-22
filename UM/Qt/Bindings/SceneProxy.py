# Copyright (c) 2015 Ultimaker B.V.
# Uranium is released under the terms of the LGPLv3 or higher.

from PyQt5.QtCore import QObject, QCoreApplication, pyqtSlot, pyqtSignal, pyqtProperty
from UM.Scene.Selection import Selection
from UM.Scene.Iterator.DepthFirstIterator import DepthFirstIterator
from cura.Scene.CuraSceneNode import CuraSceneNode


class SceneProxy(QObject):
    def __init__(self, parent = None):
        from UM.Application import Application
        Application.getInstance().activityChanged.connect(self.onActivityChanged)
        super().__init__(parent)
        self._scene = QCoreApplication.instance().getController().getScene()
        Selection.selectionChanged.connect(self._onSelectionChanged)
    
    selectionChanged = pyqtSignal()
    activityChanged = pyqtSignal()
    def onActivityChanged(self):
        self.activityChanged.emit()

    def _onSelectionChanged(self):
        self.selectionChanged.emit()
        
    @pyqtProperty(int, notify = selectionChanged)    
    def numObjectsSelected(self):
        return Selection.getCount()
    
    @pyqtProperty(bool, notify = selectionChanged) 
    def isGroupSelected(self):
        for node in Selection.getAllSelectedObjects():
            if node.callDecoration("isGroup"):
                return True
        return False

    @pyqtSlot(str)
    def setActiveCamera(self, camera):
        self._scene.setActiveCamera(camera)

    @pyqtProperty(bool, notify = activityChanged)
    def hasObjectsOnBuildPlate(self):
        from UM.Application import Application
        active_build_plate = Application.getInstance().getBuildPlateModel().activeBuildPlate
        for node in DepthFirstIterator(Application.getInstance().getController().getScene().getRoot()):
            if (
                not issubclass(type(node), CuraSceneNode) or
                (not node.getMeshData() and not node.callDecoration("getLayerData")) or
                (node.callDecoration("getBuildPlateNumber") != active_build_plate)):

                continue
            return True
        return False

    