__all__ = ("WorldEventController", "WorldEventDialog")


def __getattr__(name):
    if name == "WorldEventController":
        from mage_maker.sections.events.controller import (
            WorldEventController,
        )

        return WorldEventController

    if name == "WorldEventDialog":
        from mage_maker.sections.events.dialog import WorldEventDialog

        return WorldEventDialog

    raise AttributeError(name)
