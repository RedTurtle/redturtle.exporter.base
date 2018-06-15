# -*- coding: utf-8 -*-
from .migration.topics import TopicMigrator
from .wrapper import Wrapper
from DateTime import DateTime
from plone import api
from plone.app.discussion.interfaces import IConversation
from ploneorg.jsonify.jsonify import GetItem as BaseGetItemView
from Products.CMFCore.interfaces import ISiteRoot

import json
import pprint
import sys
import traceback


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
        except Exception, error:
            if 'serializable' in str(error):
                key, context_dict = _clean_dict(context_dict, error)
                pprint.pprint(
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
            states = tmp_dict['workflow_history'].values()
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
        # nella root
        if ISiteRoot.providedBy(item):
            break
        if api.content.get_state(item, None) and api.content.get_state(item) != 'published':  # noqa
            has_private_relatives = True
            break
    context_dict.update({'is_private': has_private_relatives})


class GetPortletsData(object):

    def get_portlets_data(self):
        """
        """
        path = "/".join(self.context.getPhysicalPath())
        portal = api.portal.get()
        target = '%s/inspect-portlets' % path
        try:
            view = portal.unrestrictedTraverse('%s/inspect-portlets' % path)
        except KeyError:
            view = None
        portlets_data = []
        if view is not None:
            # BBB: we call inspector 1.0.0 view
            view.results = {}
            view.update_results(view.context)
            data_dict = view.results.get(path, {})

            for key, values_list in data_dict.iteritems():
                for value in values_list:
                    tmp = value[0].replace('<', '').replace('>', '').split('++')  # noqa
                    p_key = '++{0}++{1}'.format(tmp[1], tmp[2])
                    target = '{0}/{1}'.format(
                        "/".join(self.context.getPhysicalPath()),
                        p_key
                    )
                    portlet = portal.unrestrictedTraverse(target)
                    config_dict = portlet.__dict__.copy()
                    for k in portlet.__dict__.keys():
                        if not isinstance(config_dict[k], str) and \
                                not isinstance(config_dict[k], bool) and \
                                not isinstance(config_dict[k], int) and \
                                not isinstance(config_dict[k], unicode):
                            del config_dict[k]
                    portlets_data.append({
                        p_key: {
                            'type': value[1],
                            'config': config_dict
                        }
                    })
        return portlets_data


class GetItem(BaseGetItemView, GetPortletsData):

    def __call__(self):
        """
        Generic content-type
        """
        try:
            context_dict = Wrapper(self.context)
            if context_dict.get('_defaultpage'):
                context_dict.update({
                    'default_page': context_dict.get('_defaultpage')
                })

            get_discussion_objects(self, context_dict)
            get_solr_extrafields(self, context_dict)
            check_hierarchy_private_status(self, context_dict)

        except Exception, e:
            tb = pprint.pformat(traceback.format_tb(sys.exc_info()[2]))
            return 'ERROR: exception wrapping object: %s\n%s' % (str(e), tb)

        return get_json_object(self, context_dict)


class GetItemLink(BaseGetItemView, GetPortletsData):

    def __call__(self):
        """
        Generic content-type
        """
        try:
            context_dict = Wrapper(self.context)

            # internalLink = context_dict.get('internalLink', None)
            # externalLink = context_dict.get('externalLink', None)
            # if internalLink and internalLink != '':
            #     context_dict.update({
            #         'remoteUrl': internalLink
            #     })
            # elif externalLink and externalLink != '':
            #     context_dict.update({
            #         'remoteUrl': externalLink
            #     })

        except Exception, e:
            tb = pprint.pformat(traceback.format_tb(sys.exc_info()[2]))
            return 'ERROR: exception wrapping object: %s\n%s' % (str(e), tb)

        return get_json_object(self, context_dict)


class GetItemEvent(BaseGetItemView, GetPortletsData):

    def __call__(self):
        """
        Event
        """
        try:
            context_dict = Wrapper(self.context)
            context_dict.update({'portlets_data': self.get_portlets_data()})
            get_discussion_objects(self, context_dict)
            get_solr_extrafields(self, context_dict)
            check_hierarchy_private_status(self, context_dict)

            context_dict.update({
                'start': context_dict.get('startDate')})
            context_dict.update({
                'end': context_dict.get('endDate')})
            context_dict.update({
                'contact_name': context_dict.get('contactName')})
            context_dict.update({
                'contact_email': context_dict.get('contactEmail')})
            context_dict.update({
                'contact_phone': context_dict.get('contactPhone')})
            context_dict.update({
                'event_url': context_dict.get('eventUrl')})

        except Exception, e:
            tb = pprint.pformat(traceback.format_tb(sys.exc_info()[2]))
            return 'ERROR: exception wrapping object: %s\n%s' % (str(e), tb)

        return get_json_object(self, context_dict)


class GetItemDocument(BaseGetItemView, GetPortletsData):

    def __call__(self):
        """
        Document
        """
        try:
            context_dict = Wrapper(self.context)
            context_dict.update({
                'portlets_data': self.get_portlets_data()})
            context_dict.update({
                'table_of_contents': self.context.tableContents})
            get_discussion_objects(self, context_dict)
            get_solr_extrafields(self, context_dict)
            check_hierarchy_private_status(self, context_dict)

        except Exception, e:
            tb = pprint.pformat(traceback.format_tb(sys.exc_info()[2]))
            return 'ERROR: exception wrapping object: %s\n%s' % (str(e), tb)

        return get_json_object(self, context_dict)


class GetItemTopic(BaseGetItemView, GetPortletsData):

    def convert_criterion(self, old_criterion):
        pass

    def __call__(self):
        """
        Topic
        """
        try:
            mt = TopicMigrator()
            criterions_list = mt.__call__(self.context)
            # check format in case of date values
            for crit_dict in criterions_list:
                values = crit_dict.get('v')
                if not values:
                    continue
                if isinstance(values, int):
                    continue
                try:
                    if not any([True for x in values if isinstance(x, DateTime)]):  # noqa
                        continue
                except Exception:
                    import pdb
                    pdb.set_trace()

                new_values = []

                for val in values:
                    new_values.append(val.asdatetime().isoformat())
                if isinstance(values, tuple):
                    new_values = tuple(new_values)
                crit_dict.update({'v': new_values})

            sort_on = mt._collection_sort_on
            sort_reversed = mt._collection_sort_reversed
            context_dict = Wrapper(self.context)
            context_dict.update({'portlets_data': self.get_portlets_data()})
            context_dict.update({'query': criterions_list})
            context_dict.update({'sort_on': sort_on})
            context_dict.update({'sort_reversed': sort_reversed})
            get_solr_extrafields(self, context_dict)
            check_hierarchy_private_status(self, context_dict)

            if not context_dict.get('itemCount'):
                context_dict.update({'item_count': '30'})
            else:
                context_dict.update({
                    'item_count': context_dict.get('itemCount')})
        except Exception, e:
            tb = pprint.pformat(traceback.format_tb(sys.exc_info()[2]))
            return 'ERROR: exception wrapping object: %s\n%s' % (str(e), tb)

        return get_json_object(self, context_dict)


class GetItemCollection(BaseGetItemView, GetPortletsData):

    def __call__(self):
        """
        Collection
        """
        try:
            context_dict = Wrapper(self.context)
            query = context_dict['query']

            fixed_query = []
            for el in query:
                tmp_dict = {}
                for key in el.keys():
                    if not isinstance(el[key], basestring):
                        tmp_lst = []
                        for item in el[key]:
                            tmp_lst.append(unicode(item))
                        tmp_dict.update({unicode(key): tmp_lst})
                    else:
                        tmp_dict.update({unicode(key): unicode(el[key])})
                fixed_query.append(tmp_dict)

            context_dict.update({'query': fixed_query})
            context_dict.update({'portlets_data': self.get_portlets_data()})
            get_solr_extrafields(self, context_dict)
            check_hierarchy_private_status(self, context_dict)

        except Exception, e:
            tb = pprint.pformat(traceback.format_tb(sys.exc_info()[2]))
            return 'ERROR: exception wrapping object: %s\n%s' % (str(e), tb)

        return get_json_object(self, context_dict)
