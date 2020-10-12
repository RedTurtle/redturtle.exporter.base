# -*- coding: utf-8 -*-
from redturtle.exporter.base.browser.wrapper import Wrapper
from DateTime import DateTime
from plone import api
from plone.app.discussion.interfaces import IConversation
from plone.memoize.view import memoize
from Products.CMFCore.interfaces import ISiteRoot
from Products.Five.browser import BrowserView
from Products.CMFCore.interfaces import IFolderish

import base64
import json
import logging
import six

logger = logging.getLogger(__name__)


def _clean_dict(dct, error):
    new_dict = dct.copy()
    message = str(error)
    for key, value in dct.items():
        if message.startswith(repr(value)):
            del new_dict[key]
            return key, new_dict
    raise ValueError("Could not clean up object")


def get_json_object(self, context_dict):
    passed = False
    while not passed:
        try:
            JSON = json.dumps(context_dict)
            passed = True
        except Exception as error:
            if 'serializable' in str(error):
                key, context_dict = _clean_dict(context_dict, error)
                logger.error(
                    'Not serializable member {0} of {1} ignored'.format(
                        key, repr(self)))
                passed = False
            else:
                return ('ERROR: Unknown error serializing object: {0}'.format(
                    str(error)))

    self.request.response.setHeader('Content-Type', 'application/json')
    return JSON


def get_discussion_objects(self, context_dict):
    conversation = IConversation(self.context)
    comments = conversation.getComments()
    comments = [comment for comment in comments]
    tmp_lst = []
    for item in comments:
        tmp_dict = item.__dict__
        if not tmp_dict.get('status'):
            states = list(tmp_dict['workflow_history'].values())
            comment_status = states[0][-1]['review_state']
        try:
            del tmp_dict['__parent__']
            del tmp_dict['workflow_history']
        except Exception:
            pass
        tmp_dict['modification_date'] = DateTime(
            tmp_dict['modification_date']).asdatetime().isoformat()
        tmp_dict['creation_date'] = DateTime(
            tmp_dict['creation_date']).asdatetime().isoformat()
        if not tmp_dict.get('status'):
            tmp_dict.update({'status': comment_status})
        tmp_lst.append(tmp_dict)
    context_dict.update({'discussions': tmp_lst})


def get_solr_extrafields(self, context_dict):
    if not getattr(self.context, 'searchwords', None):
        return
    context_dict.update({'searchwords': self.context.searchwords.raw})


def check_hierarchy_private_status(self, context_dict):
    has_private_relatives = False
    relatives = self.context.aq_chain
    for item in relatives:
        if ISiteRoot.providedBy(item):
            # se è la root del sito esci
            break
        review_state = api.content.get_state(item, 'published')
        if review_state and review_state != 'published':  # noqa
            has_private_relatives = True
            break
    context_dict.update({'is_private': has_private_relatives})


def get_list_of_container_type(self, context_dict):
    fathers_type_list = []
    relatives = self.context.aq_chain
    for item in relatives:
        if ISiteRoot.providedBy(item):
            # se è la root del sito esci
            break
        fathers_type_list.append(item.portal_type)
    context_dict.update({'fathers_type_list': fathers_type_list})


def get_taxonomy_object(self, context_dict):
    context_dict.update({'taxonomies': context_dict.get('siteAreas', None)})
    if context_dict.get('siteAreas', None):
        del context_dict['siteAreas']


class BaseGetItemView(BrowserView):

    def __call__(self):
        context_dict = Wrapper(self)

        passed = False
        while not passed:
            try:
                JSON = json.dumps(context_dict)
                passed = True
            except Exception as error:
                if "serializable" in str(error):
                    key, context_dict = _clean_dict(context_dict, error)
                    logger.error(
                        'Not serializable member %s of %s ignored' % (
                            key, repr(self)
                        )
                    )
                    passed = False
                else:
                    return ('ERROR: Unknown error serializing object: {}'.format(error))  # noqa
        self.REQUEST.response.setHeader("Content-type", "application/json")
        return JSON


class BaseGetItem(BaseGetItemView):

    def __call__(self):

        context_dict = Wrapper(self.context)

        # funzioni comuni a tutti i get_item
        get_discussion_objects(self, context_dict)
        get_solr_extrafields(self, context_dict)
        check_hierarchy_private_status(self, context_dict)
        get_list_of_container_type(self, context_dict)
        get_taxonomy_object(self, context_dict)

        return context_dict


class GetItem(BaseGetItem):

    def __call__(self):
        """
        Generic content-type
        """
        context_dict = super(GetItem, self).__call__()
        if context_dict.get('_defaultpage'):
            context_dict.update({
                'default_page': context_dict.get('_defaultpage')
            })

        return get_json_object(self, context_dict)


class GetItemLink(BaseGetItem):

    def __call__(self):
        """
        Generic content-type
        """
        context_dict = super(GetItemLink, self).__call__()
        if not context_dict.get('title'):
            context_dict['title'] = context_dict.get('id')

        return get_json_object(self, context_dict)


class GetItemEvent(BaseGetItem):

    def __call__(self):
        """
        Event
        """
        context_dict = super(GetItemEvent, self).__call__()
        context_dict.update({
            'start': DateTime(context_dict.get('startDate')).asdatetime().isoformat(),  # noqa
            'end': DateTime(context_dict.get('endDate')).asdatetime().isoformat(),  # noqa
            'contact_name': context_dict.get('contactName'),
            'contact_email': context_dict.get('contactEmail'),
            'contact_phone': context_dict.get('contactPhone'),
            'event_url': context_dict.get('eventUrl'),
        })
        context_dict.pop('startDate', None)
        context_dict.pop('endDate', None)
        context_dict.pop('contactName', None)
        context_dict.pop('contactEmail', None)
        context_dict.pop('contactPhone', None)
        context_dict.pop('eventUrl', None)
        return get_json_object(self, context_dict)


class GetItemDocument(BaseGetItem):

    def __call__(self):
        """
        Document
        """
        context_dict = super(GetItemDocument, self).__call__()
        context_dict.update({
            'table_of_contents': self.context.tableContents})

        return get_json_object(self, context_dict)


class GetItemCollection(BaseGetItem):

    def __call__(self):
        """
        Collection
        """
        context_dict = super(GetItemCollection, self).__call__()
        query = context_dict['query']

        fixed_query = []
        for el in query:
            tmp_dict = {}
            for key in el.keys():
                if not isinstance(el[key], six.string_types):
                    tmp_lst = []
                    for item in el[key]:
                        tmp_lst.append(six.text_type(item))
                    tmp_dict.update({six.text_type(key): tmp_lst})
                else:
                    tmp_dict.update({six.text_type(key): six.text_type(el[key])})
            fixed_query.append(tmp_dict)

        context_dict.update({'query': fixed_query})
        context_dict['item_count'] = context_dict.get('limit', 30)
        del context_dict['limit']

        return get_json_object(self, context_dict)


class GetItemFile(BaseGetItem):

    def __call__(self):
        """
        Files from Plone 3 could have title not set.
        In this case, set it with the id
        """
        context_dict = super(GetItemFile, self).__call__()
        if not context_dict.get('title'):
            context_dict['title'] = context_dict.get('id')
        return get_json_object(self, context_dict)


class GetItemImage(BaseGetItem):

    def __call__(self):
        """
        Images from Plone 3 could have title not set.
        In this case, set it with the id
        """
        context_dict = super(GetItemImage, self).__call__()
        if not context_dict.get('title'):
            context_dict['title'] = context_dict.get('id')
        return get_json_object(self, context_dict)


class GetCatalogResults(object):

    items = []
    item_paths = []

    @property
    @memoize
    def query(self):
        query = self.request.form.get('catalog_query', {})
        if query:
            query = eval(base64.b64decode(query), {"__builtins__": None}, {})
        query.update({'sort_on': 'getObjPositionInParent'})
        return query

    @property
    @memoize
    def brains(self):
        pc = api.portal.get_tool(name='portal_catalog')
        return pc.unrestrictedSearchResults(**self.query)

    @property
    @memoize
    def uids(self):
        return [x.UID for x in self.brains]

    @property
    @memoize
    def paths(self):
        return [x.getPath() for x in self.brains]

    def flatten(self, children):
        """ Recursively flatten the tree """
        for obj in children:
            if obj['path']:
                self.items.append(obj['path'])

            children = obj.get('children', None)
            if children:
                self.flatten(children)

    def pathInList(self, path):
        path_str = '{}/'.format(path)
        for item_path in self.paths:
            if path_str in item_path:
                return True
        return False

    def explain_tree(self, root):

        results = []

        children = root.listFolderContents()
        for obj in children:
            path = obj.absolute_url_path() if not getattr(obj, "getObject", None) else obj.getPath() # noqa
            if obj.UID() not in self.uids:
                if not self.pathInList(path):
                    # object is not in catalog results and isn't neither a
                    # folder in its tree
                    continue
            obj_dict = {'path': path, 'children': []}
            if IFolderish.providedBy(obj):
                obj_dict['children'] = self.explain_tree(obj)

            results.append(obj_dict)

        return results

    def __call__(self):

        self.items = []
        query = self.request.form.get('catalog_query', {})
        if query:
            query = eval(base64.b64decode(query), {"__builtins__": None}, {})
        query.update({'sort_on': 'getObjPositionInParent'})

        self.request.response.setHeader('Content-Type', 'application/json')

        self.items = []

        root = api.portal.get()

        tree = {'children': []}
        tree['children'].extend(self.explain_tree(root))

        if tree.get('path', None):
            self.items.append(tree['path'])
        self.flatten(tree['children'])
        item_paths = self.items
        return json.dumps(item_paths)
