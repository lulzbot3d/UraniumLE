# Copyright (c) 2017 Aleph Objects, Inc.
# Cura is released under the terms of the AGPLv3 or higher.

from UM.Mesh.MeshBuilder import MeshBuilder
from UM.Math.Vector import Vector
from UM.Scene.SceneNode import SceneNode

class Plane(SceneNode):
    def __init__(self):
        super().__init__()
        self.scale_factor = 50
        builder = MeshBuilder()
        builder.addQuad(Vector(-self.scale_factor, -self.scale_factor, 0),
                        Vector(self.scale_factor, -self.scale_factor, 0),
                        Vector(self.scale_factor, self.scale_factor, 0),
                        Vector(-self.scale_factor, self.scale_factor, 0))
        builder.addVertex(0, 0, 0.0001)
        mesh = builder.build()
        self.setMeshData(mesh)
        self.setSelectable(True)
        self.setName("Plane")

