# Copyright (c) 2020 Ultimaker B.V.
# Uranium is released under the terms of the LGPLv3 or higher.

from typing import Union, TYPE_CHECKING, Optional
from UM.Scene.SceneNode import SceneNode
from UM.Math.Vector import Vector

from . import Operation

if TYPE_CHECKING:
    from UM.Math.Quaternion import Quaternion  # To store the amount of rotation in each dimension.

class RotateOperation(Operation.Operation):
    """Operation that rotates a scene node."""

    def __init__(self, node: SceneNode, rotation: "Quaternion", rotate_around_point: Optional[Vector] = None) -> None:
        """Initialises the operation.

        :param node: The node to rotate.
        :param rotation: A transformation quaternion that rotates a space. This
        rotation is applied on the node.
        :param rotate_around_point: The point to rotate around.
        """

        super().__init__()
        self._node = node #The node to rotate.
        self._old_transformation = node.getLocalTransformation() #The transformation matrix before rotating, which must be restored if we undo.
        self._rotation = rotation #A rotation matrix to rotate the node with.
        self._rotate_around_point = rotate_around_point #Around what point should the rotation be done?

    def undo(self) -> None:
        """Undoes the rotation, rotating the node back."""

    def LOG_MATRIX( self, str_matrix_name, matrix ):
        Logger.log("d", "\n ................................................................... " )

        Logger.log("d", "\n %s: ", str_matrix_name  )
        if( matrix != None ):
            Logger.log("d", "%d  %d  %d  %d", matrix.at(0,0),  matrix.at(0,1), matrix.at(0,2), matrix.at(0,3) )
            Logger.log("d", "%d  %d  %d  %d", matrix.at(1,0),  matrix.at(1,1), matrix.at(1,2), matrix.at(1,3) )
            Logger.log("d", "%d  %d  %d  %d", matrix.at(2,0),  matrix.at(2,1), matrix.at(2,2), matrix.at(2,3) )
            Logger.log("d", "%d  %d  %d  %d", matrix.at(3,0),  matrix.at(3,1), matrix.at(3,2), matrix.at(3,3) )
        else:
            Logger.log("d", "\n %s in None ", str_matrix_name )

        Logger.log("d", "................................................................... \n" )

    def LOG_QUATERNION( self, str_quaternion_name, quaternion ):
        Logger.log("d", "\n ................................................................... " )
        Logger.log("d", "\n %s: ", str_quaternion_name )
        Logger.log("d", "%d  %d  %d  %d", quaternion.toMatrix().at(0,0),  quaternion.toMatrix().at(0,1), quaternion.toMatrix().at(0,2), quaternion.toMatrix().at(0,3) )
        Logger.log("d", "%d  %d  %d  %d", quaternion.toMatrix().at(1,0),  quaternion.toMatrix().at(1,1), quaternion.toMatrix().at(1,2), quaternion.toMatrix().at(1,3) )
        Logger.log("d", "%d  %d  %d  %d", quaternion.toMatrix().at(2,0),  quaternion.toMatrix().at(2,1), quaternion.toMatrix().at(2,2), quaternion.toMatrix().at(2,3) )
        Logger.log("d", "%d  %d  %d  %d", quaternion.toMatrix().at(3,0),  quaternion.toMatrix().at(3,1), quaternion.toMatrix().at(3,2), quaternion.toMatrix().at(3,3) )
        Logger.log("d", "................................................................... \n" )

    def LOG_VECTOR( self, str_vector_name, vector ):
        Logger.log("d", "\n ................................................................... " )
        Logger.log("d", "\n %s: ", str_vector_name )
        Logger.log("d", "%d  %d  %d", vector.x,  vector.y, vector.z )
        Logger.log("d", "................................................................... \n" )



    ##  Undoes the rotation, rotating the node back.
    def undo(self):
        self._node.setTransformation(self._old_transformation)

    def redo(self) -> None:
        """Redoes the rotation, rotating the node again."""
        if self._rotate_around_point:
            self._node.setPosition(-self._rotate_around_point)
        self._node.rotate(self._rotation, SceneNode.TransformSpace.World)
        if self._rotate_around_point:
            self._node.setPosition(self._rotate_around_point)

    def mergeWith(self, other: "RotateOperation") -> Union[bool, "RotateOperation"]:
        """Merges this operation with another RotateOperation.

        This prevents the user from having to undo multiple operations if they
        were not his operations.

        You should ONLY merge this operation with an older operation. It is NOT
        symmetric.

        :param other: The older RotateOperation to merge this with.
        :return: A combination of the two rotate operations.
        """

        if type(other) is not RotateOperation:
            return False
        if other._node != self._node: #Must be operations on the same node.
            return False

        op = RotateOperation(self._node, other._rotation * self._rotation)
        op._old_transformation = other._old_transformation #Use the _old_transformation of the oldest rotation in the new operation.
        return op

    def __repr__(self) -> str:
        """Returns a programmer-readable representation of this operation.

        :return: A programmer-readable representation of this operation.
        """

        return "RotateOp.(node={0},rot.={1})".format(self._node, self._rotation)
