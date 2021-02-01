# -*- coding: utf-8 -*-
from .migration.topics import TopicMigrator
from DateTime import DateTime
from plone import api
from plone.memoize.view import memoize
from Products.CMFCore.interfaces import IFolderish
from Products.Five.browser import BrowserView
from redturtle.exporter.base.browser.wrapper import Wrapper
from redturtle.exporter.base.interfaces import ICustomDataExporter
from zope.component import subscribers

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


class GetItem(BrowserView):
    def __call__(self):

        data = self.get_data()
        return self.get_json_object(data)

    def get_data(self):
        context_dict = Wrapper(self.context)

        # custom exporters
        handlers = [
            x
            for x in subscribers(
                (self.context, self.request), ICustomDataExporter
            )
        ]
        for handler in sorted(handlers, key=lambda h: h.order):
            context_dict.update(handler())
        if context_dict.get("_defaultpage"):
            context_dict.update(
                {"default_page": context_dict.get("_defaultpage")}
            )
        return context_dict

    def get_json_object(self, context_dict):
        passed = False
        while not passed:
            try:
                JSON = json.dumps(context_dict)
                passed = True
            except Exception as error:
                if "serializable" in str(error):
                    key, context_dict = _clean_dict(context_dict, error)
                    logger.error(
                        "Not serializable member {0} of {1} ignored".format(
                            key, repr(self)
                        )
                    )
                    passed = False
                else:
                    return "ERROR: Unknown error serializing object: {0}".format(
                        str(error)
                    )

        self.request.response.setHeader("Content-Type", "application/json")
        return JSON


class GetItemLink(GetItem):
    def get_data(self):
        """
        """
        data = super(GetItemLink, self).get_data()
        if not data.get("title"):
            data["title"] = data.get("id")
        return data


class GetItemEvent(GetItem):
    def get_data(self):
        """
        """
        data = super(GetItemEvent, self).get_data()
        data.update(
            {
                "start": DateTime(data.get("startDate"))
                .asdatetime()
                .isoformat(),
                "end": DateTime(data.get("endDate")).asdatetime().isoformat(),
                "contact_name": data.get("contactName"),
                "contact_email": data.get("contactEmail"),
                "contact_phone": data.get("contactPhone"),
                "event_url": data.get("eventUrl"),
            }
        )
        data.pop("startDate", None)
        data.pop("endDate", None)
        data.pop("contactName", None)
        data.pop("contactEmail", None)
        data.pop("contactPhone", None)
        data.pop("eventUrl", None)
        return data


class GetItemDocument(GetItem):
    def get_data(self):
        """
        """
        data = super(GetItemDocument, self).get_data()
        data.update({"table_of_contents": self.context.tableContents})

        return data


class GetItemTopic(GetItem):
    def convert_criterion(self, old_criterion):
        pass

    def get_data(self):
        """
        """
        data = super(GetItemTopic, self).get_data()

        mt = TopicMigrator()
        criterions_list = mt.__call__(self.context)
        # check format in case of date values
        for crit_dict in criterions_list:
            values = crit_dict.get("v")
            if not values:
                continue
            if isinstance(values, int):
                continue
            if not any(
                [True for x in values if isinstance(x, DateTime)]
            ):  # noqa
                continue

            new_values = []

            for val in values:
                new_values.append(val.asdatetime().isoformat())
            if isinstance(values, tuple):
                new_values = tuple(new_values)
            crit_dict.update({"v": new_values})

        sort_on = mt._collection_sort_on
        sort_reversed = mt._collection_sort_reversed

        data.update({"query": criterions_list})
        data.update({"sort_on": sort_on})
        data.update({"sort_reversed": sort_reversed})

        if not data.get("itemCount"):
            data.update({"item_count": "30"})
        else:
            data.update({"item_count": data.get("itemCount")})
        return data


class GetItemCollection(GetItem):
    def get_data(self):
        """
        """
        data = super(GetItemCollection, self).get_data()
        query = data["query"]

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
                    tmp_dict.update(
                        {six.text_type(key): six.text_type(el[key])}
                    )
            fixed_query.append(tmp_dict)

        data.update({"query": fixed_query})
        data["item_count"] = data.get("limit", 30)
        del data["limit"]

        return data


class GetItemFile(GetItem):
    def get_data(self):
        """
        Files from Plone 3 could have title not set.
        In this case, set it with the id
        """
        data = super(GetItemFile, self).get_data()
        if not data.get("title"):
            data["title"] = data.get("id")
        return data


class GetItemImage(GetItem):
    def get_data(self):
        """
        Images from Plone 3 could have title not set.
        In this case, set it with the id
        """
        data = super(GetItemImage, self).get_data()
        if not data.get("title"):
            data["title"] = data.get("id")
        return data


class GetCatalogResults(object):

    items = []
    item_paths = []

    @property
    @memoize
    def query(self):
        query = self.request.form.get("catalog_query", {})
        if query:
            query = eval(base64.b64decode(query), {"__builtins__": None}, {})
        query.update({"sort_on": "getObjPositionInParent"})
        return query

    @property
    @memoize
    def brains(self):
        pc = api.portal.get_tool(name="portal_catalog")
        if api.env.plone_version() < "5.2":
            return pc.unrestrictedSearchResults(**self.query)
        return pc(**self.query)

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
            if obj["path"]:
                self.items.append(obj["path"])

            children = obj.get("children", None)
            if children:
                self.flatten(children)

    def pathInList(self, path):
        path_str = "{}/".format(path)
        for item_path in self.paths:
            if path_str in item_path:
                return True
        return False

    def explain_tree(self, root):

        results = []

        children = root.listFolderContents()
        for obj in children:
            path = (
                obj.absolute_url_path()
                if not getattr(obj, "getObject", None)
                else obj.getPath()
            )  # noqa
            if obj.UID() not in self.uids:
                if not self.pathInList(path):
                    # object is not in catalog results and isn't neither a
                    # folder in its tree
                    continue
            obj_dict = {"path": path, "children": []}
            if IFolderish.providedBy(obj):
                obj_dict["children"] = self.explain_tree(obj)

            results.append(obj_dict)

        return results

    def __call__(self):

        self.items = []
        query = self.request.form.get("catalog_query", {})
        if query:
            query = eval(base64.b64decode(query), {"__builtins__": None}, {})
        query.update({"sort_on": "getObjPositionInParent"})

        self.request.response.setHeader("Content-Type", "application/json")

        self.items = []

        root = api.portal.get()
        tree = {"children": []}
        tree["children"].extend(self.explain_tree(root))

        if tree.get("path", None):
            self.items.append(tree["path"])
        self.flatten(tree["children"])
        item_paths = self.items
        return json.dumps(item_paths)
