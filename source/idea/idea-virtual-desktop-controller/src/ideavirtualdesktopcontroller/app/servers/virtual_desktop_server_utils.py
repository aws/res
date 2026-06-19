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
from typing import Dict, List, Optional

from botocore.exceptions import ClientError

import ideavirtualdesktopcontroller
from ideadatamodel import VirtualDesktopServer, VirtualDesktopSession
from ideasdk.utils import Utils
from ideavirtualdesktopcontroller.app.servers import constants as servers_constants
from ideavirtualdesktopcontroller.app.virtual_desktop_controller_utils import VirtualDesktopControllerUtils
from res.resources import sessions


class VirtualDesktopServerUtils:
    def __init__(self, context: ideavirtualdesktopcontroller.AppContext):
        self.context = context
        self._logger = context.logger('virtual-desktop-server-utils')
        self.ec2_client = self.context.aws().ec2()
        self._controller_utils = VirtualDesktopControllerUtils(self.context)

    @staticmethod
    def convert_server_object_to_db_dict(server: VirtualDesktopServer) -> Dict:
        if Utils.is_empty(server):
            return {}
        return {
            servers_constants.DCV_HOST_DB_HASH_KEY: server.instance_id,
            servers_constants.DCV_HOST_DB_INSTANCE_TYPE_KEY: server.instance_type,
            servers_constants.DCV_HOST_DB_IDEA_SESSION_ID_KEY: server.idea_sesssion_id,
            servers_constants.DCV_HOST_DB_IDEA_SESSION_OWNER_KEY: server.idea_session_owner,
            servers_constants.DCV_HOST_DB_LOCKED_KEY: False if Utils.is_empty(server.locked) else server.locked,
            servers_constants.DCV_HOST_DB_IS_IDLE_KEY: False if not server.is_idle else server.is_idle,
            sessions.SESSION_DB_PRIVATE_DNS_NAME_KEY: server.private_dns_name,
        }

    @staticmethod
    def convert_db_entry_to_server_object(db_entry: dict) -> Optional[VirtualDesktopServer]:
        if Utils.is_empty(db_entry):
            return None
        return VirtualDesktopServer(
            instance_id=Utils.get_value_as_string(servers_constants.DCV_HOST_DB_HASH_KEY, db_entry),
            instance_type=Utils.get_value_as_string(servers_constants.DCV_HOST_DB_INSTANCE_TYPE_KEY, db_entry),
            idea_sesssion_id=Utils.get_value_as_string(servers_constants.DCV_HOST_DB_IDEA_SESSION_ID_KEY, db_entry),
            idea_session_owner=Utils.get_value_as_string(servers_constants.DCV_HOST_DB_IDEA_SESSION_OWNER_KEY, db_entry),
            locked=Utils.get_value_as_bool(servers_constants.DCV_HOST_DB_LOCKED_KEY, db_entry, False),
            is_idle=db_entry.get(servers_constants.DCV_HOST_DB_IS_IDLE_KEY, False),
            private_dns_name=Utils.get_value_as_string(sessions.SESSION_DB_PRIVATE_DNS_NAME_KEY, db_entry),
        )

    def provision_host_for_session(self, session: VirtualDesktopSession) -> VirtualDesktopServer:
        self._logger.info(f'initiate_host_provisioning for {session.name}')

        host_provisioning_response = self._controller_utils.provision_dcv_host_for_session(session)

        instances = Utils.get_value_as_list('Instances', host_provisioning_response, [])

        # We know that there is ONLY 1 instance
        session.server.instance_id = Utils.get_value_as_string('InstanceId', instances[0], None)
        return session.server

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
            self._stop_dcv_hosts(servers_to_stop)

        if Utils.is_not_empty(servers_to_hibernate):
            self._stop_dcv_hosts(servers_to_hibernate, hibernate=True)

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

        return self._terminate_dcv_hosts(servers)
