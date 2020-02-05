# -*- coding: utf-8 -*-
from plone.app.contenttypes.testing import PLONE_APP_CONTENTTYPES_FIXTURE
from plone.app.robotframework.testing import REMOTE_LIBRARY_BUNDLE_FIXTURE
from plone.app.testing import FunctionalTesting
from plone.app.testing import IntegrationTesting
from plone.app.testing import PloneSandboxLayer
from plone.testing import z2

import redturtle.exporter.base


class RedturtleExporterBaseLayer(PloneSandboxLayer):

    defaultBases = (PLONE_APP_CONTENTTYPES_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        # Load any other ZCML that is required for your tests.
        # The z3c.autoinclude feature is disabled in the Plone fixture base
        # layer.
        self.loadZCML(package=redturtle.exporter.base)


REDTURTLE_EXPORTER_BASE_FIXTURE = RedturtleExporterBaseLayer()


REDTURTLE_EXPORTER_BASE_INTEGRATION_TESTING = IntegrationTesting(
    bases=(REDTURTLE_EXPORTER_BASE_FIXTURE,),
    name='RedturtleExporterBaseLayer:IntegrationTesting',
)


REDTURTLE_EXPORTER_BASE_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(REDTURTLE_EXPORTER_BASE_FIXTURE,),
    name='RedturtleExporterBaseLayer:FunctionalTesting',
)


REDTURTLE_EXPORTER_BASE_ACCEPTANCE_TESTING = FunctionalTesting(
    bases=(
        REDTURTLE_EXPORTER_BASE_FIXTURE,
        REMOTE_LIBRARY_BUNDLE_FIXTURE,
        z2.ZSERVER_FIXTURE,
    ),
    name='RedturtleExporterBaseLayer:AcceptanceTesting',
)
