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

"""
Test Cases for AccountsService
"""

from unittest.mock import patch

from ideaclustermanager import AppContext
from ideaclustermanager.app.accounts.helpers.quic_update_helper import (
    LISTENER_PORT,
    QUIC,
    QUIC_PROTOCOL,
    TCP,
    TCP_PROTOCOL,
    QuicUpdateHelper,
    UpdateQuicResults,
)

from ideadatamodel import constants

describe_target_groups_result = {
    "TargetGroupArn": "target-group-arn",
    "TargetGroupName": "target-group-name",
    "VpcId": "target-group-vpc-id",
}

egress_udp_ip_permissions = [
    {
        "FromPort": 8443,
        "IpProtocol": "udp",
        "IpRanges": [
            {"CidrIp": "0.0.0.0/0", "Description": "Allow UDP egress for port 8443"},
        ],
        "ToPort": 8443,
    }
]


@patch.object(QuicUpdateHelper, "update_quic_config_steps")
def test_update_quic_config_enable(mock_update_quic_config_steps, context: AppContext):
    """
    update_quic_config should call update_quic_config_steps with QUIC protocol
    """

    context.accounts.quic_update_helper.update_quic_config(enabled=True)
    mock_update_quic_config_steps.assert_called_with(QUIC_PROTOCOL, QUIC)


@patch.object(QuicUpdateHelper, "update_quic_config_steps")
def test_update_quic_config_disable(mock_update_quic_config_steps, context: AppContext):
    """
    update_quic_config should call update_quic_config_steps with TCP protocol
    """

    context.accounts.quic_update_helper.update_quic_config(enabled=False)
    mock_update_quic_config_steps.assert_called_with(TCP_PROTOCOL, TCP)


@patch.object(QuicUpdateHelper, "update_egress")
@patch.object(QuicUpdateHelper, "update_quic_flag")
@patch.object(QuicUpdateHelper, "create_listener")
@patch.object(
    QuicUpdateHelper, "create_target_group", return_value="new-target-group-arn"
)
def test_update_quic_config_steps_enable(
    mock_create_target_group,
    mock_create_listener,
    mock_update_quic_flag,
    mock_update_egress,
    context: AppContext,
):
    """
    update_quic_config_steps should delete old listener and target group, create new ones with QUIC configurations,
    add UDP egress rule, and update QUIC flag
    """
    context.config().put("virtual-desktop-controller.external_nlb_arn", "nlb-arn")

    result = context.accounts.quic_update_helper.update_quic_config_steps(
        protocol=QUIC_PROTOCOL, config=QUIC
    )

    context.aws().elbv2().delete_listener.assert_called_with(ListenerArn="listener-arn")
    context.aws().elbv2().delete_target_group.assert_called_with(
        TargetGroupArn="target-group-arn"
    )
    mock_create_target_group.assert_called_with(
        "target-group-name",
        QUIC_PROTOCOL,
        "target-group-vpc-id",
    )
    mock_create_listener.assert_called_with(
        "nlb-arn",
        QUIC_PROTOCOL,
        "new-target-group-arn",
    )
    mock_update_egress.assert_called_with(QUIC)
    mock_update_quic_flag.assert_called_with(QUIC)
    assert result == UpdateQuicResults.SUCCESS


@patch.object(QuicUpdateHelper, "update_egress")
@patch.object(QuicUpdateHelper, "update_quic_flag")
@patch.object(QuicUpdateHelper, "create_listener")
@patch.object(
    QuicUpdateHelper, "create_target_group", return_value="new-target-group-arn"
)
def test_update_quic_config_steps_disable(
    mock_create_target_group,
    mock_create_listener,
    mock_update_quic_flag,
    mock_update_egress,
    context: AppContext,
):
    """
    update_quic_config_steps should delete old listener and target group, create new ones with TCP configurations,
    remove UDP egress rule, and update QUIC flag
    """
    context.config().put("virtual-desktop-controller.external_nlb_arn", "nlb-arn")

    result = context.accounts.quic_update_helper.update_quic_config_steps(
        protocol=TCP_PROTOCOL, config=TCP
    )

    context.aws().elbv2().delete_listener.assert_called_with(ListenerArn="listener-arn")
    context.aws().elbv2().delete_target_group.assert_called_with(
        TargetGroupArn="target-group-arn"
    )
    mock_create_target_group.assert_called_with(
        "target-group-name",
        TCP_PROTOCOL,
        "target-group-vpc-id",
    )
    mock_create_listener.assert_called_with(
        "nlb-arn",
        TCP_PROTOCOL,
        "new-target-group-arn",
    )
    mock_update_egress.assert_called_with(TCP)
    mock_update_quic_flag.assert_called_with(TCP)
    assert result == UpdateQuicResults.SUCCESS


@patch.object(QuicUpdateHelper, "execute_rollback_steps")
def test_rollback_enable(mock_execute_rollback_steps, context: AppContext):
    """
    rollback should call execute_rollback_steps with TCP protocols
    """

    context.accounts.quic_update_helper.rollback(
        config=QUIC,
        current_target_group=describe_target_groups_result,
        external_nlb_arn="nlb-arn",
    )

    mock_execute_rollback_steps.assert_called_with(
        TCP_PROTOCOL,
        TCP,
        describe_target_groups_result,
        "nlb-arn",
        None,
        None,
    )


@patch.object(QuicUpdateHelper, "execute_rollback_steps")
def test_rollback_disable(mock_execute_rollback_steps, context: AppContext):
    """
    rollback should call execute_rollback_steps with TCP protocols
    """

    context.accounts.quic_update_helper.rollback(
        config=TCP,
        current_target_group=describe_target_groups_result,
        external_nlb_arn="nlb-arn",
    )

    mock_execute_rollback_steps.assert_called_with(
        QUIC_PROTOCOL,
        QUIC,
        describe_target_groups_result,
        "nlb-arn",
        None,
        None,
    )


@patch.object(QuicUpdateHelper, "create_listener")
@patch.object(
    QuicUpdateHelper, "create_target_group", return_value="new-target-group-arn"
)
def test_execute_rollback_steps_enable(
    mock_create_target_group, mock_create_listener, context: AppContext
):
    """
    execute_rollback_steps should create a new target group and listener following the configurations of the original
    resources. It should also delete the newly created target group if it was created.
    """

    result = context.accounts.quic_update_helper.execute_rollback_steps(
        protocol=TCP_PROTOCOL,
        config=TCP,
        current_target_group=describe_target_groups_result,
        external_nlb_arn="nlb-arn",
        new_target_group_arn="new-target-group-arn",
    )

    context.aws().elbv2().delete_target_group.assert_called_with(
        TargetGroupArn="new-target-group-arn"
    )
    mock_create_target_group.assert_called_with(
        "target-group-name",
        TCP_PROTOCOL,
        "target-group-vpc-id",
    )
    mock_create_listener.assert_called_with(
        "nlb-arn",
        TCP_PROTOCOL,
        "new-target-group-arn",
    )
    assert result == UpdateQuicResults.ROLLBACK_COMPLETE


def test_update_egress_enable(context: AppContext):
    """
    update_egress should create a new egress UDP rule
    """
    context.config().put(
        "virtual-desktop-controller.gateway_security_group_id", "security-id"
    )

    context.accounts.quic_update_helper.update_egress(config=QUIC)

    context.aws().ec2().authorize_security_group_egress.assert_called_with(
        GroupId="security-id", IpPermissions=egress_udp_ip_permissions
    )


def test_update_egress_disable(context: AppContext):
    """
    update_egress should delete the egress UDP rule
    """
    context.config().put(
        "virtual-desktop-controller.gateway_security_group_id", "security-id"
    )

    context.accounts.quic_update_helper.update_egress(config=TCP)

    context.aws().ec2().revoke_security_group_egress.assert_called_with(
        GroupId="security-id", IpPermissions=egress_udp_ip_permissions
    )


def test_update_quic_flag_enable(context: AppContext):
    """
    update_quic_flag should update QUIC flag to be True
    """
    with patch.object(context._config, "put"):
        context.accounts.quic_update_helper.update_quic_flag(config=QUIC)

        module_id = context.config().get_module_id(
            constants.MODULE_VIRTUAL_DESKTOP_CONTROLLER
        )
        context.config().db.set_config_entry.assert_called_with(
            f"{module_id}.dcv_session.quic_support", True
        )
        context.config().put.assert_called_with(
            f"{module_id}.dcv_session.quic_support", True
        )


def test_update_quic_flag_disable(context: AppContext):
    """
    update_quic_flag should update QUIC flag to be True
    """
    with patch.object(context._config, "put"):
        context.accounts.quic_update_helper.update_quic_flag(config=TCP)

        module_id = context.config().get_module_id(
            constants.MODULE_VIRTUAL_DESKTOP_CONTROLLER
        )
        context.config().db.set_config_entry.assert_called_with(
            f"{module_id}.dcv_session.quic_support", False
        )
        context.config().put.assert_called_with(
            f"{module_id}.dcv_session.quic_support", False
        )


def test_create_listener(context: AppContext):
    """
    create_listener should create listener with provided values and return the arn of the created listener
    """

    result = context.accounts.quic_update_helper.create_listener(
        external_nlb_arn="nlb-arn",
        protocol=QUIC_PROTOCOL,
        target_group_arn="target-group-arn",
    )

    context.aws().elbv2().create_listener.assert_called_with(
        LoadBalancerArn="nlb-arn",
        Protocol=QUIC_PROTOCOL,
        Port=LISTENER_PORT,
        DefaultActions=[{"Type": "forward", "TargetGroupArn": "target-group-arn"}],
    )
    assert result == "listener-arn"


def test_create_target_group(context: AppContext):
    """
    create_target_group should create target group and register the vdc_gateway instance as a registered target
    """
    context.accounts.quic_update_helper.create_target_group(
        target_group_name="target-group-name", protocol=QUIC_PROTOCOL, vpc_id="vpc-id"
    )

    context.aws().elbv2().register_targets.assert_called_with(
        TargetGroupArn="target-group-arn", Targets=[{"Id": "i-123"}]
    )
