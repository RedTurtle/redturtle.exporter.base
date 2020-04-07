.. This README is meant for consumption by humans and pypi. Pypi can render rst files so please do not use Sphinx features.
   If you want to learn more about writing documentation, please check out: http://docs.plone.org/about/documentation_styleguide.html
   This text does not appear on pypi or github. It is a comment.

=======================
Redturtle Exporter base
=======================

.. image:: https://github.com/RedTurtle/redturtle.exporter.base/workflows/Tests/badge.svg

Tool that exports Plone contents for a major migration.

This should be used with **redturtle.importer.base/volto** packages.

Features
--------

- Easily to include in your old site (just add to the buildout)
- No dependencies to other tools
- Easily to extend (see below)

Custom exporters
----------------

This base product exports standard content-types (also Archetype-based).

If your site has some additional content-types to be exported and need to structure output in a more specific way,
you can create a more specific package (for example redturtle.importer.project_name) where you can add specific exporters like this::

    <browser:page
      for="my.project.interfaces.IMyCustomType"
      name="get_item"
      class=".jsonify.MyCustomTypeGetItem"
      permission="zope2.ViewManagementScreens"
      />

where **GetItem** class is::

    from redturtle.exporter.base.browser.jsonify import GetItem as BaseGetter
    class MyCustomTypeGetItem(GetItem):

        def __call__(self):

            context_dict = super(MyCustomTypeGetItem, self).__call__()
            ... do something with context_dict ...

            return get_json_object(self, context_dict)


Export users and groups
-----------------------

There are two additional views that can be called (only Site Managers has access to these views) to export the list of users and groups:

- /export_users
- /export_groups

These views returns a json with all the informations.

Installation
------------

Install redturtle.exporter.base by adding it to your buildout::

    [buildout]

    ...

    eggs =
        redturtle.exporter.base


and then running ``bin/buildout``


Contribute
----------

- Issue Tracker: https://github.com/collective/redturtle.exporter.base/issues
- Source Code: https://github.com/collective/redturtle.exporter.base


Credits
-------

This product has been developed with some help from

.. image:: https://kitconcept.com/logo.svg
   :alt: kitconcept
   :width: 300
   :height: 80
   :target: https://kitconcept.com/

License
-------

The project is licensed under the GPLv2.
