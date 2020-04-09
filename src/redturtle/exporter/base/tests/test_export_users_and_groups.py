# -*- coding: utf-8 -*-
from redturtle.exporter.base.testing import (
    REDTURTLE_EXPORTER_BASE_INTEGRATION_TESTING,
)
from plone.app.testing import applyProfile
from AccessControl.unauthorized import Unauthorized
from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_NAME
from plone.app.testing import login
from plone.app.testing import logout
from plone.app.testing import setRoles

import unittest
import json


class WrapperTest(unittest.TestCase):

    layer = REDTURTLE_EXPORTER_BASE_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        self.request = self.layer['request']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        applyProfile(self.portal, 'redturtle.exporter.base:default')

    def test_export_users_restricted_for_admins(self):
        logout()
        self.assertRaises(
            Unauthorized, self.portal.restrictedTraverse, 'export_users'
        )

    def test_export_groups_restricted_for_admins(self):
        logout()
        self.assertRaises(
            Unauthorized, self.portal.restrictedTraverse, 'export_groups'
        )

    def test_export_users(self):
        login(self.portal, TEST_USER_NAME)
        view = self.portal.restrictedTraverse('export_users')
        res = json.loads(view())

        self.assertIn('_acl_users', res)
        users = res['_acl_users']
        self.assertIn('bob', users)
        self.assertIn('john', users)
        self.assertEqual('jdoe@plone.org', users['john']['email'])
        self.assertEqual('bob@plone.org', users['bob']['email'])
        self.assertEqual('John Doe', users['john']['properties']['fullname'])
        self.assertEqual(
            'http://www.plone.org', users['john']['properties']['home_page']
        )
        self.assertEqual('foo', users['john']['properties']['description'])
        self.assertEqual(
            {
                u'description': u'',
                u'fullname': u'',
                u'home_page': u'',
                u'location': u'',
            },
            users['bob']['properties'],
        )
        self.assertEqual(
            [u'Member', u'Reviewer', u'Authenticated', u'Editor', u'Reader'],
            users['bob']['roles'],
        )
        self.assertEqual(
            [u'Member', u'Manager', u'Authenticated'], users['john']['roles']
        )

    def test_export_groups(self):
        login(self.portal, TEST_USER_NAME)
        view = self.portal.restrictedTraverse('export_groups')
        res = json.loads(view())

        self.assertIn('_acl_groups', res)
        groups = res['_acl_groups']
        self.assertIn('staff', groups)
        self.assertIn('Administrators', groups)
        self.assertEqual(['bob'], groups['staff']['members'])
        self.assertEqual(['john'], groups['Administrators']['members'])
        self.assertEqual(
            {u'Authenticated': 1, u'Editor': 1, u'Reader': 1},
            groups['staff']['roles'],
        )
