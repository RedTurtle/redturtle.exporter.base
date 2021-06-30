# -*- coding: utf-8 -*-
from plone import api
from Products.CMFCore.interfaces import ISiteRoot
from redturtle.exporter.base.interfaces import ICustomDataExporter
from zope.component import adapter
from zope.interface import implementer
from zope.interface import Interface


@adapter(Interface, Interface)
@implementer(ICustomDataExporter)
class SkipNCIExporter(object):
    order = 6

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        """
        """
        skip_me = False
        aq_chain = self.context.aq_chain
        for aq_item in aq_chain:
            if ISiteRoot.providedBy(aq_item):
                # se è la root del sito esci
                break
            if "-aa-" in list(aq_item.Subject()):
                skip_me = True
                break

        return {"skip_nci": skip_me}
