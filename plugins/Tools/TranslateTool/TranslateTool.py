# Copyright (c) 2022 Ultimaker B.V.
# Uranium is released under the terms of the LGPLv3 or higher.

import time
from typing import cast, List, Optional, Union

from PyQt6.QtCore import Qt, QTimer

from UM.Application import Application
from UM.Event import Event, MouseEvent, KeyEvent
from UM.Math.Float import Float
from UM.Math.Plane import Plane
from UM.Math.Vector import Vector
from UM.Operations.GroupedOperation import GroupedOperation
from UM.Operations.ToBuildPlateOperation import ToBuildPlateOperation
from UM.Operations.TranslateOperation import TranslateOperation
from UM.Scene.SceneNodeSettings import SceneNodeSettings
from UM.Scene.Selection import Selection
from UM.Scene.ToolHandle import ToolHandle
from UM.Tool import Tool

try:
    from . import TranslateToolHandle
except (ImportError, SystemError):
    import TranslateToolHandle  # type: ignore  # This fixes the tests not being able to import.


DIMENSION_TOLERANCE = 0.0001  # Tolerance value used for comparing dimensions from the UI.
DIRECTION_TOLERANCE = 0.0001  # Used to check if you're perpendicular on some axis

class TranslateTool(Tool):
    """Provides the tool to move meshes and groups.

    The tool exposes a ToolHint to show the distance of the current operation.
    """

    def __init__(self) -> None:
        super().__init__()

        self._handle = TranslateToolHandle.TranslateToolHandle() #type: TranslateToolHandle.TranslateToolHandle #Because for some reason MyPy thinks this variable contains Optional[ToolHandle].
        self._enabled_axis = [ToolHandle.XAxis, ToolHandle.YAxis, ToolHandle.ZAxis]

        self._grid_snap = False
        self._grid_size = 10
        self._moved = False

        self._shortcut_key = Qt.Key.Key_T

        self._distance_update_time = None #type: Optional[float]
        self._distance = None #type: Optional[Vector]

        self.setExposedProperties("ToolHint",
                                  "X", "Y", "Z",
                                  SceneNodeSettings.LockPosition,
                                  SceneNodeSettings.AutoDropDown)

        self._update_selection_center_timer = QTimer()
        self._update_selection_center_timer.setInterval(50)
        self._update_selection_center_timer.setSingleShot(True)
        self._update_selection_center_timer.timeout.connect(self.propertyChanged.emit)

        # Ensure that the properties (X, Y & Z) are updated whenever the selection center is changed.
        Selection.selectionCenterChanged.connect(self._onSelectionCenterChanged)

        # CURA-5966 Make sure to render whenever objects get selected/deselected.
        Selection.selectionChanged.connect(self.propertyChanged)

    def _onSelectionCenterChanged(self):
        self._update_selection_center_timer.start()

    def getX(self) -> float:
        """Get the x-location of the selection bounding box center.

        :return: X location in mm.
        """
        if Selection.hasSelection():
            return float(Selection.getBoundingBox().center.x)
        return 0.0

    def getY(self) -> float:
        """Get the y-location of the selection bounding box center.

        :return: Y location in mm.
        """
        if Selection.hasSelection():
            # Note; The switching of z & y is intentional. We display z as up for the user,
            # But store the data in openGL space.
            # direction handles the Y flip axis conversions for the UI if user has it enabled.
            direction = -1 if bool(
                Application.getInstance().getPreferences().getValue("tool/flip_y_axis_tool_handle")) else 1
            return float(Selection.getBoundingBox().center.z) * direction
        return 0.0

    def getZ(self) -> float:
        """Get the z-location of the selection bounding box bottom

        The bottom is used as opposed to the center, because the biggest use
        case is to push the selection into the build plate.
        :return: Z location in mm.
        """
        # We want to display based on the bottom instead of the actual coordinate.
        if Selection.hasSelection():
            # Note; The switching of z & y is intentional. We display z as up for the user,
            # But store the data in openGL space.
            return float(Selection.getBoundingBox().bottom)
        return 0.0

    @staticmethod
    def _parseFloat(str_value: str) -> float:
        try:
            parsed_value = float(str_value)
        except ValueError:
            parsed_value = float(0)
        return parsed_value

    def setX(self, x: str) -> None:
        """Set the x-location of the selected object(s) by translating relative to

        the selection bounding box center.
        :param x: Location in mm.
        """
        parsed_x = self._parseFloat(x)
        bounding_box = Selection.getBoundingBox()

        if not Float.fuzzyCompare(parsed_x, float(bounding_box.center.x), DIMENSION_TOLERANCE):
            selected_nodes = self._getSelectedObjectsWithoutSelectedAncestors()
            if len(selected_nodes) > 1:
                op = GroupedOperation()
                for selected_node in self._getSelectedObjectsWithoutSelectedAncestors():
                    world_position = selected_node.getWorldPosition()
                    new_position = world_position.set(x = parsed_x + (world_position.x - bounding_box.center.x))
                    node_op = TranslateOperation(selected_node, new_position, set_position = True)
                    op.addOperation(node_op)
                op.push()
            else:
                for selected_node in self._getSelectedObjectsWithoutSelectedAncestors():
                    world_position = selected_node.getWorldPosition()
                    new_position = world_position.set(x = parsed_x + (world_position.x - bounding_box.center.x))
                    TranslateOperation(selected_node, new_position, set_position = True).push()

        self._controller.toolOperationStopped.emit(self)

    def setY(self, y: str) -> None:
        """Set the y-location of the selected object(s) by translating relative to

        the selection bounding box center.
        :param y: Location in mm.
        """
        # direction handles the Y flip axis conversions for the UI if user has it enabled.
        direction = -1 if bool(
            Application.getInstance().getPreferences().getValue("tool/flip_y_axis_tool_handle")) else 1
        parsed_y = self._parseFloat(y) * direction
        bounding_box = Selection.getBoundingBox()

        if not Float.fuzzyCompare(parsed_y, float(bounding_box.center.z), DIMENSION_TOLERANCE):
            selected_nodes = self._getSelectedObjectsWithoutSelectedAncestors()
            if len(selected_nodes) > 1:
                op = GroupedOperation()
                for selected_node in selected_nodes:
                    # Note; The switching of z & y is intentional. We display z as up for the user,
                    # But store the data in openGL space.
                    world_position = selected_node.getWorldPosition()
                    new_position = world_position.set(z = parsed_y + (world_position.z - bounding_box.center.z))
                    node_op = TranslateOperation(selected_node, new_position, set_position = True)
                    op.addOperation(node_op)
                op.push()
            else:
                for selected_node in selected_nodes:
                    world_position = selected_node.getWorldPosition()
                    new_position = world_position.set(z = parsed_y + (world_position.z - bounding_box.center.z))
                    TranslateOperation(selected_node, new_position, set_position = True).push()

        self._controller.toolOperationStopped.emit(self)

    def setZ(self, z: str) -> None:
        """Set the y-location of the selected object(s) by translating relative to

        the selection bounding box bottom.
        :param z: Location in mm.
        """
        parsed_z = self._parseFloat(z)
        bounding_box = Selection.getBoundingBox()

        if not Float.fuzzyCompare(parsed_z, float(bounding_box.bottom), DIMENSION_TOLERANCE):
            selected_nodes = self._getSelectedObjectsWithoutSelectedAncestors()
            if len(selected_nodes) > 1:
                op = GroupedOperation()
                for selected_node in selected_nodes:
                    # Note: The switching of z & y is intentional. We display z as up for the user,
                    # But store the data in openGL space.
                    world_position = selected_node.getWorldPosition()
                    new_position = world_position.set(y = parsed_z + (world_position.y - bounding_box.bottom))
                    node_op = TranslateOperation(selected_node, new_position, set_position = True)
                    op.addOperation(node_op)
                op.push()
            else:
                for selected_node in selected_nodes:
                    world_position = selected_node.getWorldPosition()
                    new_position = world_position.set(y=parsed_z + (world_position.y - bounding_box.bottom))
                    TranslateOperation(selected_node, new_position, set_position=True).push()
        self._controller.toolOperationStopped.emit(self)

    def setEnabledAxis(self, axis: List[int]) -> None:
        """Set which axis/axes are enabled for the current translate operation

        :param axis: List of axes (expressed as ToolHandle enum).
        """

        self._enabled_axis = axis
        self._handle.setEnabledAxis(axis)

    def setLockPosition(self, value: bool) -> None:
        """Set lock setting to the object. This setting will be used to prevent
        model movement on the build plate.
        :param value: The setting state.
        """
        self.setSettingToSelection(SceneNodeSettings.LockPosition, value)

    def getLockPosition(self) -> Optional[bool]:
        return self.getBoolSettingFromSelection(SceneNodeSettings.LockPosition, False)

    def setAutoDropDown(self, value: bool) -> None:
        """Set auto drop down setting to the object. This setting will be used
        to make the model flush with the build plate.
        :param value: The setting state.
        """
        self.setSettingToSelection(SceneNodeSettings.AutoDropDown, value)

    def getAutoDropDown(self) -> Optional[bool]:
        default = Application.getInstance().getPreferences().getValue("physics/automatic_drop_down")
        return self.getBoolSettingFromSelection(SceneNodeSettings.AutoDropDown, default)


    def centerSelection(self) -> None:
        selected_nodes = self._getSelectedObjectsWithoutSelectedAncestors()
        if len(selected_nodes) > 1:
                op = GroupedOperation()
                big_box = Selection.getBoundingBox()
                sel_x = big_box.center.x
                sel_y = big_box.center.z
                for selected_node in selected_nodes:
                    current_pos = selected_node.getWorldPosition()
                    updated_pos = current_pos.set(x = current_pos.x - sel_x, z = current_pos.z - sel_y)
                    op.addOperation(TranslateOperation(selected_node, updated_pos, set_position = True))
                op.push()
        else:
            for selected_node in selected_nodes:
                current_z = selected_node.getWorldPosition().y
                TranslateOperation(selected_node, Vector(0, current_z, 0), set_position = True).push()
        self._controller.toolOperationStopped.emit(self)

    def dropToBuildPlate(self) -> None:
        selected_nodes = self._getSelectedObjectsWithoutSelectedAncestors()
        if len(selected_nodes) > 1:
                op = GroupedOperation()
                for selected_node in selected_nodes:
                    op.addOperation(ToBuildPlateOperation(selected_node))
                op.push()
        else:
            for selected_node in selected_nodes:
                ToBuildPlateOperation(selected_node).push()
        self._controller.toolOperationStopped.emit(self)

    def event(self, event: Event) -> bool:
        """Handle mouse and keyboard events.

        :param event: The event to handle.
        :return: Whether this event has been caught by this tool (True) or should
        be passed on (False).
        """
        super().event(event)

        # Make sure the displayed values are updated if the bounding box of the selected mesh(es) changes
        if event.type == Event.ToolActivateEvent:
            for node in self._getSelectedObjectsWithoutSelectedAncestors():
                node.boundingBoxChanged.connect(self.propertyChanged)

        if event.type == Event.ToolDeactivateEvent:
            for node in self._getSelectedObjectsWithoutSelectedAncestors():
                node.boundingBoxChanged.disconnect(self.propertyChanged)

        if event.type == Event.KeyPressEvent and cast(KeyEvent, event).key == KeyEvent.ShiftKey:
            return False

        if event.type == Event.MousePressEvent and self._controller.getToolsEnabled():
            # Start a translate operation
            if MouseEvent.LeftButton not in cast(MouseEvent, event).buttons:
                return False

            if not self._selection_pass:
                return False
            id = self._selection_pass.getIdAtPosition(cast(MouseEvent, event).x, cast(MouseEvent, event).y)
            if not id:
                return False

            if id in self._enabled_axis:
                self.setLockedAxis(id)
            elif self._handle.isAxis(id):
                return False

            self._moved = False

            camera = self._controller.getScene().getActiveCamera()
            if not camera:
                return False
            camera_direction = camera.getPosition().normalized()

            abs_x = abs(camera_direction.x)
            abs_y = abs(camera_direction.y)

            # We have to define a plane vector that is suitable for the selected toolhandle axis
            # and at the same time the camera direction should not be exactly perpendicular to the plane vector
            if id == ToolHandle.XAxis:
                plane_vector = Vector(0, camera_direction.y, camera_direction.z).normalized()
            elif id == ToolHandle.YAxis:
                plane_vector = Vector(camera_direction.x, 0, camera_direction.z).normalized()
            elif id == ToolHandle.ZAxis:
                plane_vector = Vector(camera_direction.x, camera_direction.y, 0).normalized()
            else:
                if abs_y > DIRECTION_TOLERANCE:
                    plane_vector = Vector(0, 1, 0)
                elif abs_x > DIRECTION_TOLERANCE:
                    plane_vector = Vector(1, 0, 0)
                    self.setLockedAxis(ToolHandle.ZAxis)  # Do not move y / vertical
                else:
                    plane_vector = Vector(0, 0, 1)
                    self.setLockedAxis(ToolHandle.XAxis)  # Do not move y / vertical

            self.setDragPlane(Plane(plane_vector, 0))
            return True

        if event.type == Event.MouseMoveEvent:
            # Perform a translate operation

            if not self.getDragPlane():
                return False

            x = cast(MouseEvent, event).x
            y = cast(MouseEvent, event).y

            if not self.getDragStart():
                self.setDragStart(x, y)
                return False

            drag = self.getDragVector(x, y)
            if drag:
                if self._grid_snap and drag.length() < self._grid_size:
                    return False

                if self.getLockedAxis() == ToolHandle.XAxis:
                    drag = drag.set(y = 0, z = 0)
                elif self.getLockedAxis() == ToolHandle.YAxis:
                    drag = drag.set(x = 0, z = 0)
                elif self.getLockedAxis() == ToolHandle.ZAxis:
                    drag = drag.set(x = 0, y = 0)

                if not self._moved:
                    self._moved = True
                    self._distance = Vector(0, 0, 0)
                    self.operationStarted.emit(self)

                selected_nodes = self._getSelectedObjectsWithoutSelectedAncestors()
                if len(selected_nodes) > 1:
                    op = GroupedOperation()
                    for node in selected_nodes:
                        if node.getSetting(SceneNodeSettings.LockPosition, False) == False:
                            op.addOperation(TranslateOperation(node, drag))
                    op.push()
                else:
                    for node in selected_nodes:
                        if node.getSetting(SceneNodeSettings.LockPosition, False) == False:
                            TranslateOperation(node, drag).push()

                if not self._distance:
                    self._distance = Vector(0, 0, 0)
                self._distance += drag

            self.setDragStart(x, y)

            # Rate-limit the angle change notification
            # This is done to prevent the UI from being flooded with property change notifications,
            # which in turn would trigger constant repaints.
            new_time = time.monotonic()
            if not self._distance_update_time or new_time - self._distance_update_time > 0.1:
                self.propertyChanged.emit()
                self._distance_update_time = new_time

            return True

        if event.type == Event.MouseReleaseEvent:
            # Finish a translate operation
            if self.getDragPlane():
                self.operationStopped.emit(self)
                self._distance = None
                self.propertyChanged.emit()
                self.setLockedAxis(ToolHandle.NoAxis)
                self.setDragPlane(None)
                self.setDragStart(cast(MouseEvent, event).x, cast(MouseEvent, event).y)
                return True

        return False

    def getToolHint(self) -> Optional[str]:
        """Return a formatted distance of the current translate operation.

        :return: Fully formatted string showing the distance by which the
        mesh(es) are dragged.
        """
        return "%.2f mm" % self._distance.length() if self._distance else None
