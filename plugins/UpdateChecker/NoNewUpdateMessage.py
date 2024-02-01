# Copyright (c) 2023 Fargo Additive Manufacturing Equipment 3D, LLC.
# Uranium is released under the terms of the LGPLv3 or higher.

from UM import i18nCatalog

from .AnnotatedUpdateMessage import AnnotatedUpdateMessage

I18N_CATALOG = i18nCatalog("uranium")

class NoNewVersionMessage(AnnotatedUpdateMessage):

    def __init__(self) -> None:
        super().__init__(
            title = I18N_CATALOG.i18nc("@info:status",
                                        "No Updates Available"),
            text = I18N_CATALOG.i18nc("@info:status",
                                         "You are still using the most current version of this software.")
        )
        self._lifetime = 10