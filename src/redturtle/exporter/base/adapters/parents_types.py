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
        parents_type_list = []
        for item in self.context.aq_chain:
            if item == self.context:
                # skip current context
                continue
            if ISiteRoot.providedBy(item):
                break
            parents_type_list.append(item.portal_type)
        try:
            parent_uid = self.context.aq_parent.UID()
        except AttributeError:
            parent_uid = ""
        return {
            "parents_type_list": parents_type_list,
            "parent_uid": parent_uid,
        }
