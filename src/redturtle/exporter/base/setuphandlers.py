# -*- coding: utf-8 -*-
from App.Common import package_home
from DateTime import DateTime
from plone import api
from plone.app.textfield.value import RichTextValue
from plone.namedfile.file import NamedBlobImage
from Products.ATContentTypes.interfaces.interfaces import IATContentType
from Products.CMFPlone.interfaces import INonInstallable
from zope.interface import implementer

import logging
import os

logger = logging.getLogger(__name__)

SIMPLE_TEXT = """
<p>Nunc <strong>nulla</strong>. Nullam vel sem. Ut tincidunt tincidunt erat.</p>
<p>Praesent turpis. Etiam ut purus mattis mauris sodales aliquam.</p>
<ul>
<li>one</li>
<li>two</li>
<li>three</li>
</ul>
"""

TEXT_WITH_LINK = """
<p>
  This is an
  <a class="internal-link" href="resolveuid/{uid}" title="">
    internal link
  </a>
</p>
<p>
    This is
    <a class="external-link" href="https://www.plone.org" title="">external</a>
</p>
"""

TEXT_WITH_EMPTY_TAGS = """
<p>Foo</p>
<p> </p>
<p><strong><br /></strong></p>
<p><strong>Bar</strong></p>
<p><i> </i></p>
<p><strong> </strong></p>
<p></p>
<p><i><br /></i></p>
<i>
"""


@implementer(INonInstallable)
class HiddenProfiles(object):
    def getNonInstallableProfiles(self):
        """Hide uninstall profile from site-creation and quickinstaller."""
        return ["redturtle.exporter.base:default"]


def post_install(context):
    """Create some contents"""

    portal = api.portal.get()

    # first of all create some contents
    folder1 = api.content.create(type="Folder", title="Folder foo", container=portal)
    folder2 = api.content.create(type="Folder", title="Folder bar", container=portal)
    folder3 = api.content.create(type="Folder", title="Folder baz", container=folder2)

    doc = api.content.create(
        type="Document",
        title="First Document",
        description="Pellentesque habitant morbi tristique senectus",
        container=portal,
    )
    doc2 = api.content.create(
        type="Document",
        title="Second Document",
        description="it's inside a folder",
        container=folder1,
    )

    doc3 = api.content.create(
        type="Document",
        title="Third document",
        description="this is the defaulf view of a folder",
        container=folder3,
    )
    folder3.setDefaultPage(doc3.getId())

    doc4 = api.content.create(
        type="Document",
        title="Document with empty tags",
        description="",
        container=portal,
        effectiveDate=DateTime(),
    )

    news = api.content.create(
        type="News Item",
        title="A News",
        description="In hac habitasse platea dictumst",
        container=portal,
    )
    api.content.create(
        type="News Item",
        title="Second News",
        description="it's inside a folder",
        container=folder2,
    )

    api.content.create(type="Event", title="Event foo", container=portal)

    api.content.create(
        type="Collection",
        title="Collection item",
        container=portal,
        query=[
            {
                u"i": u"portal_type",
                u"o": u"plone.app.querystring.operation.selection.is",
                u"v": [u"Document", u"News Item"],
            }
        ],
    )

    image = api.content.create(type="Image", title="example image", container=folder3)
    file_obj = api.content.create(type="File", title="example file", container=folder3)

    # Now let's add some text and files
    set_text(item=doc, text=SIMPLE_TEXT)
    set_text(item=doc3, text=SIMPLE_TEXT)
    set_text(item=news, text=SIMPLE_TEXT)
    set_text(item=doc2, text=TEXT_WITH_LINK, ref=doc.UID())
    set_text(item=doc4, text=TEXT_WITH_EMPTY_TAGS)

    set_image(item=image)
    set_file(item=file_obj)

    #  and publish some contents
    api.content.transition(obj=folder1, transition="publish")
    api.content.transition(obj=doc, transition="publish")
    api.content.transition(obj=doc4, transition="publish")
    doc.setEffectiveDate(DateTime())
    doc4.setEffectiveDate(DateTime())
    folder1.setEffectiveDate(DateTime())

    #  finally create some users and groups
    api.user.create(
        username="john",
        email="jdoe@plone.org",
        properties=dict(
            fullname="John Doe", description="foo", home_page="http://www.plone.org"
        ),
    )
    api.user.create(username="bob", email="bob@plone.org")
    api.user.grant_roles(username="bob", roles=["Reviewer"])

    api.group.create(groupname="staff")
    group_tool = api.portal.get_tool(name="portal_groups")
    group_tool.editGroup("staff", roles=["Editor", "Reader"])
    api.group.add_user(groupname="Administrators", username="john")
    api.group.add_user(groupname="staff", username="bob")


def set_text(item, text, ref=""):
    if ref:
        text = text.format(uid=ref)
    if IATContentType.providedBy(item):
        item.setText(text, mimetype="text/html")
        return
    # dx content
    item.text = RichTextValue(text, "text/html", "text/html")


def set_image(item):
    path = os.path.join(package_home(globals()), "example_files", "plone.png")
    with open(path, "rb") as fd:
        image_data = fd.read()
    item.image = NamedBlobImage(data=image_data, filename=u"plone.png")


def set_file(item):
    path = os.path.join(package_home(globals()), "example_files", "example.pdf")
    with open(path, "rb") as fd:
        file_data = fd.read()
    item.file = NamedBlobImage(data=file_data, filename=u"example.pdf")
