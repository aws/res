#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import ideasdk.app

import ideabastionhost
from ideabastionhost.app.api_invoker import BastionHostApiInvoker
from ideasdk.server import SocaServer, SocaServerOptions


class IdeaBastionHostApp(ideasdk.app.SocaApp):
    """
    Bastion host app
    """
    def __init__(self, context: ideabastionhost.AppContext,
                 **kwargs):
        super().__init__(
            context=context,
            api_invoker=BastionHostApiInvoker(),
            server_options=SocaServerOptions(enable_openapi_spec=False, api_path_prefixes=["/bastion-host"]),
            **kwargs
        )
        self.context = context

    def app_initialize(self):
        # Start SSSD service
        self.context.config().restart_sssd()

    def app_start(self):
        pass

    def app_stop(self):
        pass
