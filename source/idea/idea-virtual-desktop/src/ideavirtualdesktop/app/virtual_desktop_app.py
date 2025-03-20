#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import ideasdk.app

import ideavirtualdesktop
from ideavirtualdesktop.app.api_invoker import VirtualDesktopAppApiInvoker
from ideasdk.server import SocaServerOptions


class IdeaVirtualDesktopApp(ideasdk.app.SocaApp):
    """
    Virtual desktop app
    """
    def __init__(self, context: ideavirtualdesktop.AppContext,
                 **kwargs):
        super().__init__(
            context=context,
            api_invoker=VirtualDesktopAppApiInvoker(),
            server_options=SocaServerOptions(enable_openapi_spec=False, api_path_prefixes=["/vdc"]),
            **kwargs
        )
        self.context = context

    def app_initialize(self):
        pass

    def app_start(self):
        pass

    def app_stop(self):
        pass
