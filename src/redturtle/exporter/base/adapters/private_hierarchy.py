# -*- coding: utf-8 -*-
from plone import api
from Products.CMFCore.interfaces import ISiteRoot
from redturtle.exporter.base.interfaces import ICustomDataExporter
from zope.component import adapter
from zope.interface import implementer
from zope.interface import Interface


@adapter(Interface, Interface)
@implementer(ICustomDataExporter)
class PrivateHierarchyExporter(object):
    order = 1

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        """
        """
        has_private_relatives = False
        for item in self.context.aq_chain:
            if ISiteRoot.providedBy(item):
                # se è la root del sito esci
                break
            review_state = api.content.get_state(item, "published")
            if review_state and review_state != "published":
                has_private_relatives = True
                break
        return {"is_private": has_private_relatives}
