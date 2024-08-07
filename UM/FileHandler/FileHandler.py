# Copyright (c) 2021 Ultimaker B.V.
# Uranium is released under the terms of the LGPLv3 or higher.

from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING, cast

from .FileReader import FileReader
from .FileWriter import FileWriter
from PyQt6.QtCore import QFileInfo, QObject, pyqtProperty, pyqtSlot, QUrl

from UM.Logger import Logger
from UM.Platform import Platform
from UM.PluginRegistry import PluginRegistry

from UM.i18n import i18nCatalog
i18n_catalog = i18nCatalog("uranium")

if TYPE_CHECKING:
    from UM.Qt.QtApplication import QtApplication


def resolveAnySymlink(file_name: str) -> str:
    """ Some OSs have different extensions for linked files (for example, one possibility is .lnk-files on Windows).
    In such cases, the literal .lnk file will be attempted to open, not the file this resolves:
    """

    info = QFileInfo(file_name)
    if info.exists() and info.isSymLink():  # Use 'exists': Not certain to be a literal file, depending on subclass.
        file_name = info.symLinkTarget()
    return file_name


class FileHandler(QObject):
    """Central class for reading and writing meshes.
    This class is created by Application and handles reading and writing mesh files.
    """

    def __init__(self, application: "QtApplication", writer_type: str = "unknown_file_writer", reader_type: str = "unknown_file_reader", parent: QObject = None) -> None:
        if cast(FileHandler, self.__class__).__instance is not None:
            raise RuntimeError("Try to create singleton '%s' more than once" % self.__class__.__name__)

        super().__init__(parent)
        cast(FileHandler, self.__class__).__instance = self

        self._application = application
        self._readers = {} # type: Dict[str, FileReader]
        self._writers = {} # type: Dict[str, FileWriter]

        self._writer_type = writer_type # type: str
        self._reader_type = reader_type # type: str

        self._add_to_recent_files_hints = [] # type: List[QUrl]

        PluginRegistry.addType(self._writer_type, self.addWriter)
        PluginRegistry.addType(self._reader_type, self.addReader)

    @pyqtProperty("QStringList", constant = True)
    def supportedReadFileTypes(self) -> List[str]:
        file_types = []
        all_types = []

        # Adding a quick filter that only shows you 3D Model files
        files_3d = ["stl", "obj", "x3d", "ctm", "dae", "glb", "gltf", "ply", "zae", "3mf", "amf"]
        model_types = []

        if Platform.isLinux():
            for ext, desc in self.getSupportedFileTypesRead().items():
                file_types.append("{0} (*.{1} *.{2})".format(desc, ext.lower(), ext.upper()))
                all_types.append("*.{0} *.{1}".format(ext.lower(), ext.upper()))
                if ext.lower() in files_3d:
                    model_types.append("*.{0} *.{1}".format(ext.lower(), ext.upper()))
        else:
            for ext, desc in self.getSupportedFileTypesRead().items():
                file_types.append("{0} (*.{1})".format(desc, ext))
                all_types.append("*.{0}".format(ext))
                if ext.lower() in files_3d:
                    model_types.append("*.{0}".format(ext.lower()))

        file_types.sort()
        file_types.insert(0, i18n_catalog.i18nc("@item:inlistbox", "All Supported Types ({0})", " ".join(all_types)))
        file_types.insert(0, i18n_catalog.i18nc("@item:inlistbox", "3D Model Files ({0})", " ".join(model_types)))
        file_types.append(i18n_catalog.i18nc("@item:inlistbox", "All Files (*)"))

        return file_types

    @pyqtProperty("QStringList", constant = True)
    def supportedWriteFileTypes(self) -> List[str]:
        file_types = []

        for item in self.getSupportedFileTypesWrite():
            file_types.append("{0} (*.{1})".format(item["description"], item["extension"]))

        file_types.sort()

        return file_types

    @pyqtSlot(QUrl, bool)
    @pyqtSlot(QUrl)
    def readLocalFile(self, file: QUrl, add_to_recent_files_hint: bool = True) -> None:
        if not file.isValid():
            return
        if add_to_recent_files_hint:
            self._add_to_recent_files_hints.append(file)
        self._readLocalFile(file, add_to_recent_files_hint)

    def _readLocalFile(self, file: QUrl, add_to_recent_files_hint: bool = True) -> None:
        raise NotImplementedError("_readLocalFile needs to be implemented by subclasses")

    def getSupportedFileTypesWrite(self) -> List[Dict[str, Union[str, int]]]:
        """Get list of all supported filetypes for writing.
        :return: List of dicts containing id, extension, description and mime_type for all supported file types.
        """

        supported_types = []
        meta_data = PluginRegistry.getInstance().getAllMetaData(filter={self._writer_type: {}}, active_only=True)
        for entry in meta_data:
            for output in entry[self._writer_type].get("output", []):
                ext = output.get("extension", "")
                description = output.get("description", ext)
                mime_type = output.get("mime_type", "text/plain")
                mode = output.get("mode", FileWriter.OutputMode.TextMode)
                hide_in_file_dialog = output.get("hide_in_file_dialog", False)
                supported_types.append({
                    "id": entry["id"],
                    "extension": ext,
                    "description": description,
                    "mime_type": mime_type,
                    "mode": mode,
                    "hide_in_file_dialog": hide_in_file_dialog,
                })
        return supported_types

    # Get list of all supported file types for reading.
    # \returns For each supported file type, the description of the plug-in.
    def getSupportedFileTypesRead(self) -> Dict[str, str]:
        supported_types = {}
        meta_data = PluginRegistry.getInstance().getAllMetaData(filter={self._reader_type: {}}, active_only=True)
        for entry in meta_data:
            if self._reader_type in entry:
                for input_type in entry[self._reader_type]:
                    ext = input_type.get("extension", None)
                    if ext:
                        description = input_type.get("description", ext)
                        supported_types[ext] = description
        return supported_types

    def addReader(self, reader: "FileReader") -> None:
        self._readers[reader.getPluginId()] = reader

    def addWriter(self, writer: "FileWriter") -> None:
        self._writers[writer.getPluginId()] = writer

    # Try to read the data from a file using a specified Reader.
    # \param reader Reader to read the file with.
    # \param file_name The name of the file to load.
    # \param kwargs Keyword arguments.
    # \returns None if nothing was found
    def readerRead(self, reader, file_name: str, **kwargs: Any):
        raise NotImplementedError("readerRead must be implemented by subclasses.")

    def getWriterByMimeType(self, mime: str) -> Optional["FileWriter"]:
        """Get a mesh writer object that supports writing the specified mime type

        :param mime: The mime type that should be supported.
        :return: A FileWriter instance or None if no mesh writer supports the specified mime type. If there are multiple
        writers that support the specified mime type, the first entry is returned.
        """

        writer_data = PluginRegistry.getInstance().getAllMetaData(filter={self._writer_type: {}}, active_only=True)
        for entry in writer_data:
            for output in entry[self._writer_type].get("output", []):
                if mime == output["mime_type"]:
                    return self._writers[entry["id"]]

        return None

    def getWriter(self, writer_id: str) -> Optional["FileWriter"]:
        """Get an instance of a mesh writer by ID"""

        if writer_id not in self._writers:
            return None

        return self._writers[writer_id]

    def getReaderForFile(self, file_name: str) -> Optional["FileReader"]:
        """Find a Reader that accepts the given file name.
        :param file_name: The name of file to load.
        :returns: Reader that accepts the given file name. If no acceptable Reader is found None is returned.
        """

        file_name = resolveAnySymlink(file_name)
        for id, reader in self._readers.items():
            try:
                if reader.acceptsFile(file_name):
                    return reader
            except Exception as e:
                Logger.log("e", str(e))

        return None

    __instance = None   # type: FileHandler

    @classmethod
    def getInstance(cls, *args, **kwargs) -> "FileHandler":
        return cls.__instance
