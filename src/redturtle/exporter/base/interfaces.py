# -*- coding: utf-8 -*-
from zope.interface import Interface
from zope.publisher.interfaces.browser import IDefaultBrowserLayer
from zope.interface import Attribute


class IRedTurtleExporterBaseLayer(IDefaultBrowserLayer):
    """Marker interface that defines a browser layer."""


class ICustomDataExporter(Interface):
    """
    Append custom data
    """

    order = Attribute("The order which this adapter is run")

    def __init__(context, request):
        """Adapts context and the request.
        """

    def __call__():
        """
        """
