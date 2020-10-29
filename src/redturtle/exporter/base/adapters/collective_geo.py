# -*- coding: utf-8 -*-
from redturtle.exporter.base.interfaces import ICustomDataExporter
from zope.component import adapter
from zope.interface import implementer
from zope.interface import Interface


@adapter(Interface, Interface)
@implementer(ICustomDataExporter)
class CollectiveGeoExporter(object):
    order = 5

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        """
        """
        try:
            view = self.context.restrictedTraverse("@@geoview")
        except AttributeError:
            return {}
        coordinates = view.getCoordinates()
        if (
            not coordinates
            or len(coordinates) != 2  # noqa
            or coordinates == (None, None)  # noqa
        ):
            return {}

        lng, lat = coordinates[1]
        return {
            "geo": {
                "latitude": lat,
                "longitude": lng,
                "description": self.context.getLocation(),
            }
        }
