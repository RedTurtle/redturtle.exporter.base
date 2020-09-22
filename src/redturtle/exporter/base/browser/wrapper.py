# -*- coding: utf-8 -*-
from Acquisition import aq_base
from DateTime import DateTime
from plone import api
from plone.app.portlets.interfaces import IPortletTypeInterface
from plone.portlets.interfaces import IPortletAssignmentMapping
from plone.portlets.interfaces import IPortletAssignmentSettings
from plone.portlets.interfaces import IPortletManager
from Products.CMFCore.utils import getToolByName
from six.moves import range
from zope.component import getUtilitiesFor
from zope.component import queryMultiAdapter
from zope.interface import providedBy

import datetime
import os
import six


try:
    from plone.uuid.interfaces import IUUID

    HASPLONEUUID = True
except ImportError:
    HASPLONEUUID = False


class Wrapper(dict):
    """Gets the data in a format that can be used by the transmogrifier
    blueprints in collective.jsonmigrator.
    """

    def __init__(self, context, defaultpage=False):
        self.context = context
        self._context = aq_base(context)
        self.defaultpage = defaultpage
        self.charset = None
        self.portal = api.portal.get()

        try:
            self.portal_path = "/".join(self.portal.getPhysicalPath())
            self.portal_utils = api.portal.get_tool(name="plone_utils")
            try:
                self.charset = (
                    self.portal.portal_properties.site_properties.default_charset  # noqa
                )
            except AttributeError:
                pass
        except ImportError:
            pass

        # never seen it missing ... but users can change it
        if not self.charset:
            self.charset = "utf-8"
        for method in dir(self):
            if method.startswith("get_"):
                getattr(self, method)()

    def providedBy(self, iface, ctx):
        # Handle zope.interface and Interface interfaces.
        if getattr(iface, "providedBy", False):
            ret = iface.providedBy(ctx)
        elif getattr(iface, "isImplementedBy", False):
            ret = iface.isImplementedBy(ctx)
        return bool(ret)

    def decode(self, s, encodings=("utf8", "latin1", "ascii")):
        """Sometimes we have to guess charset
        """
        if callable(s):
            s = s()
        if isinstance(s, six.text_type):
            return s
        test_encodings = encodings
        if self.charset:
            test_encodings = (self.charset,) + test_encodings
        for encoding in test_encodings:
            try:
                return s.decode(encoding)
            except Exception:
                pass
        return s.decode(test_encodings[0], "ignore")

    def _serialize_file(self, value):
        if hasattr(value, "open"):
            data = value.open().read()
        else:
            data = value.data

        try:
            max_filesize = int(
                os.environ.get("JSONIFY_MAX_FILESIZE", 20000000)
            )
        except ValueError:
            max_filesize = 20000000

        if data and len(data) > max_filesize:
            raise ValueError

        import base64

        ctype = value.contentType
        size = value.getSize()
        dvalue = {
            "data": base64.b64encode(data),
            "size": size,
            "filename": value.filename or "",
            "content_type": ctype,
            "encoding": "base64",
        }
        return dvalue

    def get_dexterity_fields(self):
        """If dexterity is used then extract fields.
        """
        try:
            from plone.dexterity.interfaces import IDexterityContent

            if not self.providedBy(IDexterityContent, self.context):
                return
            from plone.dexterity.utils import iterSchemata

            # from plone.uuid.interfaces import IUUID
            from zope.schema import getFieldsInOrder
            from datetime import date
        except Exception:
            return

        # get all fields for this obj
        for schemata in iterSchemata(self.context):
            for fieldname, field in getFieldsInOrder(schemata):
                try:
                    value = field.get(schemata(self.context))
                    # value = getattr(context, name).__class__.__name__
                except AttributeError:
                    continue
                if value is field.missing_value:
                    continue

                field_type = field.__class__.__name__
                try:
                    field_value_type = field.value_type.__class__.__name__
                except AttributeError:
                    field_value_type = None

                if field_type in ("RichText",):
                    # TODO: content_type missing
                    value = six.text_type(value.raw.decode("utf-8"))

                elif field_type in ("List", "Tuple") and field_value_type in (
                    "NamedImage",
                    "NamedBlobImage",
                    "NamedFile",
                    "NamedBlobFile",
                ):
                    fieldname = six.text_type("_datafield_" + fieldname)
                    _value = []
                    for item in value:
                        try:
                            _value.append(self._serialize_file(item))
                        except ValueError:
                            continue
                    value = _value

                elif field_type in (
                    "NamedImage",
                    "NamedBlobImage",
                    "NamedFile",
                    "NamedBlobFile",
                ):
                    # still to test above with NamedFile & NamedBlobFile
                    fieldname = six.text_type("_datafield_" + fieldname)
                    try:
                        value = self._serialize_file(value)
                    except ValueError:
                        continue

                elif field_type in ("RelationList",) and field_value_type in (
                    "RelationChoice",
                ):
                    _value = []
                    for item in value:
                        try:
                            # Simply export the path to the relation. Postprocessing when importing is needed.
                            _value.append(item.to_path)
                        except ValueError:
                            continue
                    value = _value

                elif field_type == "GeolocationField":
                    # super special plone.formwidget.geolocation case
                    self["latitude"] = getattr(value, "latitude", 0)
                    self["longitude"] = getattr(value, "longitude", 0)
                    continue
                elif isinstance(value, date) or isinstance(
                    value, datetime.datetime
                ):
                    value = value.isoformat()

                # elif field_type in ('TextLine',):
                else:
                    BASIC_TYPES = (
                        six.text_type,
                        int,
                        int,
                        float,
                        bool,
                        type(None),
                        list,
                        tuple,
                        dict,
                    )
                    if type(value) in BASIC_TYPES:
                        pass
                    else:
                        # E.g. DateTime or datetime are nicely representated
                        value = six.text_type(value)

                self[six.text_type(fieldname)] = value

    def _get_at_field_value(self, field):
        if field.accessor is not None:
            return getattr(self.context, field.accessor)()
        return field.get(self.context)

    def _fix_collection_query(self, query):
        """Run upgrade step transformation (this is not available from Plone 4.3.x)
        plone.app.querystring.upgrades.fix_select_all_existing_collections
        """
        indexes_to_fix = [
            u"portal_type",
            u"review_state",
            u"Creator",
            u"Subject",
        ]
        operator_mapping = {
            # old -> new
            u"plone.app.querystring.operation.selection.is": u"plone.app.querystring.operation.selection.any",  # noqa
            u"plone.app.querystring.operation.string.is": u"plone.app.querystring.operation.selection.any",  # noqa
        }
        fixed_querystring = []
        for querystring in query or []:
            # transform querystring to dict
            if not isinstance(querystring, dict):
                querystring = dict(querystring)
            if querystring["i"] in indexes_to_fix:
                for old_operator, new_operator in operator_mapping.items():
                    if querystring["o"] == old_operator:
                        querystring["o"] = new_operator
            if "v" not in querystring:
                fixed_querystring.append(querystring)
                continue
            # fix DateTime representation
            if isinstance(querystring["v"], DateTime):
                querystring["v"] = str(querystring["v"])
            elif type(querystring["v"]) in [tuple, list]:
                new_value = []
                for value in querystring["v"]:
                    if not isinstance(value, DateTime):
                        new_value.append(value)
                        continue
                    new_value.append(str(value))
                querystring["v"] = tuple(new_value)
            fixed_querystring.append(querystring)
        return fixed_querystring

    def get_archetypes_fields(self):
        """If Archetypes is used then dump schema.
        """
        try:
            from Products.Archetypes.interfaces import IBaseObject

            if not self.providedBy(IBaseObject, self.context):
                return
        except Exception:
            return

        try:
            from archetypes.schemaextender.interfaces import IExtensionField
        except Exception:
            IExtensionField = None

        import base64

        fields = []
        for schemata in self.context.Schemata().values():
            fields.extend(schemata.fields())

        for field in fields:
            fieldname = six.text_type(field.__name__)
            type_ = field.__class__.__name__

            try:
                if self.providedBy(IExtensionField, field):
                    # archetypes.schemaextender case:
                    # Try to get the base class of the schemaexter-field, which
                    # is not an extension field.
                    type_ = [
                        it.__name__
                        for it in field.__class__.__bases__
                        if not IExtensionField.implementedBy(it)
                    ][0]
            except Exception:
                pass

            fieldnames = [
                "BooleanField",
                "ComputedField",
                "DataGridField",
                "EmailField",
                "FixedPointField",
                "FloatField",
                "IntegerField",
                "LinesField",
                "SimpleDataGridField",
                "StringField",
                "TALESLines",
                "TALESString",
                "TextField",
                "ZPTField",
            ]

            if type_ in fieldnames:
                try:
                    value = field.getRaw(self.context)
                except AttributeError:
                    value = self._get_at_field_value(field)

                if callable(value):
                    value = value()

                if value and type_ in ["ComputedField"]:
                    if isinstance(value, str):
                        value = self.decode(value)

                if value and type_ in ["StringField", "TextField"]:
                    try:
                        value = self.decode(value)
                    except AttributeError:
                        # maybe an int?
                        value = six.text_type(value)
                    except Exception as e:
                        raise Exception(
                            "problems with %s: %s"
                            % (self.context.absolute_url(), str(e))
                        )

                elif value and type_ == "DataGridField":
                    for i, row in enumerate(value):
                        for col_key in row.keys():
                            col_value = row[col_key]
                            if type(col_value) in (six.text_type, str):
                                value[i][col_key] = self.decode(col_value)

                self[six.text_type(fieldname)] = value

                if value and type_ in ["StringField", "TextField"]:
                    try:
                        ct = field.getContentType(self.context)
                        self[six.text_type("_content_type_") + fieldname] = ct
                    except AttributeError:
                        pass

            elif type_ in ["DateTimeField"]:
                value = str(self._get_at_field_value(field))
                if value:
                    self[six.text_type(fieldname)] = value

            elif type_ in [
                "ImageField",
                "FileField",
                "BlobField",
                "AttachmentField",
                "ExtensionBlobField",
            ]:
                fieldname = six.text_type("_datafield_" + fieldname)
                value = self._get_at_field_value(field)
                value2 = value

                if value and not isinstance(value, str):
                    if isinstance(getattr(value, "data", None), str):
                        value = base64.b64encode(value.data)
                    else:
                        data = value.data
                        value = ""
                        while data is not None:
                            value += data.data
                            data = data.next
                        value = base64.b64encode(value)

                try:
                    max_filesize = int(
                        os.environ.get("JSONIFY_MAX_FILESIZE", 20000000)
                    )
                except ValueError:
                    max_filesize = 20000000

                if value and len(value) < max_filesize:
                    size = value2.getSize()
                    try:
                        fname = field.getFilename(self.context)
                    except AttributeError:
                        fname = value2.getFilename()

                    try:
                        fname = self.decode(fname)
                    except AttributeError:
                        # maybe an int?
                        fname = six.text_type(fname)
                    except Exception as e:
                        raise Exception(
                            "problems with %s: %s"
                            % (self.context.absolute_url(), str(e))
                        )

                    try:
                        ctype = field.getContentType(self.context)
                    except AttributeError:
                        ctype = value2.getContentType()

                    self[fieldname] = {
                        "data": value,
                        "size": size,
                        "filename": fname or "",
                        "content_type": ctype,
                        "encoding": "base64",
                    }

            elif type_ in ["ReferenceField"]:
                # If there are references, add the UIDs to the referenced
                # contents
                value = field.getRaw(self.context)
                if value:
                    self[fieldname] = value

            elif type_ in ["QueryField"]:
                value = field.getRaw(self.context)
                value = [dict(q) for q in value]
                self[fieldname] = self._fix_collection_query(value)

            elif type_ in [
                "RecordsField",  # from Products.ATExtensions
                "RecordField",
                "FormattableNamesField",
                "FormattableNameField",
            ]:
                # ATExtensions fields
                # convert items to real dicts
                # value = [dict(it) for it in field.get(self.context)]

                def _enc(val):
                    if type(val) in (six.text_type, str):
                        val = self.decode(val)
                    return val

                value = []
                for it in field.get(self.context):
                    it = dict(it)
                    val_ = {}
                    for k_, v_ in it.items():
                        val_[_enc(k_)] = _enc(v_)
                    value.append(val_)

                self[six.text_type(fieldname)] = value

            else:
                # Just try to stringify value
                try:
                    value = field.getRaw(self.context)
                except AttributeError:
                    value = self._get_at_field_value(field)
                self[six.text_type(fieldname)] = self.decode(str(value))

    def get_references(self):
        """AT references.
        """
        try:
            from Products.Archetypes.interfaces import IReferenceable

            if not self.providedBy(IReferenceable, self.context):
                return
        except Exception:
            return

        self["_atrefs"] = {}
        self["_atbrefs"] = {}
        relationships = self.context.getRelationships()
        for rel in relationships:
            self["_atrefs"][rel] = []
            refs = self.context.getRefs(relationship=rel)
            for ref in refs:
                if ref is not None:
                    self["_atrefs"][rel].append(
                        "/".join(ref.getPhysicalPath())
                    )
        brelationships = self.context.getBRelationships()
        for brel in brelationships:
            self["_atbrefs"][brel] = []
            brefs = self.context.getBRefs(relationship=brel)
            for bref in brefs:
                if bref is not None:
                    self["_atbrefs"][brel].append(
                        "/".join(bref.getPhysicalPath())
                    )

    def get_uid(self):
        """Unique ID of object
        Example::
            {'_uid': '12jk3h1kj23h123jkh13kj1k23jh1'}
        """
        if hasattr(self._context, "UID"):
            self["_uid"] = self.context.UID()
        elif HASPLONEUUID:
            self["_uid"] = IUUID(self.context.aq_base, None)

    def get_id(self):
        """Object id
        :keys: _id
        """
        self["_id"] = self.context.getId()

    def get_path(self):
        """Path of object
        Example::
            {'_path': '/Plone/first-page'}
        """
        self["_path"] = "/".join(self.context.getPhysicalPath())

    def get_type(self):
        """Portal type of object
        Example::
            {'_type': 'Document'}
        """
        try:
            type_ = self.context.portal_type
            if type_ == "Topic":
                type_ = "Collection"
            self["_type"] = type_
        except AttributeError:
            pass

    def get_classname(self):
        """Classname of object.
        Sometimes in old Plone sites we dont know exactly which type we are
        using.
        Example::
           {'_classname': 'ATDocument'}
        """
        self["_classname"] = self.context.__class__.__name__

    def get_properties(self):
        """Object properties
        :keys: _properties
        """
        self["_properties"] = []
        if getattr(self.context, "propertyIds", False):
            for pid in self.context.propertyIds():
                val = self.context.getProperty(pid)
                typ = self.context.getPropertyType(pid)
                if typ == "string" and isinstance(val, str):
                    val = self.decode(val)
                if (
                    isinstance(val, DateTime)  # noqa
                    or isinstance(val, datetime.time)  # noqa
                    or isinstance(val, datetime.datetime)  # noqa
                    or isinstance(val, datetime.date)  # noqa
                ):
                    val = six.text_type(val)
                self["_properties"].append(
                    (pid, val, self.context.getPropertyType(pid))
                )

    def get_directly_provided_interfaces(self):
        try:
            from zope.interface import directlyProvidedBy
        except Exception:
            return
        self["_directly_provided"] = [
            it.__identifier__ for it in directlyProvidedBy(self.context)
        ]

    def get_defaultview(self):
        """Default view of object
        :keys: _layout, _defaultpage
        """
        try:
            # When migrating Zope folders to Plone folders
            # set defaultpage to "index_html"
            from Products.CMFCore.PortalFolder import PortalFolder

            if isinstance(self.context, PortalFolder):
                self["_defaultpage"] = "index_html"
                return
        except Exception:
            pass

        _default_item = None
        _default = ""
        try:
            _default_item, _default = self.portal_utils.browserDefault(
                self.context
            )
            for path in _default:
                if _default_item is None:
                    break
                _default_item = _default_item.get(path, None)
            _default = "/".join(_default)
        except AttributeError:
            pass

        _layout = ""
        try:
            _layout = self.context.getLayout()
        except Exception:
            pass

        if _default and _layout and _default == _layout:
            # browserDefault always returns the layout, but we only want to set
            # the defaultpage, if it's different from the layout
            _default = ""

        _isdefaultpage = False
        _parent = self.context.getParentNode()
        if _parent.getDefaultPage() == self.context.id:
            _isdefaultpage = True
        self["_isdefaultpage"] = _isdefaultpage

        if _default_item and not self.defaultpage:
            self["_defaultitem"] = Wrapper(_default_item, defaultpage=True)
        self["_defaultpage"] = _default
        self["_layout"] = _layout

    def get_format(self):
        """Format of object
        :keys: _format
        """
        try:
            self["_content_type"] = self.context.Format()
        except Exception:
            pass

    def get_local_roles(self):
        """Local roles of object
        :keys: _ac_local_roles
        """
        self["_ac_local_roles"] = {}
        if getattr(self.context, "__ac_local_roles__", False):
            for key, val in self.context.__ac_local_roles__.items():
                if key is not None:
                    self["_ac_local_roles"][key] = val

    def get_userdefined_roles(self):
        """User defined roles for object (via sharing UI)
        :keys: _userdefined_roles
        """
        self["_userdefined_roles"] = ()
        if getattr(self.context, "userdefined_roles", False):
            self["_userdefined_roles"] = self.context.userdefined_roles()

    def get_permissions(self):
        """Permission of object (Security tab in ZMI)
        :keys: _permissions
        This works well until Plone 51.
        From Plone 52, permission_settings method returns a different list.
        """
        self["_permissions"] = {}
        if getattr(self.context, "permission_settings", False):
            roles = self.context.validRoles()
            ps = self.context.permission_settings()
            for perm in ps:
                unchecked = 0
                if not perm["acquire"]:
                    unchecked = 1
                new_roles = []
                for role in perm["roles"]:
                    if role["checked"]:
                        role_idx = role["name"].index("r") + 1
                        role_name = roles[int(role["name"][role_idx:])]
                        new_roles.append(role_name)
                if unchecked or new_roles:
                    self["_permissions"][perm["name"]] = {
                        "acquire": not unchecked,
                        "roles": new_roles,
                    }

    def get_owner(self):
        """Object owner
        :keys: _owner
        """
        try:
            try:
                try:
                    self["_owner"] = self.context.getWrappedOwner().getId()
                except Exception:
                    self["_owner"] = self.context.getOwner(info=1).getId()
            except Exception:
                self["_owner"] = self.context.getOwner(info=1)[1]
        except Exception:
            pass

    def get_workflowhistory(self):
        """Workflow history
        :keys: _workflow_history
        Example:::
            lalala
        """
        self["_workflow_history"] = {}
        if getattr(self.context, "workflow_history", False):
            workflow_history = self.context.workflow_history.data
            for w in workflow_history:
                for i, w2 in enumerate(workflow_history[w]):
                    if "time" in list(workflow_history[w][i].keys()):
                        workflow_history[w][i]["time"] = str(
                            workflow_history[w][i]["time"]
                        )
                    if "comments" in list(workflow_history[w][i].keys()):
                        workflow_history[w][i]["comments"] = self.decode(
                            workflow_history[w][i]["comments"]
                        )
            self["_workflow_history"] = workflow_history

    def get_position_in_parent(self):
        """Get position in parent
        :keys: _gopip
        """
        try:
            from Products.CMFPlone.CatalogTool import getObjPositionInParent
        except ImportError:
            return

        pos = getObjPositionInParent(self.context)

        # After plone 3.3 the above method returns a 'DelegatingIndexer' rather
        # than an int
        try:
            from plone.indexer.interfaces import IIndexer

            if self.providedBy(IIndexer, pos):
                self["_gopip"] = pos()
                return
        except ImportError:
            pass

        self["_gopip"] = pos

    def get_translation(self):
        """ Get LinguaPlone translation linking information.
        """
        if not hasattr(self._context, "getCanonical"):
            return

        translations = self.context.getTranslations()
        self["_translations"] = {}

        for lang in translations:
            trans_obj = "/".join(translations[lang][0].getPhysicalPath())[
                len(self.portal_path) :  # noqa
            ]
            self["_translations"][lang] = trans_obj

        self["_translationOf"] = "/".join(
            self.context.getCanonical().getPhysicalPath()
        )[
            len(self.portal_path) :  # noqa
        ]
        self["_canonicalTranslation"] = self.context.isCanonical()

    def _is_cmf_only_obj(self):
        """Test, if a content item is a CMF only object.
        """
        context = self.context
        try:
            from Products.ATContentTypes.interface.interfaces import (
                IATContentType,
            )  # noqa

            if self.providedBy(IATContentType, context):
                return False
        except Exception:
            pass
        try:
            from Products.ATContentTypes.interfaces import IATContentType

            if self.providedBy(IATContentType, context):
                return False
        except Exception:
            pass
        try:
            from plone.dexterity.interfaces import IDexterityContent

            if self.providedBy(IDexterityContent, context):
                return False
        except Exception:
            pass
        try:
            from Products.CMFCore.DynamicType import DynamicType

            # restrict this to non archetypes/dexterity
            if isinstance(context, DynamicType):
                return True
        except Exception:
            pass
        return False

    def get_zope_dublin_core(self):
        """If CMFCore is used in an old Zope site, then dump the
        Dublin Core fields
        """
        if not self._is_cmf_only_obj():
            return

        # strings
        for field in ("title", "description", "rights", "language"):
            val = getattr(self.context, field, False)
            if val:
                self[field] = self.decode(val)
            else:
                self[field] = ""
        # tuples
        for field in ("subject", "contributors"):
            self[field] = []
            val_tuple = getattr(self.context, field, False)
            if not val_tuple:
                # At least on Plone 2.5 we need Subject and Contributors
                # with a first capital letter.
                val_tuple = getattr(self.context, field.title(), False)
                if callable(val_tuple):
                    val_tuple = val_tuple()
            if val_tuple:
                for val in val_tuple:
                    self[field].append(self.decode(val))
                self[field] = tuple(self[field])
            else:
                self[field] = ()
        # datetime fields
        for field in [
            "creation_date",
            "expiration_date",
            "effective_date",
            "expirationDate",
            "effectiveDate",
        ]:
            val = getattr(self.context, field, False)
            if val:
                self[field] = str(val)
            else:
                self[field] = ""
        # modification_date:
        # bobobase_modification_time seems to have better data than
        # modification_date in Zope 2.6.4 - 2.9.7
        val = self.context.bobobase_modification_time()
        if val:
            self["modification_date"] = str(val)
        else:
            self["modification_date"] = ""

    def get_basic_dates(self):
        """ Dump creation and modification dates for items
        that are not "cmf-only". For dexterity for instance, these
        are not included in behaviors and so are not included in the
        iteration over schematas and fields in get_dexterity_fields().
        """
        if self._is_cmf_only_obj():
            # then the dates are handled by get_zope_dublin_core,
            # so we do nothing.
            return
        # datetime fields
        for field in ["creation_date", "modification_date"]:
            val = getattr(self.context.aq_base, field, False)
            if val:
                self[field] = str(val)
            else:
                self[field] = ""

    def get_zope_cmfcore_fields(self):
        """If CMFCore is used in an old Zope site, then dump the fields we know
        about.
        """
        if not self._is_cmf_only_obj():
            return

        self["_cmfcore_marker"] = "yes"

        # For Link & Favourite types - field name has changed in Archetypes &
        # Dexterity
        if hasattr(self.context, "remote_url"):
            self["remoteUrl"] = self.decode(
                getattr(self.context, "remote_url")
            )

        # For Document & News items
        if hasattr(self.context, "text"):
            self["text"] = self.decode(getattr(self.context, "text"))
        if hasattr(self.context, "text_format"):
            self["text_format"] = self.decode(
                getattr(self.context, "text_format")
            )

        # Found in Document & News items, but not sure if this is necessary
        if hasattr(self.context, "safety_belt"):
            self["safety_belt"] = self.decode(
                getattr(self.context, "safety_belt")
            )

        # Found in File & Image types, but not sure if this is necessary
        if hasattr(self.context, "precondition"):
            self["precondition"] = self.decode(
                getattr(self.context, "precondition")
            )

        data_type = self.context.portal_type

        if data_type in ["File", "Image"]:
            fieldname = six.text_type("_datafield_%s" % data_type.lower())
            value = self.context
            orig_value = value

            if not isinstance(value, str):
                try:
                    from base64 import b64encode
                except Exception:
                    # Legacy version of base64 (eg on Python 2.2)
                    from base64 import encodestring as b64encode
                if isinstance(value.data, str):
                    value = b64encode(value.data)
                else:
                    data = value.data
                    value = ""
                    while data is not None:
                        value += data.data
                        data = data.next
                    value = b64encode(value)

            try:
                max_filesize = int(
                    os.environ.get("JSONIFY_MAX_FILESIZE", 20000000)
                )
            except ValueError:
                max_filesize = 20000000

            if value and len(value) < max_filesize:
                size = orig_value.getSize()
                fname = orig_value.getId()
                try:
                    fname = self.decode(fname)
                except AttributeError:
                    # maybe an int?
                    fname = six.text_type(fname)
                except Exception as e:
                    raise Exception(
                        "problems with %s: %s"
                        % (self.context.absolute_url(), str(e))
                    )

                ctype = orig_value.getContentType()
                self[fieldname] = {
                    "data": value,
                    "size": size,
                    "filename": fname or "",
                    "content_type": ctype,
                    "encoding": "base64",
                }

    def get_zopeobject_document_src(self):
        if not self._is_cmf_only_obj():
            return
        document_src = getattr(self.context, "document_src", None)
        if document_src:
            self["document_src"] = self.decode(document_src())
        else:
            self["_zopeobject_document_src"] = ""

    def get_history(self):
        """ Export the history - metadata
        """
        try:
            repo_tool = getToolByName(self.context, "portal_repository")
            history_metadata = repo_tool.getHistoryMetadata(self.context)
            if not (hasattr(history_metadata, "getLength")):
                # No history metadata
                return

            history_list = []
            # Count backwards from most recent to least recent
            for i in range(
                history_metadata.getLength(countPurged=False) - 1, -1, -1
            ):
                data = history_metadata.retrieve(i, countPurged=False)
                meta = data["metadata"]["sys_metadata"].copy()
                # version_id = history_metadata.getVersionId(
                #     i, countPurged=False
                # )
                try:
                    dateaux = datetime.datetime.fromtimestamp(
                        meta.get("timestamp", 0)
                    )
                    meta["timestamp"] = dateaux.strftime(
                        "%Y/%m/%d %H:%M:%S GMT"
                    )
                except Exception:
                    meta["timestamp"] = ""
                history_list.append(meta)
            self["_history"] = history_list

        except Exception:
            pass

    def get_redirects(self):
        """Export plone.app.redirector redirects, if available.
        Comply with default expectations of redirector section in
        plone.app.transmogrifier: use the same key name "_old_paths"
        and don't include the site name on the path.
        """
        try:
            from zope.component import getUtility
            from plone.app.redirector.interfaces import IRedirectionStorage

            storage = getUtility(IRedirectionStorage)
            redirects = storage.redirects(
                "/".join(self.context.getPhysicalPath())
            )
            if redirects:
                # remove site name (e.g. "/Plone") from redirect paths
                self["_old_paths"] = [
                    r[len(self.portal_path) :] for r in redirects  # noqa
                ]
        except:  # noqa: E72 Exception2
            pass

    # def get_convert_topic_query(self):
    #     if self.context.portal_type != "Topic":
    #         return
    #     if self.context.limitNumber:
    #         self["limit"] = self["itemCount"]

    #     reg = getUtility(IRegistry)
    #     reader = IQuerystringRegistryReader(reg)
    #     registry = reader.parseRegistry()

    #     criteria = self.context.listCriteria()
    #     formquery = []
    #     for criterion in criteria:
    #         type_ = criterion.__class__.__name__
    #         if type_ == "ATSortCriterion":
    #             self["sort_reversed"] = criterion.getReversed()
    #             self["sort_on"] = criterion.Field()
    #             continue
    #         converter = CONVERTERS.get(type_)
    #         if converter is None:
    #             continue
    #         converter(formquery, criterion, registry)

    #     self["query"] = self._fix_collection_query(formquery)

    def get_portlets(self):
        portlets_schemata = {
            iface: name
            for name, iface in getUtilitiesFor(IPortletTypeInterface)
        }
        portlets = {}
        for manager_name, manager in getUtilitiesFor(IPortletManager):
            mapping = queryMultiAdapter(
                (self.context, manager), IPortletAssignmentMapping
            )
            if mapping is None:
                continue
            mapping = mapping.__of__(self.context)
            for name, assignment in mapping.items():
                type_ = None
                schema = None
                for schema in providedBy(assignment).flattened():
                    type_ = portlets_schemata.get(schema, None)
                    if type_ is not None:
                        break
                if type_ is None:
                    continue
                assignment = assignment.__of__(mapping)
                settings = IPortletAssignmentSettings(assignment)
                if manager_name not in portlets:
                    portlets[manager_name] = []
                portlets[manager_name].append(
                    {
                        "type": type_,
                        "visible": settings.get("visible", True),
                        "assignment": {
                            name: getattr(assignment, name, None)
                            for name in schema.names()
                        },
                    }
                )
        self["portlets"] = portlets
