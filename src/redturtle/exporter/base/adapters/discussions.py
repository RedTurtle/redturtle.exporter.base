# -*- coding: utf-8 -*-
from DateTime import DateTime
from plone.app.discussion.interfaces import IConversation
from redturtle.exporter.base.interfaces import ICustomDataExporter
from zope.component import adapter
from zope.interface import implementer
from zope.interface import Interface


@adapter(Interface, Interface)
@implementer(ICustomDataExporter)
class DiscussionsExporter(object):
    order = 2

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        """
        """
        conversation = IConversation(self.context)
        comments = conversation.getComments()
        comments = [comment for comment in comments]
        tmp_lst = []
        for item in comments:
            tmp_dict = item.__dict__
            if not tmp_dict.get("status"):
                states = list(tmp_dict["workflow_history"].values())
                comment_status = states[0][-1]["review_state"]
            try:
                del tmp_dict["__parent__"]
                del tmp_dict["workflow_history"]
            except Exception:
                pass
            tmp_dict["modification_date"] = (
                DateTime(tmp_dict["modification_date"])
                .asdatetime()
                .isoformat()
            )
            tmp_dict["creation_date"] = (
                DateTime(tmp_dict["creation_date"]).asdatetime().isoformat()
            )
            if not tmp_dict.get("status"):
                tmp_dict.update({"status": comment_status})
            tmp_lst.append(tmp_dict)
        return {"discussions": tmp_lst}
