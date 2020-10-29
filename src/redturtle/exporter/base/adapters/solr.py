# -*- coding: utf-8 -*-
from redturtle.exporter.base.interfaces import ICustomDataExporter
from zope.component import adapter
from zope.interface import implementer
from zope.interface import Interface


@adapter(Interface, Interface)
@implementer(ICustomDataExporter)
class SolrExporter(object):
    order = 3

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        """
        """
        if not getattr(self.context, "searchwords", None):
            return {}
        return {"searchwords": self.context.searchwords.raw}
