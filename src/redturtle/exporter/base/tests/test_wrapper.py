# -*- coding: utf-8 -*-
from redturtle.exporter.base.testing import (
    REDTURTLE_EXPORTER_BASE_INTEGRATION_TESTING,
)
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from redturtle.exporter.base.browser.wrapper import Wrapper

import unittest


class WrapperTest(unittest.TestCase):

    layer = REDTURTLE_EXPORTER_BASE_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        self.request = self.layer['request']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self.document = api.content.create(
            container=self.portal,
            type='Document',
            title='Example document',
            subject=['foo', 'bar'],
        )
        self.news = api.content.create(
            container=self.portal,
            type='News Item',
            title='Example News Item',
            subject=['foo', 'bar'],
        )
        self.folder1 = api.content.create(
            container=self.portal, type='Folder', title='Example folder 1'
        )
        self.folder2 = api.content.create(
            container=self.portal, type='Folder', title='Example folder 2'
        )
        self.document2 = api.content.create(
            container=self.folder2,
            type='Document',
            title='Default view',
            description="this page is a default view",
        )
        self.folder2.setDefaultPage(self.document2.getId())

    def test_wrapper_document(self):
        result = Wrapper(self.document)
        self.assertEqual(result['title'], self.document.Title())
        self.assertEqual(result['subjects'], self.document.subject)
        self.assertEqual(result['_type'], self.document.portal_type)
        self.assertNotIn('description', result)
        self.assertFalse(result['_isdefaultpage'])

    def test_wrapper_default_view(self):
        result = Wrapper(self.document2)
        self.assertEqual(result['title'], self.document2.Title())
        self.assertEqual(result['_type'], self.document2.portal_type)
        self.assertTrue(result['_isdefaultpage'])

    def test_wrapper_news_item(self):
        result = Wrapper(self.news)
        self.assertEqual(result['title'], self.news.Title())
        self.assertEqual(result['subjects'], self.news.subject)
        self.assertEqual(result['_type'], self.news.portal_type)
        self.assertNotIn('description', result)

    def test_wrapper_folder(self):
        result = Wrapper(self.folder1)
        self.assertEqual(result['title'], self.folder1.Title())
        self.assertNotIn('subjects', result)
        self.assertEqual(result['_type'], self.folder1.portal_type)
        self.assertEqual(result['_defaultpage'], '')
        self.assertNotIn('_defaultitem', result)

    def test_wrapper_folder_with_default_view(self):
        result = Wrapper(self.folder2)
        self.assertEqual(result['title'], self.folder2.Title())
        self.assertEqual(result['_defaultpage'], self.document2.getId())
        self.assertIn('_defaultitem', result)
        self.assertEqual(
            result['_defaultitem']['title'], self.document2.Title()
        )
