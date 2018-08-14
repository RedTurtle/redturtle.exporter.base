# -*- coding: utf-8 -*-
from Acquisition import aq_base
from plone import api
from ploneorg.jsonify.wrapper import Wrapper as BaseWrapper
from Products.CMFCore.utils import getToolByName
from redturtle.exporter.base import logger

import base64
import DateTime
import os

SKIP_FIELDS = [
    'ComputedField',
    'CarouselProviderField',
    'InterfaceMarkerField',
    'ExtensionBooleandField',
    'ReferenceDataGridField',
    'ExtensionColumnsField',
    '_ExtensionWidthField',
    '_ExtensionHeightField',
    'ExtentionTextField',
    'ReverseInterfaceField',
    'ExtensionBooleanField',
]

STANDARD_FIELDS = [
    'StringField', 'BooleanField', 'LinesField',
    'IntegerField', 'TextField', 'SimpleDataGridField',
    'FloatField', 'FixedPointField', 'TALESString',
    'TALESLines', 'ZPTField', 'DataGridField', 'EmailField',
    'QueryField', '_StringExtensionField',
]

BLOB_FIELDS = [
    'ImageField',
    'FileField',
    'AttachmentField',
    'ExtensionBlobField',
    'BlobField',
]


class Wrapper(BaseWrapper):
    """ Gets the data in a format that can be used by the
        transmogrifier blueprints in collective.jsonmigrator
    """

    def __init__(self, context):
        self.context = context
        self._context = aq_base(context)
        self.portal = api.portal.get()
        self.portal_path = '/'.join(self.portal.getPhysicalPath())
        self.portal_utils = api.portal.get_tool(name='plone_utils')
        self.charset = getattr(self.portal.portal_properties.site_properties, 'default_charset', None)  # noqa
        if not self.charset:
            # never seen it missing ... but users can change it
            self.charset = 'utf-8'

        for method in dir(self):
            if method.startswith('get_'):
                getattr(self, method)()

        getattr(self, 'get_general_settings')()

    def get_general_settings(self):
        try:
            if self.context.isDiscussable():
                self['allow_discusion'] = True
            if self.context.getExcludeFromNav():
                self['exclude_from_nav'] = True
            if self.context.getEffectiveDate():
                self['effective_date'] = self.context.getEffectiveDate().asdatetime().isoformat()  # noqa
            if self.context.getExpirationDate():
                self['expiration_date'] = self.context.getExpirationDate().asdatetime().isoformat()  # noqa
        except Exception:
            pass

    def get_defaultview(self):
        """ Default view of object
            :keys: _layout, _defaultpage
        """
        topic_mapping_views = {
            'atct_album_view': 'album_view',
            'folder_listing': 'listing_view',
            'folder_summary_view': 'summary_view',
            'folder_tabular_view': 'tabular_view',
            'folder_full_view': 'full_view',
            'atct_topic_view': 'listing_view',
        }
        if self['_classname'] in ['ATTopic', 'ATFolder']:
            _browser = self.context.getLayout()
            self['_layout'] = topic_mapping_views.get(_browser)
            if not self['_layout']:
                self['_layout'] = _browser
            if self.context.getDefaultPage():
                self['_defaultpage'] = self.context.getDefaultPage()
        else:
            try:
                _browser = '/'.join(
                    self.portal_utils.browserDefault(self.context)[1])
                if _browser not in ['folder_listing', 'index_html']:
                    self['_layout'] = ''
                    self['_defaultpage'] = _browser
            except AttributeError:
                _browser = self.context.getLayout()
                self['_layout'] = _browser
                self['_defaultpage'] = ''

    def get_archetypes_fields(self):
        """ If Archetypes is used then dump schema
        """

        try:
            from Products.Archetypes.interfaces import IBaseObject
            if not IBaseObject.providedBy(self.context):
                return
        except Exception:
            return

        fields = self.context.Schema().fields()
        for field in fields:
            self.set_field_value(field)

    def set_field_value(self, field):
        type_ = field.__class__.__name__
        fieldname = unicode(field.__name__)
        if type_ in SKIP_FIELDS:
            return

        if type_ in STANDARD_FIELDS:
            self.set_standard_fields(
                field=field,
                fieldname=fieldname,
                type_=type_,
            )

        elif type_ in ['DateTimeField']:
            self.set_date_field(field=field, fieldname=fieldname, type_=type_)

        elif type_ in BLOB_FIELDS:
            self.set_blob_field(field=field, fieldname=fieldname, type_=type_)

        elif type_ in ['ReferenceField']:
            self.set_raw_field(field=field, fieldname=fieldname, type_=type_)
        elif type_ == 'siteAreasField':
            self.set_siteareas_field(field=field, fieldname=fieldname)
        else:
            raise TypeError(
                'Unknown field type for ArchetypesWrapper in {0} in {1}'.format(  # noqa
                    fieldname, self.context.absolute_url()))

    def set_standard_fields(self, field, fieldname, type_):
        try:
            value = field.getRaw(self.context)
        except AttributeError:
            value = self._get_at_field_value(field)

        if callable(value) is True:
            value = value()

        if value and type_ in ['StringField', 'TextField']:
            try:
                value = self.decode(value)
            except AttributeError:
                # maybe an int?
                value = unicode(value)
            except Exception, e:
                raise Exception('problems with %s: %s' % (
                    self.context.absolute_url(), str(e))
                )
        elif value and type_ == 'DataGridField':
            for i, row in enumerate(value):
                for col_key in row.keys():
                    col_value = row[col_key]
                    if type(col_value) in (unicode, str):
                        value[i][col_key] = self.decode(col_value)

        try:
            ct = field.getContentType(self.context)
        except AttributeError:
            ct = ''
        self[unicode(fieldname)] = value
        self[unicode('_content_type_') + fieldname] = ct

    def set_date_field(self, field, fieldname, type_):
        value = self._get_at_field_value(field)
        if value:
            value = DateTime.DateTime.strftime(value, '%Y-%m-%d %H:%M')
            # value = str(self._get_at_field_value(field))
            # value = self._get_at_field_value(field).ISO8601()
            self[unicode(fieldname)] = value

    def set_blob_field(self, field, fieldname, type_):
        fieldname = unicode('_datafield_' + fieldname)
        value = self._get_at_field_value(field)
        value2 = value

        try:
            max_filesize = int(
                os.environ.get('JSONIFY_MAX_FILESIZE', 2000)
            )
        except ValueError:
            max_filesize = 2000

        try:
            if value:
                pass
        except Exception as e:
            logger.error('Problem exporting content: {0}'.format(
                self.context.absolute_url()))
            return

        if not value:
            return
        try:
            value.get_size()
        except Exception as e:
            logger.error('Problem exporting content {0}'.format(
                self.context.absolute_url()))
            return

        if value.get_size() and value.get_size() < max_filesize:
            if type(value) is not str:
                if type(value.data) is str:
                    value = base64.b64encode(value.data)
                else:
                    data = value.data
                    value = ''
                    while data is not None:
                        value += data.data
                        data = data.next
                    value = base64.b64encode(value)

            self[fieldname] = {'data': value}
        else:
            data_uri = '{0}/at_download/{1}'.format(
                self.context.absolute_url(),
                fieldname.replace('_datafield_', '')
            )
            self[fieldname] = {'data_uri': data_uri}

        size = value2.get_size()
        try:
            fname = field.getFilename(self.context)
        except AttributeError:
            fname = value2.getFilename()

        try:
            fname = self.decode(fname)
        except AttributeError:
            # maybe an int?
            fname = unicode(fname)
        except Exception, e:
            raise Exception(
                'problems with %s: %s' % (
                    self.context.absolute_url(), str(e)
                )
            )

        try:
            ctype = field.getContentType(self.context)
        except AttributeError:
            ctype = value2.getContentType()

        self[fieldname].update({
            'size': size,
            'filename': fname or '',
            'content_type': ctype
        })

    def set_raw_field(self, field, fieldname, type_):
        value = field.getRaw(self.context)
        if value:
            self[fieldname] = value

    def set_siteareas_field(self, field, fieldname):
        uids = field.get(self.context)
        if not uids:
            return
        siteareas = api.content.find(UID=uids)
        self[fieldname] = [x.Title for x in siteareas]
