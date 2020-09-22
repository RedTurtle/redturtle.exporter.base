# -*- coding: utf-8 -*-
"""Installer for the redturtle.exporter.base package."""

from setuptools import find_packages
from setuptools import setup


long_description = '\n\n'.join(
    [
        open('README.rst').read(),
        open('CONTRIBUTORS.rst').read(),
        open('CHANGES.rst').read(),
    ]
)


setup(
    name='redturtle.exporter.base',
    version='1.2.0',
    description="Json exporter base for Plone",
    long_description=long_description,
    # Get more from https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        "Environment :: Web Environment",
        "Framework :: Plone",
        "Framework :: Plone :: 4.3",
        "Framework :: Plone :: 5.1",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
    ],
    keywords='Python Plone',
    author='RedTurtle Technology',
    author_email='sviluppoplone@redturtle.it',
    url='https://pypi.python.org/pypi/redturtle.exporter.base',
    license='GPL version 2',
    packages=find_packages('src', exclude=['ez_setup']),
    namespace_packages=['redturtle', 'redturtle.exporter'],
    package_dir={'': 'src'},
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        # -*- Extra requirements: -*-
        'plone.api>=1.10.0',
        'Products.GenericSetup',
        'setuptools',
    ],
    extras_require={
        'test': [
            'plone.app.testing',
            # Plone KGS does not use this version, because it would break
            # Remove if your package shall be part of coredev.
            # plone_coredev tests as of 2016-04-01.
            'plone.testing>=5.0.0',
            'plone.app.contenttypes',
            'plone.app.robotframework[debug]',
        ]
    },
    entry_points="""
    [z3c.autoinclude.plugin]
    target = plone
    """,
)
