# -*- coding: utf-8 -*-
from App.Common import package_home
from plone import api
from plone.app.textfield.value import RichTextValue
from Products.ATContentTypes.interfaces.interfaces import IATContentType
from Products.CMFPlone.interfaces import INonInstallable
from zope.interface import implementer
from plone.namedfile.file import NamedBlobImage
from plone.namedfile.file import NamedBlobFile

import logging
import os

logger = logging.getLogger(__name__)

SIMPLE_TEXT = '''
<p>Nunc <strong>nulla</strong>. Nullam vel sem. Ut tincidunt tincidunt erat.</p>
<p>Praesent turpis. Etiam ut purus mattis mauris sodales aliquam.</p>
<ul>
<li>one</li>
<li>two</li>
<li>three</li>
</ul>
'''

TEXT_WITH_LINK = '''
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
'''


@implementer(INonInstallable)
class HiddenProfiles(object):
    def getNonInstallableProfiles(self):
        """Hide uninstall profile from site-creation and quickinstaller."""
        return ['redturtle.exporter.base:default']


def post_install(context):
    """Create some contents"""

    portal = api.portal.get()

    # first of all create some contents
    doc = api.content.create(
        type='Document',
        title='First Document',
        description='Pellentesque habitant morbi tristique senectus',
        container=portal,
    )
    news = api.content.create(
        type='News Item',
        title='A News',
        description='In hac habitasse platea dictumst',
        container=portal,
    )
    event = api.content.create(
        type='Event', title='Event foo', container=portal
    )
    folder = api.content.create(
        type='Folder', title='Support folder', container=portal
    )
    image = api.content.create(
        type='Image', title='example image', container=portal
    )
    file_obj = api.content.create(
        type='File', title='example file', container=portal
    )
    doc2 = api.content.create(
        type='Document',
        title='Second Document',
        description='it\'s inside the folder',
        container=folder,
    )

    # Now let's add some text
    set_text(item=doc, text=SIMPLE_TEXT)
    set_text(item=news, text=SIMPLE_TEXT)
    set_text(item=doc2, text=TEXT_WITH_LINK, ref=doc.UID())
    set_image(item=image)
    set_file(item=file_obj)


def set_text(item, text, ref=''):
    if ref:
        text = text.format(uid=ref)
    if IATContentType.providedBy(item):
        item.setText(text, mimetype='text/html')
        return
    # dx content
    item.text = RichTextValue(text, 'text/html', 'text/html')


def set_image(item):
    path = os.path.join(package_home(globals()), 'example_files', 'plone.png')
    with open(path, 'rb') as fd:
        image_data = fd.read()
    item.image = NamedBlobImage(data=image_data, filename=u'plone.png')


def set_file(item):
    path = os.path.join(
        package_home(globals()), 'example_files', 'example.pdf'
    )
    with open(path, 'rb') as fd:
        file_data = fd.read()
    item.file = NamedBlobImage(data=file_data, filename=u'example.pdf')
