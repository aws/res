#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.
from typing import List

from botocore.exceptions import ClientError

import ideavirtualdesktopcontroller
from ideadatamodel import VirtualDesktopServer, VirtualDesktopSession
from ideasdk.utils import Utils
from ideavirtualdesktopcontroller.app.servers.virtual_desktop_server_db import VirtualDesktopServerDB
from ideavirtualdesktopcontroller.app.virtual_desktop_controller_utils import VirtualDesktopControllerUtils


class VirtualDesktopServerUtils:
    def __init__(self, context: ideavirtualdesktopcontroller.AppContext, db: VirtualDesktopServerDB):
        self.context = context
        self._logger = context.logger('virtual-desktop-server-utils')
        self.ec2_client = self.context.aws().ec2()
        self._server_db = db
        self._controller_utils = VirtualDesktopControllerUtils(self.context)

    def provision_host_for_session(self, session: VirtualDesktopSession) -> VirtualDesktopServer:
        self._logger.info(f'initiate_host_provisioning for {session.name}')

        host_provisioning_response = self._controller_utils.provision_dcv_host_for_session(session)

        instances = Utils.get_value_as_list('Instances', host_provisioning_response, [])

        # We know that there is ONLY 1 instance
        session.server.instance_id = Utils.get_value_as_string('InstanceId', instances[0], None)
        return self._server_db.create(
            server=session.server,
            idea_session_id=session.idea_session_id,
            idea_session_owner=session.owner
        )

    def _stop_dcv_hosts(self, servers: List[VirtualDesktopServer], hibernate=False) -> dict:
        if Utils.is_empty(servers):
            self._logger.debug('No servers provided to _stop_dcv_hosts...')
            return {}

        instance_ids = []
        for server in servers:
            instance_ids.append(server.instance_id)

        if hibernate:
            self._logger.debug(f'Hibernating {instance_ids}')
        else:
            self._logger.debug(f'Stopping {instance_ids}')

        response = self.ec2_client.stop_instances(
            InstanceIds=instance_ids,
            Hibernate=hibernate
        )
        return Utils.to_dict(response)

    def stop_or_hibernate_servers(self, servers_to_stop: List[VirtualDesktopServer] = None, servers_to_hibernate: List[VirtualDesktopServer] = None):
        if Utils.is_empty(servers_to_stop) and Utils.is_empty(servers_to_hibernate):
            self._logger.debug('No servers provided to stop or hibernate...')
            return {}

        if Utils.is_not_empty(servers_to_stop):
            response = self._stop_dcv_hosts(servers_to_stop)
            instances = Utils.get_value_as_list('StoppingInstances', response, [])
            for instance in instances:
                instance_id = Utils.get_value_as_string('InstanceId', instance, None)
                server = self._server_db.get(instance_id=instance_id)
                if server.is_idle:
                    server.state = 'STOPPED_IDLE'
                else:
                    server.state = 'STOPPED'
                self._server_db.update(server)

        if Utils.is_not_empty(servers_to_hibernate):
            response = self._stop_dcv_hosts(servers_to_hibernate, hibernate=True)
            instances = Utils.get_value_as_list('StoppingInstances', response, [])
            for instance in instances:
                instance_id = Utils.get_value_as_string('InstanceId', instance, None)
                server = self._server_db.get(instance_id=instance_id)
                server.state = 'HIBERNATED'
                self._server_db.update(server)

    def start_dcv_hosts(self, servers: List[VirtualDesktopServer]) -> dict:
        instance_ids = []
        for server in servers:
            instance_ids.append(server.instance_id)
        try:
            response = self.ec2_client.start_instances(
                InstanceIds=instance_ids
            )
        except ClientError as e:
            self._logger.error(e)
            return {
                "ERROR": str(e)
            }
        return Utils.to_dict(response)

    def reboot_dcv_hosts(self, servers: List[VirtualDesktopServer]) -> dict:
        if Utils.is_empty(servers):
            return {}

        instance_ids = []
        for server in servers:
            instance_ids.append(server.instance_id)

        response = self.ec2_client.reboot_instances(
            InstanceIds=instance_ids
        )
        return Utils.to_dict(response)

    def _terminate_dcv_hosts(self, servers: List[VirtualDesktopServer]) -> dict:
        instance_ids = []
        for server in servers:
            instance_ids.append(server.instance_id)

        response = self.ec2_client.terminate_instances(
            InstanceIds=instance_ids
        )
        return Utils.to_dict(response)

    def terminate_dcv_hosts(self, servers: List[VirtualDesktopServer]) -> dict:
        if Utils.is_empty(servers):
            return {}

        terminate_response = self._terminate_dcv_hosts(servers)
        instances = Utils.get_value_as_list('TerminatingInstances', terminate_response, [])
        for instance in instances:
            self._server_db.delete(VirtualDesktopServer(
                instance_id=Utils.get_value_as_string('InstanceId', instance, None)
            ))
        return terminate_response
