# -*- coding: utf-8 -*-
from Products.CMFCore.interfaces import ISiteRoot
from redturtle.exporter.base.interfaces import ICustomDataExporter
from zope.component import adapter
from zope.interface import implementer
from zope.interface import Interface


@adapter(Interface, Interface)
@implementer(ICustomDataExporter)
class ParentsTypesExporter(object):
    order = 4

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        """
        """
        fathers_type_list = []
        for item in self.context.aq_chain:
            if ISiteRoot.providedBy(item):
                break
            fathers_type_list.append(item.portal_type)
        return {"fathers_type_list": fathers_type_list}
