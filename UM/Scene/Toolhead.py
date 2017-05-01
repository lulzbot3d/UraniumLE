# Copyright (c) 2017 Alephobjects, Inc.
# Uranium is released under the terms of the AGPLv3 or higher.

from . import SceneNode

from UM.Application import Application
from UM.Logger import Logger
from UM.Resources import Resources
from UM.Math.Vector import Vector
from UM.Job import Job

from UM.View.GL.OpenGL import OpenGL


class Toolhead(SceneNode.SceneNode):
    def __init__(self, parent):
        super().__init__(parent)

        self._load_toolhead_job = None
        self._shader = None
        self._texture = None
        self._global_container_stack = None
        Application.getInstance().globalContainerStackChanged.connect(self._onGlobalContainerStackChanged)
        self._onGlobalContainerStackChanged()
        self.setCalculateBoundingBox(False)

    def render(self, renderer):
        if not self._shader:
            self._shader = OpenGL.getInstance().createShaderProgram(Resources.getPath(Resources.Shaders, "platform.shader"))
            if self._texture:
                self._shader.setTexture(0, self._texture)
            else:
                self._updateTexture()

        if self.getMeshData():
            renderer.queueNode(self, shader=self._shader, transparent = True, backface_cull = True, sort = -10)
            return True

    def _onGlobalContainerStackChanged(self):
        if self._global_container_stack:
            self.setMeshData(None)

        self._global_container_stack = Application.getInstance().getGlobalContainerStack()
        if self._global_container_stack:
            container = self._global_container_stack.findContainer({ "toolhead": "*" })
            if container:
                mesh_file = container.getMetaDataEntry("toolhead")
                try:
                    path = Resources.getPath(Resources.Meshes, mesh_file)
                except FileNotFoundError:
                    Logger.log("w", "Unable to find the toolhead mesh %s", mesh_file)
                    path = ""

                if self._load_toolhead_job:
                    # This prevents a previous load job from triggering texture loads.
                    self._load_toolhead_job.finished.disconnect(self._onToolheadLoaded)

                # Perform toolhead mesh loading in the background
                self._load_toolhead_job = _LoadToolheadJob(path)
                self._load_toolhead_job.finished.connect(self._onToolheadLoaded)
                self._load_toolhead_job.start()

                offset = container.getMetaDataEntry("toolhead_offset")
                if offset:
                    if len(offset) == 3:
                        self.setPosition(Vector(offset[0], offset[1], offset[2]))
                    else:
                        Logger.log("w", "Toolhead offset is invalid: %s", str(offset))
                        self.setPosition(Vector(0.0, 0.0, 0.0))
                else:
                    self.setPosition(Vector(0.0, 0.0, 0.0))

    def _updateTexture(self):
        if not self._global_container_stack or not OpenGL.getInstance():
            return

        self._texture = OpenGL.getInstance().createTexture()

        container = self._global_container_stack.findContainer({"toolhead_texture":"*"})
        if container:
            texture_file = container.getMetaDataEntry("toolhead_texture")
            self._texture.load(Resources.getPath(Resources.Images, texture_file))
        # Note: if no texture file is specified, a 1 x 1 pixel transparent image is created
        # by UM.GL.QtTexture to prevent rendering issues

        if self._shader:
            self._shader.setTexture(0, self._texture)

    def _onToolheadLoaded(self, job):
        self._load_toolhead_job = None

        if not job.getResult():
            self.setMeshData(None)
            return

        node = job.getResult()
        if node.getMeshData():
            self.setMeshData(node.getMeshData())

            # Calling later because for some reason the OpenGL context might be outdated on some computers.
            Application.getInstance().callLater(self._updateTexture)


##  Protected class that ensures that the mesh for the machine toolhead is loaded.
class _LoadToolheadJob(Job):
    def __init__(self, file_name):
        self._file_name = file_name
        self._mesh_handler = Application.getInstance().getMeshFileHandler()

    def run(self):
        reader = self._mesh_handler.getReaderForFile(self._file_name)
        if not reader:
            self.setResult(None)
            return

        self.setResult(reader.read(self._file_name))
