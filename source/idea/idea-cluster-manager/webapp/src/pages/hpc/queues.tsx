/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
 * with the License. A copy of the License is located at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
 * OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
 * and limitations under the License.
 */

import React, { Component, RefObject } from "react";

import IdeaListView from "../../components/list-view";
import { SchedulerAdminClient } from "../../client";
import { AppContext } from "../../common";
import { HpcQueueProfile } from "../../client/data-model";
import IdeaSplitPanel from "../../components/split-panel";
import { TableProps } from "@cloudscape-design/components/table/interfaces";
import Utils from "../../common/utils";
import { ColumnLayout, StatusIndicator, Tabs } from "@cloudscape-design/components";
import { KeyValue, KeyValueGroup } from "../../components/key-value";
import { QueueUtils } from "./hpc-utils";
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import IdeaAppLayout, { IdeaAppLayoutProps } from "../../components/app-layout";
import { withRouter } from "../../navigation/navigation-utils";

export const HPC_QUEUE_TABLE_COLUMN_DEFINITIONS: TableProps.ColumnDefinition<HpcQueueProfile>[] = [
    {
        id: "queue-profile",
        header: "Queue Profile",
        cell: (queue) => queue.name,
    },
    {
        id: "queues",
        header: "Queues",
        cell: (queue) => {
            if (Utils.isEmpty(queue.queues)) {
                return "-";
            }
            return queue.queues!.join(", ");
        },
    },
    {
        id: "projects",
        header: "Projects",
        cell: (queue) => {
            if (Utils.isEmpty(queue.projects)) {
                return "-";
            }
            return (
                <div>
                    {queue.projects?.map((project, index) => {
                        return (
                            <li key={index}>
                                {project.title} ({project.name})
                            </li>
                        );
                    })}
                </div>
            );
        },
    },
    {
        id: "is-enabled",
        header: "Is Enabled?",
        cell: (queue) => {
            return queue.enabled ? <StatusIndicator type="success">Active</StatusIndicator> : <StatusIndicator type="stopped">Disabled</StatusIndicator>;
        },
    },
    {
        id: "status",
        header: "Provisioning Status",
        cell: (queue) => {
            if (!queue.enabled) {
                return "-";
            }
            let color;
            const status = queue.status!;
            let displayStatus;
            if (status === "idle") {
                color = "#c77405";
                displayStatus = "Idle";
            } else if (status === "active") {
                color = "green";
                displayStatus = "Active";
            } else {
                color = "red";
                displayStatus = "Blocked";
            }
            return (
                <b
                    style={{
                        color: color,
                        fontSize: "small",
                    }}
                >
                    {displayStatus}
                </b>
            );
        },
    },
];

export interface QueuesProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {}

export interface QueuesState {
    splitPanelOpen: boolean;
    queueSelected: boolean;
}

class Queues extends Component<QueuesProps, QueuesState> {
    listing: RefObject<IdeaListView>;

    constructor(props: QueuesProps) {
        super(props);
        this.listing = React.createRef();
        this.state = {
            splitPanelOpen: false,
            queueSelected: false,
        };
    }

    schedulerAdmin(): SchedulerAdminClient {
        return AppContext.get().client().schedulerAdmin();
    }

    getListing(): IdeaListView {
        return this.listing.current!;
    }

    isSelected(): boolean {
        return this.state.queueSelected;
    }

    getSelected(): HpcQueueProfile | null {
        if (this.getListing() == null) {
            return null;
        }
        return this.getListing().getSelectedItem();
    }

    isSelectedQueueProfileEnabled(): boolean {
        if (!this.isSelected()) {
            return false;
        }
        if (this.getSelected()?.enabled != null) {
            return this.getSelected()!.enabled!;
        }
        return false;
    }

    buildListing() {
        return (
            <IdeaListView
                ref={this.listing}
                preferencesKey={"queues"}
                showPreferences={false}
                title="Queue Profiles"
                description="Scale-Out Queue Management"
                selectionType="single"
                primaryAction={{
                    id: "submit-queue",
                    text: "Create Queue Profile",
                    onClick: () => {
                        this.props.navigate("/soca/queues/create");
                    },
                }}
                secondaryActionsDisabled={!this.isSelected()}
                secondaryActions={[
                    {
                        id: "edit-queue-profile",
                        text: "Edit Queue Profile",
                        onClick: () => {
                            this.props.navigate(`/soca/queues/update?id=${this.getSelected()?.queue_profile_id}`);
                        },
                    },
                    {
                        id: "enable-queue-profile",
                        text: this.isSelectedQueueProfileEnabled() ? "Disable Queue Profile" : "Enable Queue Profile",
                        onClick: () => {
                            if (this.isSelectedQueueProfileEnabled()) {
                                this.schedulerAdmin()
                                    .disableQueueProfile({
                                        queue_profile_id: this.getSelected()?.queue_profile_id,
                                    })
                                    .then(
                                        (_) => {
                                            this.setState(
                                                {
                                                    queueSelected: false,
                                                },
                                                () => {
                                                    this.props.onFlashbarChange({
                                                        items: [
                                                            {
                                                                type: "success",
                                                                content: `Queue Profile: ${this.getSelected()?.name} disabled successfully`,
                                                                dismissible: true,
                                                            },
                                                        ],
                                                    });
                                                    this.getListing().fetchRecords();
                                                }
                                            );
                                        },
                                        (error) => {
                                            this.props.onFlashbarChange({
                                                items: [
                                                    {
                                                        type: "error",
                                                        content: `Failed to disable queue profile: ${error.message}`,
                                                        dismissible: true,
                                                    },
                                                ],
                                            });
                                        }
                                    );
                            } else {
                                this.schedulerAdmin()
                                    .enableQueueProfile({
                                        queue_profile_id: this.getSelected()?.queue_profile_id,
                                    })
                                    .then(
                                        (_) => {
                                            this.setState(
                                                {
                                                    queueSelected: false,
                                                },
                                                () => {
                                                    this.props.onFlashbarChange({
                                                        items: [
                                                            {
                                                                type: "success",
                                                                content: `Queue Profile: ${this.getSelected()?.name} enabled successfully`,
                                                                dismissible: true,
                                                            },
                                                        ],
                                                    });
                                                    this.getListing().fetchRecords();
                                                }
                                            );
                                        },
                                        (error) => {
                                            this.props.onFlashbarChange({
                                                items: [
                                                    {
                                                        type: "error",
                                                        content: `Failed to enable queue profile: ${error.message}`,
                                                        dismissible: true,
                                                    },
                                                ],
                                            });
                                        }
                                    );
                            }
                        },
                    },
                ]}
                onRefresh={() => {
                    this.setState(
                        {
                            queueSelected: false,
                        },
                        () => {
                            this.getListing().fetchRecords();
                        }
                    );
                }}
                onSelectionChange={() => {
                    this.setState(
                        {
                            queueSelected: true,
                            splitPanelOpen: true,
                        },
                        () => {}
                    );
                }}
                onFetchRecords={() => {
                    return this.schedulerAdmin().listQueueProfiles({
                        filters: this.getListing().getFilters(),
                        paginator: this.getListing().getPaginator(),
                    });
                }}
                columnDefinitions={HPC_QUEUE_TABLE_COLUMN_DEFINITIONS}
            />
        );
    }

    buildSplitPanelContent() {
        const selected = () => this.getSelected()!;
        const jobParams = () => selected().default_job_params!;
        const queueParams = () => selected().queue_management_params!;
        const queueUtils = () => new QueueUtils(selected());
        return (
            this.isSelected() && (
                <IdeaSplitPanel title={`Queue Profile: ${this.getSelected()?.name}`}>
                    <Tabs
                        tabs={[
                            {
                                label: "Queue Info",
                                id: "queue-info",
                                content: (
                                    <ColumnLayout columns={3}>
                                        <KeyValue title="Queue Profile" value={selected().name} />
                                        <KeyValue title="Queues" value={selected().queues} />
                                        <KeyValue title="Is Enabled?" value={selected().enabled} />
                                        <KeyValue title="Queue Mode" value={selected().queue_mode} />
                                        {!Utils.asBoolean(selected().keep_forever) && <KeyValue title="Scaling Mode" value={selected().scaling_mode} />}
                                        <KeyValue title="Terminate When Idle" value={selected().terminate_when_idle} suffix="minutes" />
                                        <KeyValue title="Keep Forever?" value={selected().keep_forever} type="boolean" />
                                    </ColumnLayout>
                                ),
                            },
                            {
                                label: "ACLs",
                                id: "queue-acl",
                                content: (
                                    <ColumnLayout columns={3}>
                                        <KeyValue title="Allowed Instance Types" value={queueParams().allowed_instance_types} />
                                        <KeyValue title="Excluded Instance Types" value={queueParams().excluded_instance_types} />
                                        <KeyValue title="Restricted Parameters" value={queueParams().restricted_parameters} />
                                        <KeyValue title="Allowed Instance Profiles" value={queueParams().allowed_instance_profiles} />
                                        <KeyValue title="Allowed Security Groups" value={queueParams().allowed_security_groups} />
                                    </ColumnLayout>
                                ),
                            },
                            {
                                label: "Limits",
                                id: "queue-limits",
                                content: (
                                    <ColumnLayout columns={3}>
                                        <KeyValue title="Max Running Jobs" value={queueParams().max_running_jobs} />
                                        <KeyValue title="Max Provisioned Instances" value={queueParams().max_provisioned_instances} />
                                        <KeyValue title="Max Provisioned Capacity" value={queueParams().max_provisioned_capacity} />
                                        <KeyValue title="Block on any job with Licenses" value={queueParams().wait_on_any_job_with_license} type="boolean" />
                                    </ColumnLayout>
                                ),
                            },
                            {
                                label: "Compute Stack Parameters",
                                id: "compute-stack-parameters",
                                content: (
                                    <ColumnLayout columns={2}>
                                        <KeyValueGroup title="Instance Info">
                                            <KeyValue title="Base OS" value={jobParams().base_os} />
                                            <KeyValue title="Instance AMI" value={jobParams().instance_ami} />
                                            <KeyValue title="Instance Types" value={jobParams().instance_types} />
                                            <KeyValue title="Keep EBS Volumes" value={jobParams().keep_ebs_volumes} />
                                            <KeyValue title="Root Storage Size" value={jobParams().root_storage_size} type="memory" />
                                            <KeyValue title="Enable Elastic Fabric Adapter (EFA)" value={jobParams().enable_efa_support} />
                                            <KeyValue title="Force Reserved Instances" value={jobParams().force_reserved_instances} />
                                            <KeyValue title="Enable Hyper-Threading" value={jobParams().enable_ht_support} />
                                        </KeyValueGroup>

                                        <KeyValueGroup title="Network and Security">
                                            <KeyValue title="Subnet Ids" value={jobParams().subnet_ids} />
                                            <KeyValue title="Security Groups" value={jobParams().security_groups} />
                                            <KeyValue title="Instance Profile" value={jobParams().instance_profile} />
                                            <KeyValue title="Enable Placement Group" value={jobParams().enable_placement_group} />
                                        </KeyValueGroup>

                                        <KeyValueGroup title="Spot Fleet">
                                            <KeyValue title="Is Spot?" value={jobParams().spot} />
                                            {queueUtils().isEnableSpot() && <KeyValue title="Spot Price" value={jobParams().spot_price} type="amount" />}
                                            {queueUtils().isEnableSpot() && <KeyValue title="Spot Allocation Count" value={jobParams().spot_allocation_count} />}
                                            {queueUtils().isEnableSpot() && <KeyValue title="Spot Allocation Strategy" value={jobParams().spot_allocation_strategy} />}
                                        </KeyValueGroup>

                                        {!queueUtils().isScratchStorageEnabled() && (
                                            <KeyValueGroup title="Scratch Storage">
                                                <KeyValue title="Is Enabled?" value={false} />
                                            </KeyValueGroup>
                                        )}

                                        {queueUtils().isScratchEBS() && (
                                            <KeyValueGroup title="Scratch Storage: EBS">
                                                <KeyValue title="EBS: Storage Size" value={jobParams().scratch_storage_size} type="memory" />
                                                <KeyValue title="EBS Storage IOPS" value={jobParams().scratch_storage_iops} />
                                            </KeyValueGroup>
                                        )}

                                        {queueUtils().isScratchExistingFsxLustre() && (
                                            <KeyValueGroup title="Scratch Storage: Existing FSx for Lustre">
                                                <KeyValue title="Existing FSx Lustre" value={jobParams().fsx_lustre?.existing_fsx} />
                                            </KeyValueGroup>
                                        )}
                                        {queueUtils().isScratchNewFsxLustre() && (
                                            <KeyValueGroup title="Scratch Storage: New FSx for Lustre">
                                                <KeyValue title="S3 Backend" value={jobParams().fsx_lustre?.s3_backend} />
                                                <KeyValue title="Import Path" value={jobParams().fsx_lustre?.import_path} />
                                                <KeyValue title="Export Path" value={jobParams().fsx_lustre?.export_path} />
                                                <KeyValue title="Deployment Type" value={jobParams().fsx_lustre?.deployment_type} />
                                                <KeyValue title="Per Unit Throughput" value={jobParams().fsx_lustre?.per_unit_throughput} />
                                                <KeyValue title="Size" value={jobParams().fsx_lustre?.size} type="memory" />
                                            </KeyValueGroup>
                                        )}

                                        <KeyValueGroup title="Metrics">
                                            <KeyValue title="Enable System Metrics" value={jobParams().enable_system_metrics} />
                                            <KeyValue title="Enable Anonymous Metrics" value={jobParams().enable_anonymous_metrics} />
                                        </KeyValueGroup>
                                    </ColumnLayout>
                                ),
                            },
                        ]}
                    />
                </IdeaSplitPanel>
            )
        );
    }

    render() {
        return (
            <IdeaAppLayout
                ideaPageId={this.props.ideaPageId}
                toolsOpen={this.props.toolsOpen}
                tools={this.props.tools}
                onToolsChange={this.props.onToolsChange}
                onPageChange={this.props.onPageChange}
                sideNavHeader={this.props.sideNavHeader}
                sideNavItems={this.props.sideNavItems}
                onSideNavChange={this.props.onSideNavChange}
                onFlashbarChange={this.props.onFlashbarChange}
                flashbarItems={this.props.flashbarItems}
                breadcrumbItems={[
                    {
                        text: "IDEA",
                        href: "#/",
                    },
                    {
                        text: "Scale-Out Computing",
                        href: "#/soca/active-jobs",
                    },
                    {
                        text: "Queues",
                        href: "",
                    },
                ]}
                content={<div>{this.buildListing()}</div>}
                splitPanelOpen={this.state.splitPanelOpen}
                splitPanel={this.buildSplitPanelContent()}
                onSplitPanelToggle={(event: any) => {
                    this.setState({
                        splitPanelOpen: event.detail.open,
                    });
                }}
            />
        );
    }
}

export default withRouter(Queues);
