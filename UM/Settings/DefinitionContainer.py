# Copyright (c) 2022 Ultimaker B.V.
# Uranium is released under the terms of the LGPLv3 or higher.

import json
import collections
import copy

from PyQt6.QtCore import QObject, pyqtProperty
from PyQt6.QtQml import QQmlEngine

from UM.i18n import i18nCatalog #For typing.
from UM.Logger import Logger
from UM.MimeTypeDatabase import MimeTypeDatabase, MimeType
from UM.PluginObject import PluginObject
from UM.Resources import Resources
from UM.Settings.Interfaces import DefinitionContainerInterface
from UM.Settings.PropertyEvaluationContext import PropertyEvaluationContext
from UM.Settings.SettingDefinition import SettingDefinition
from UM.Settings.SettingDefinition import DefinitionPropertyType
from UM.Settings.SettingRelation import SettingRelation
from UM.Settings.SettingRelation import RelationType
from UM.Settings.SettingFunction import SettingFunction
from UM.Signal import Signal

from typing import Dict, Any, List, Optional, Set, Tuple

class InvalidDefinitionError(Exception):
    pass


class IncorrectDefinitionVersionError(Exception):
    pass


class InvalidOverrideError(Exception):
    pass

MimeTypeDatabase.addMimeType(
    MimeType(
        name = "application/x-uranium-definitioncontainer",
        comment = "Uranium Definition Container",
        suffixes = ["def.json"]
    )
)


class DefinitionContainer(QObject, DefinitionContainerInterface, PluginObject):
    """A container for SettingDefinition objects."""

    Version = 2

    def __init__(self, container_id: str, i18n_catalog: i18nCatalog = None, parent: QObject = None, *args, **kwargs) -> None:
        """Constructor

        :param container_id: A unique, machine readable/writable ID for this container.
        """

        super().__init__()
        QQmlEngine.setObjectOwnership(self, QQmlEngine.ObjectOwnership.CppOwnership)

        self._metadata = {"id": container_id,
                          "name": container_id,
                          "container_type": DefinitionContainer,
                          "version": self.Version} # type: Dict[str, Any]
        self._definitions = []                     # type: List[SettingDefinition]
        self._inherited_files = []                 # type: List[str]
        self._i18n_catalog = i18n_catalog          # type: Optional[i18nCatalog]

        self._definition_cache = {}                # type: Dict[str, SettingDefinition]
        self._path = ""

    def __setattr__(self, name: str, value: Any) -> None:
        """Reimplement __setattr__ so we can make sure the definition remains unchanged after creation."""

        super().__setattr__(name, value)
        #raise NotImplementedError()

    def __getnewargs__(self) -> Tuple[str, Optional[i18nCatalog]]:
        """For pickle support"""

        return (self.getId(), self._i18n_catalog)

    def __getstate__(self) -> Dict[str, Any]:
        """For pickle support"""

        return self.__dict__

    def __setstate__(self, state: Dict[str, Any]) -> None:
        """For pickle support"""

        # We need to call QObject.__init__() in order to initialize the underlying C++ object.
        # pickle doesn't do that so we have to do this here.
        QObject.__init__(self, parent = None)
        self.__dict__.update(state)

    def getId(self) -> str:
        """:copydoc ContainerInterface::getId

        Reimplemented from ContainerInterface
        """

        return self._metadata["id"]

    id = pyqtProperty(str, fget = getId, constant = True)

    def getName(self) -> str:
        """:copydoc ContainerInterface::getName

        Reimplemented from ContainerInterface
        """

        return self._metadata["name"]

    name = pyqtProperty(str, fget = getName, constant = True)

    def isReadOnly(self) -> bool:
        """:copydoc ContainerInterface::isReadOnly

        Reimplemented from ContainerInterface
        """

        return True

    def setReadOnly(self, read_only: bool) -> None:
        pass

    readOnly = pyqtProperty(bool, fget = isReadOnly, constant = True)

    def getPath(self) -> str:
        """:copydoc ContainerInterface::getPath.

        Reimplemented from ContainerInterface
        """

        return self._path

    def setPath(self, path: str) -> None:
        """:copydoc ContainerInterface::setPath

        Reimplemented from ContainerInterface
        """

        self._path = path

    def getMetaData(self) -> Dict[str, Any]:
        """:copydoc ContainerInterface::getMetaData

        Reimplemented from ContainerInterface
        """

        return self._metadata

    metaData = pyqtProperty("QVariantMap", fget = getMetaData, constant = True)

    @property
    def definitions(self) -> List[SettingDefinition]:
        return self._definitions

    def getInheritedFiles(self) -> List[str]:
        """Gets all ancestors of this definition container.

        This returns the definition in the "inherits" property of this
        container, and the definition in its "inherits" property, and so on. The
        ancestors are returned in order from parent to
        grand-grand-grand-...-grandparent, normally ending in a "root"
        container.

        :return: A list of ancestors, in order from near ancestor to the root.
        """

        return self._inherited_files

    def getAllKeys(self) -> Set[str]:
        """:copydoc DefinitionContainerInterface::getAllKeys

        :return: A set of all keys of settings in this container.
        """

        keys = set()  # type: Set[str]
        for definition in self.definitions:
            keys |= definition.getAllKeys()
        return keys

    def getMetaDataEntry(self, entry: str, default: Any = None) -> Any:
        """:copydoc ContainerInterface::getMetaDataEntry

        Reimplemented from ContainerInterface
        """

        return self._metadata.get(entry, default)

    def getProperty(self, key: str, property_name: str, context: PropertyEvaluationContext = None) -> Any:
        """:copydoc ContainerInterface::getProperty

        Reimplemented from ContainerInterface.
        """

        definition = self._getDefinition(key)
        if not definition:
            return None

        try:
            value = getattr(definition, property_name)
            if value is None and property_name == "value":
                value = getattr(definition, "default_value")
                if key in ["machine_start_gcode", "machine_end_gcode", "machine_wipe_gcode","machine_abort_gcode", "machine_level_x_axis_gcode",
                           "machine_extruder_start_code", "machine_extruder_end_code"]:
                    value_from_file = getattr(definition, "default_value_from_file")
                    if value_from_file != None:
                        try:
                            path = Resources.getPath(Resources.GCodes, value_from_file + ".gcode")
                            with open(path, encoding = "utf-8") as f:
                                value = f.read()
                        except FileNotFoundError:
                            return None
            return value
        except AttributeError:
            return None

    def hasProperty(self, key: str, property_name: str, ignore_inherited: bool = False) -> Any:
        """:copydoc ContainerInterface::hasProperty

        Reimplemented from ContainerInterface
        """

        definition = self._getDefinition(key)
        if not definition:
            return False
        if definition.parent is not None and ignore_inherited:
            return False
        return hasattr(definition, property_name)

    propertyChanged = Signal()
    """This signal is unused since the definition container is immutable, but is provided for API consistency."""

    metaDataChanged = Signal()

    def serialize(self, ignored_metadata_keys: Optional[Set[str]] = None) -> str:
        """:copydoc ContainerInterface::serialize

        TODO: This implementation flattens the definition container, since the
        data about inheritance and overrides was lost when deserialising.

        Reimplemented from ContainerInterface
        """

        data = {}  # type: Dict[str, Any]  # The data to write to a JSON file.
        data["name"] = self.getName()
        data["version"] = DefinitionContainer.Version
        data["metadata"] = self.getMetaData().copy()

        # Remove the keys that we want to ignore in the metadata
        if not ignored_metadata_keys:
            ignored_metadata_keys = set()
        ignored_metadata_keys |= {"name", "version", "id", "container_type"}
        for key in ignored_metadata_keys:
            if key in data["metadata"]:
                del data["metadata"][key]

        data["settings"] = {}
        for definition in self.definitions:
            data["settings"][definition.key] = definition.serialize_to_dict()

        return json.dumps(data, separators = (", ", ": "), indent = 4)  # Pretty print the JSON.

    @classmethod
    def getConfigurationTypeFromSerialized(cls, serialized: str) -> Optional[str]:
        configuration_type = None
        try:
            parsed = json.loads(serialized, object_pairs_hook = collections.OrderedDict)
            configuration_type = parsed.get("metadata", {}).get("type", "machine") #TODO: Not all definitions have a type. They get this via inheritance but that requires an instance.
        except InvalidDefinitionError as ide:
            raise ide
        except Exception as e:
            Logger.log("d", "Could not get configuration type: %s", e)
        return configuration_type

    def readAndValidateSerialized(self, serialized: str) -> Tuple[Dict[str, Any], bool]:
        parsed = json.loads(serialized, object_pairs_hook = collections.OrderedDict)

        if "inherits" in parsed:
            inherited = self._resolveInheritance(parsed["inherits"])
            parsed = self._mergeDicts(inherited, parsed, new_dict = False)

        self._verifyJson(parsed)

        is_valid = self._preprocessParsedJson(parsed)

        return parsed, is_valid

    @classmethod
    def getVersionFromSerialized(cls, serialized: str) -> Optional[int]:
        version = None
        parsed = json.loads(serialized, object_pairs_hook = collections.OrderedDict)
        try:
            version = int(parsed["version"])
        except Exception as e:
            Logger.log("d", "Could not get version from serialized: %s", e)
        return version

    # Returns whether the parsed JSON is valid.
    def _preprocessParsedJson(self, parsed: Dict[str, Any]) -> bool:
        # Pre-process the JSON data to include the overrides.
        is_valid = True
        if "overrides" in parsed:
            for key, value in parsed["overrides"].items():
                setting = self._findInDict(parsed["settings"], key)
                if setting is None:
                    Logger.log("w", "Unable to override setting %s", key)
                    is_valid = False
                else:
                    setting.update(value)

        return is_valid

    def addDefinition(self, definition: SettingDefinition) -> None:
        """Add a setting definition instance if it doesn't exist yet.

        Warning: this might not work when there are relationships higher up in the stack.
        """

        if definition.key not in [d.key for d in self._definitions]:
            self._definitions.append(definition)
            self._definition_cache[definition.key] = definition
            self._updateRelations(definition)

    def deserialize(self, serialized: str, file_name: Optional[str] = None) -> str:
        """:copydoc ContainerInterface::deserialize

        Reimplemented from ContainerInterface
        """

        # update the serialized data first
        serialized = super().deserialize(serialized, file_name)
        parsed, is_valid = self.readAndValidateSerialized(serialized)

        # Update properties with the data from the JSON
        old_id = self.getId() #The ID must be set via the constructor. Retain it.
        self._metadata = parsed["metadata"]
        self._metadata["id"] = old_id
        self._metadata["name"] = parsed["name"]
        self._metadata["version"] = self.Version #Guaranteed to be equal to what's in the parsed data by the validation.
        self._metadata["container_type"] = DefinitionContainer

        self._deserializeDefinitions(parsed["settings"])

        for definition in self._definitions:
            self._updateRelations(definition)

        return serialized

    def _deserializeDefinitions(self, settings_dict: Dict[str, Any], force_category: Optional[str] = None) -> List[SettingDefinition]:

        # When there is a forced category (= parent) present, find the category parent, create it if it doesn't exist.
        category_parent = None
        if force_category:
            category_parent = self.findDefinitions(key = force_category)
            category_parent = category_parent[0] if len(category_parent) > 0 else None

        added_definitions = []
        for key, value in settings_dict.items():
            definition = SettingDefinition(key, self, category_parent, self._i18n_catalog)
            self._definition_cache[key] = definition
            definition.deserialize(value)
            if category_parent:
                # Forced category; these are then children of that category, instead of full categories on their own.
                category_parent.children.append(definition)
            else:
                self._definitions.append(definition)
            added_definitions.append(definition)

        return added_definitions

    def appendAdditionalSettingDefinitions(self, additional_settings: Dict[str, Dict[str, Any]]) -> None:
        """
        Appends setting-definitions not defined for/by the main program (for example, a plugin) to this container.

        Additional settings are always assumed to come in the form of categories with child-settings.
        See also the Settings.AdditionalSettingDefinitionAppender class.

        :param additional_settings: A dictionary of category-name to categories, each containing setting-definitions.
        """
        try:
            merge_with_existing_categories = {}
            create_new_categories = {}

            for category, values in additional_settings.items():
                if len(self.findDefinitions(key = category)) > 0:
                    merge_with_existing_categories[category] = values
                else:
                    create_new_categories[category] = values

            added_definitions = []
            if len(create_new_categories) > 0:
                self._deserializeDefinitions(create_new_categories)
            for category, values in merge_with_existing_categories.items():
                if "children" in values:
                    for key, value in values["children"].items():
                        added_definitions += self._deserializeDefinitions({key: value}, category)
                else:
                    added_definitions += self._deserializeDefinitions(values, category)

            for definition in added_definitions:
                self._updateRelations(definition)

        except Exception as ex:
            Logger.error(f"Failed to append additional settings from external source because: {str(ex)}")

    @classmethod
    def deserializeMetadata(cls, serialized: str, container_id: str) -> List[Dict[str, Any]]:
        """Gets the metadata of a definition container from a serialised format.

        This parses the entire JSON document and only extracts the metadata from
        it.

        :param serialized: A JSON document, serialised as a string.
        :param container_id: The ID of the container (as obtained from the file name).

        :return: A dictionary of metadata that was in the JSON document in a
        singleton list. If anything went wrong, the list will be empty.
        """

        serialized = cls._updateSerialized(serialized) #Update to most recent version.
        try:
            parsed = json.loads(serialized, object_pairs_hook = collections.OrderedDict) #TODO: Load only part of this JSON until we find the metadata. We need an external library for this though.
        except json.JSONDecodeError as e:
            Logger.log("d", "Could not parse definition: %s", e)
            return []
        metadata = {} #type: Dict[str, Any]
        if "inherits" in parsed:
            import UM.Settings.ContainerRegistry #To find the definitions we're inheriting from.
            parent_metadata = UM.Settings.ContainerRegistry.ContainerRegistry.getInstance().findDefinitionContainersMetadata(id = parsed["inherits"])
            if not parent_metadata:
                Logger.log("e", "Could not load parent definition container {parent} of child {child}".format(parent = parsed["inherits"], child = container_id))
                #Ignore the parent then.
            else:
                metadata.update(parent_metadata[0])
                metadata["inherits"] = parsed["inherits"]

        metadata["container_type"] = DefinitionContainer
        metadata["id"] = container_id
        try:  # Move required fields to metadata.
            metadata["name"] = parsed["name"]
            metadata["version"] = parsed["version"]
        except KeyError as e:  # Required fields not present!
            raise InvalidDefinitionError("Missing required fields: {error_msg}".format(error_msg = str(e)))
        if "metadata" in parsed:
            metadata.update(parsed["metadata"])
        return [metadata]

    def findDefinitions(self, **kwargs: Any) -> List[SettingDefinition]:
        """Find definitions matching certain criteria.

        :param kwargs: A dictionary of keyword arguments containing key-value pairs which should match properties of
        the definition.
        """

        if len(kwargs) == 1 and "key" in kwargs:
            # If we are searching for a single definition by exact key, we can speed up things by retrieving from the cache.
            key = kwargs["key"]
            if key in self._definition_cache:
                return [self._definition_cache[key]]

        definitions = []
        for definition in self._definitions:
            definitions.extend(definition.findDefinitions(**kwargs))

        if len(kwargs) == 1 and "key" in kwargs:
            # Ensure that next time round, the definition is in the cache!
            if definitions:
                self._definition_cache[kwargs["key"]] = definitions[0]

        return definitions

    @classmethod
    def getLoadingPriority(cls) -> int:
        return 0

    # protected:

    # Load a file from disk, used to handle inheritance and includes
    def _loadFile(self, file_name: str) -> Dict[str, Any]:
        path = Resources.getPath(Resources.DefinitionContainers, file_name + ".def.json")
        with open(path, encoding = "utf-8") as f:
            contents = json.load(f, object_pairs_hook=collections.OrderedDict)

        self._inherited_files.append(path)
        return contents

    # Recursively resolve loading inherited files
    def _resolveInheritance(self, file_name: str) -> Dict[str, Any]:
        json_dict = self._loadFile(file_name)

        if "inherits" in json_dict:
            # NOTE: Since load-file isn't cached, this will load base definitions multiple times!
            inherited = self._resolveInheritance(json_dict["inherits"])
            json_dict = self._mergeDicts(inherited, json_dict)

        self._verifyJson(json_dict)

        return json_dict

    # Verify that a loaded json matches our basic expectations.
    def _verifyJson(self, json_dict: Dict[str, Any]):
        required_fields = {"version", "name", "settings", "metadata"}
        missing_fields = required_fields - json_dict.keys()
        if missing_fields:
            raise InvalidDefinitionError("Missing required properties: {properties}".format(properties = ", ".join(missing_fields)))

        if json_dict["version"] != self.Version:
            raise IncorrectDefinitionVersionError("Definition uses version {0} but expected version {1}".format(json_dict["version"], self.Version))

    # Recursively find a key in a dictionary
    def _findInDict(self, dictionary: Dict[str, Any], key: str) -> Any:
        if key in dictionary:
            return dictionary[key]
        for v in dictionary.values():
            if isinstance(v, dict):
                item = self._findInDict(v, key)
                if item is not None:
                    return item

    def _mergeDicts(self, first: Dict[Any, Any], second: Dict[Any, Any], new_dict = True) -> Dict[Any, Any]:
        """
        Recursively merge a dictionary. It will return a new dict if new_dict is true (default)
        :param first: First dictionary to merge
        :param second: Second dictionary
        :param new_dict: Should a new dict be created or should the first dict be updated in place?
        :return: Merged dict
        """
        if new_dict:
            result = copy.deepcopy(first)
        else:
            result = first
        for key, value in second.items():
            if key in result:
                if isinstance(value, dict):
                    result[key] = self._mergeDicts(result[key], value, new_dict = new_dict)
                else:
                    result[key] = value
            else:
                result[key] = value

        return result

    # Recursively update relations of settings
    def _updateRelations(self, definition: SettingDefinition) -> None:
        for property_name in SettingDefinition.getPropertyNames(DefinitionPropertyType.Function):
            self._processFunction(definition, property_name)

        for child in definition.children:
            self._updateRelations(child)

    # Create relation objects for all settings used by a certain function
    def _processFunction(self, definition: SettingDefinition, property_name: str) -> None:
        try:
            function = getattr(definition, property_name)
        except AttributeError:
            return

        settings_dependencies = set()

        if isinstance(function, SettingFunction):
            settings_dependencies.update(function.getUsedSettingKeys())

        try:
            settings_dependencies.update(definition.force_depends_on_settings)
        except AttributeError:
            pass

        for setting in settings_dependencies:
            # Prevent circular relations between the same setting and the same property
            # Note that the only property used by SettingFunction is the "value" property, which
            # is why this is hard coded here.
            if setting == definition.key and property_name == "value":
                Logger.log("w", "Found circular relation for property 'value' between {0} and {1}", definition.key, setting)
                continue

            other = self._getDefinition(setting)
            if not other:
                other = SettingDefinition(setting)

            relation = SettingRelation(definition, other, RelationType.RequiresTarget, property_name)
            definition.relations.append(relation)

            relation = SettingRelation(other, definition, RelationType.RequiredByTarget, property_name)
            other.relations.append(relation)

    def _getDefinition(self, key: str) -> Optional[SettingDefinition]:
        definition = None
        if key in self._definition_cache:
            definition = self._definition_cache[key]
        else:
            definitions = self.findDefinitions(key = key)
            if definitions:
                definition = definitions[0]
                self._definition_cache[key] = definition

        return definition

    def isDirty(self) -> bool:
        return False

    def __str__(self) -> str:
        """Simple short string representation for debugging purposes."""
        return "<DefContainer '{definition_id}'>".format(definition_id = self.getId())

    def __repr__(self) -> str:
        return str(self)

    def __hash__(self) -> int:
        return hash(self.getId())
