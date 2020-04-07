# -*- coding: utf-8 -*-
from redturtle.exporter.base.testing import (
    REDTURTLE_EXPORTER_BASE_FUNCTIONAL_TESTING,
)

from plone import api
from plone.app.testing import applyProfile
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID

import base64
import json
import unittest


class CatalogExporterViewTest(unittest.TestCase):

    layer = REDTURTLE_EXPORTER_BASE_FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        self.request = self.layer['request']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        applyProfile(self.portal, 'redturtle.exporter.base:default')
        self.view = api.content.get_view(
            name='rt_get_catalog_results',
            context=self.portal,
            request=self.request,
        )
        self.catalog = api.portal.get_tool(name='portal_catalog')

    def generate_query(self, query):
        return {"catalog_query": base64.b64encode(json.dumps(query))}

    def test_export_without_query(self):
        res = json.loads(self.view())
        self.assertEqual(len(res), 13)
        self.assertEqual(len(res), len(self.catalog()))

    def test_export_only_documents(self):
        self.request.form = self.generate_query({'portal_type': 'Document'})
        res = json.loads(self.view())
        self.assertEqual(len(res), 7)
        self.assertEqual(
            res,
            [
                u'/plone/folder-foo',
                u'/plone/folder-foo/second-document',
                u'/plone/folder-bar',
                u'/plone/folder-bar/folder-baz',
                u'/plone/folder-bar/folder-baz/third-document',
                u'/plone/first-document',
                u'/plone/document-with-empty-tags',
            ],
        )

    def test_export_only_events(self):
        self.request.form = self.generate_query({'portal_type': 'Event'})
        res = json.loads(self.view())
        self.assertEqual(len(res), 1)
        self.assertEqual(res, [u'/plone/event-foo'])

    def test_export_only_subsection(self):
        self.request.form = self.generate_query(
            {'path': '/plone/folder-bar/folder-baz'}
        )
        res = json.loads(self.view())
        self.assertEqual(len(res), 5)
        self.assertEqual(
            res,
            [
                u'/plone/folder-bar',
                u'/plone/folder-bar/folder-baz',
                u'/plone/folder-bar/folder-baz/third-document',
                u'/plone/folder-bar/folder-baz/example-image',
                u'/plone/folder-bar/folder-baz/example-file',
            ],
        )
