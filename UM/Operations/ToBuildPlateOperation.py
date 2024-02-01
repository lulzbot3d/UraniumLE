# Copyright (c) 2023 Fargo Additive Manufacturing Equipment 3D, LLC
# Uranium is released under the terms of the LGPLv3 or higher.

from UM.Scene.SceneNode import SceneNode

from . import Operation
from UM.Math.Vector import Vector


class ToBuildPlateOperation(Operation.Operation):
    """
    An operation that moves a scene node down OR UP to 0 on the y-axis.
    Basically just a GravityOperation that disregards the ZOffset decorator
    """

    def __init__(self, node):
        """Initialises this ToBuildPlateOperation.

        :param node: The node to translate.
        """

        super().__init__()
        self._node = node
        self._old_transformation = node.getLocalTransformation() # To restore the transformation to in case of an undo.

    def undo(self):
        """Undoes the ToBuildPlateOperation, restoring the old transformation."""

        self._node.setTransformation(self._old_transformation)

    def redo(self):
        """(Re-)Applies the ToBuildPlateOperation."""

        # Move to bottom of usable space (if not already there):
        height_move = -self._node.getBoundingBox().bottom
        # Disregard the ZOffset decorator if the node has one, we don't care
        if abs(height_move) > 1e-5:
            self._node.translate(Vector(0.0, height_move, 0.0), SceneNode.TransformSpace.World)

    def mergeWith(self, other):
        """Merges this operation with another ToBuildPlateOperation.

        This prevents the user from having to undo multiple operations if they
        were not his operations.

        You should ONLY merge this operation with an older operation. It is NOT
        symmetric.

        :param other: The older ToBuildPlateOperation to merge this operation with.
        """

        if type(other) is not ToBuildPlateOperation:
            return False
        if other._node != self._node: # Must be moving the same node.
            return False
        return other

    def __repr__(self):
        """Returns a programmer-readable representation of this operation.

        :return: A programmer-readable representation of this operation.
        """

        return "ToBuildPlateOp.(node={0})".format(self._node)
