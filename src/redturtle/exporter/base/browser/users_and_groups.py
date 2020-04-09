# -*- coding: utf-8 -*-
from Products.Five import BrowserView
from plone import api

import json


class BaseView(BrowserView):
    def __call__(self):

        data = self.get_data()
        self.request.response.setHeader("Content-type", "application/json")
        return json.dumps(data)


class ExportUsers(BaseView):
    def get_data(self):
        acl_users = api.portal.get_tool(name='acl_users')
        users = acl_users.source_users.getUsers()
        exported_users = {"_acl_users": dict()}

        for user in users:
            user_data = {
                'email': user.getProperty('email'),
                'roles': user.getRoles(),
                'properties': {
                    'fullname': user.getProperty('fullname', ''),
                    'description': user.getProperty('description', ''),
                    'location': user.getProperty('location', ''),
                    'home_page': user.getProperty('home_page', ''),
                },
            }
            exported_users['_acl_users'][user._id] = user_data
        return exported_users


class ExportGroups(BaseView):
    def get_data(self):
        acl_users = api.portal.get_tool(name='acl_users')
        groups = dict(acl_users.source_groups._groups)
        exported_groups = {"_acl_groups": dict()}
        for group in groups:
            # Loop over each group grabbing members
            members = acl_users.source_groups._group_principal_map[
                group
            ].keys()
            roles = acl_users.getGroupByName(group)._roles
            group_info = {
                'title': groups[group]['title'],
                'description': groups[group]['description'],
                'members': members,
                'roles': roles,
            }
            exported_groups['_acl_groups'][group] = group_info
        return exported_groups
