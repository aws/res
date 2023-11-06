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
import { TableProps } from "@cloudscape-design/components/table/interfaces";
import { DeleteJobRequest, DeleteJobResult, SocaJob } from "../../client/data-model";
import { AppContext } from "../../common";
import { SchedulerAdminClient, SchedulerClient } from "../../client";
import IdeaSplitPanel from "../../components/split-panel";
import { Box, ColumnLayout, Popover, StatusIndicator, Table, Tabs } from "@cloudscape-design/components";
import { KeyValue, KeyValueGroup } from "../../components/key-value";
import Utils from "../../common/utils";
import { JobUtils } from "./hpc-utils";
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import IdeaAppLayout, { IdeaAppLayoutProps } from "../../components/app-layout";
import { withRouter } from "../../navigation/navigation-utils";

export const JOB_TABLE_COLUMN_DEFINITIONS: TableProps.ColumnDefinition<SocaJob>[] = [
    {
        id: "id",
        header: "Job Id",
        cell: (job) => job.job_id,
    },
    {
        id: "name",
        header: "Name",
        cell: (job) => job.name,
    },
    {
        id: "owner",
        header: "Owner",
        cell: (job) => job.owner,
    },
    {
        id: "queue",
        header: "Queue",
        cell: (job) => job.queue,
    },
    {
        id: "project",
        header: "Project",
        cell: (job) => job.project,
    },
    {
        id: "status",
        header: "Status",
        cell: (job) => {
            if (job.params?.compute_stack === "tbd") {
                if (Utils.isEmpty(job.error_message)) {
                    return <StatusIndicator type="pending">Queued</StatusIndicator>;
                } else {
                    return (
                        <Box color="text-status-error">
                            <Popover dismissAriaLabel="Close" header="Job cannot be provisioned currently ..." content={job.error_message}>
                                <StatusIndicator type="info">Queued</StatusIndicator>
                            </Popover>
                        </Box>
                    );
                }
            } else if (job.params?.compute_stack !== "tbd") {
                if (job.state === "queued") {
                    return (
                        <StatusIndicator type="in-progress" colorOverride="blue">
                            Provisioning
                        </StatusIndicator>
                    );
                } else if (job.state === "running") {
                    return <StatusIndicator type="success">Running</StatusIndicator>;
                } else {
                    return (
                        <StatusIndicator type="success" colorOverride="grey">
                            Finished
                        </StatusIndicator>
                    );
                }
            }
        },
    },
    {
        id: "queued-on",
        header: "Queue Time",
        cell: (job) => new Date(job.queue_time!).toLocaleString(),
    },
];

export interface JobsProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {
    type: string; // active, completed
    scope: string; // user, admin
}

export interface JobsState {
    splitPanelOpen: boolean;
    jobSelected: boolean;
}

class Jobs extends Component<JobsProps, JobsState> {
    listing: RefObject<IdeaListView>;

    constructor(props: JobsProps) {
        super(props);
        this.listing = React.createRef();
        this.state = {
            splitPanelOpen: false,
            jobSelected: false,
        };
    }

    schedulerAdmin(): SchedulerAdminClient {
        return AppContext.get().client().schedulerAdmin();
    }

    scheduler(): SchedulerClient {
        return AppContext.get().client().scheduler();
    }

    getListing(): IdeaListView {
        return this.listing.current!;
    }

    isSelected(): boolean {
        return this.state.jobSelected;
    }

    getSelected(): SocaJob | null {
        if (this.getListing() == null) {
            return null;
        }
        return this.getListing().getSelectedItem();
    }

    isActiveJobs(): boolean {
        return this.props.type === "active";
    }

    isCompletedJobs(): boolean {
        return this.props.type === "completed";
    }

    buildListing() {
        let columnDefinitions = [...JOB_TABLE_COLUMN_DEFINITIONS];
        if (this.isCompletedJobs()) {
            columnDefinitions.push({
                id: "exit_code",
                header: "Exit Status",
                cell: (job) => job.exit_status,
            });
        }
        return (
            <IdeaListView
                ref={this.listing}
                preferencesKey={"hpc-jobs"}
                showPreferences={true}
                title={this.isActiveJobs() ? "Active Jobs" : "Completed Jobs"}
                description={this.isActiveJobs() ? "All active Jobs" : "All completed Jobs"}
                selectionType="single"
                // todo - commented until file picker UI is implemented in submit job form
                // primaryAction={{
                //     id: 'submit-job',
                //     text: 'Submit Job',
                //     onClick: () => {
                //         this.props.history.push('/soca/jobs/submit-job')
                //     }
                // }}
                secondaryActionsDisabled={this.isCompletedJobs()}
                secondaryActions={[
                    {
                        id: "delete-job",
                        text: "Delete Job",
                        disabled: !this.isSelected(),
                        onClick: () => {
                            const deleteJob = (request: DeleteJobRequest): Promise<DeleteJobResult> => {
                                if (this.props.scope === "admin") {
                                    return this.schedulerAdmin().deleteJob(request);
                                } else {
                                    return this.scheduler().deleteJob(request);
                                }
                            };

                            deleteJob({
                                job_id: this.getSelected()?.job_id,
                            })
                                .then(() => {
                                    this.props.onFlashbarChange({
                                        items: [
                                            {
                                                type: "info",
                                                content: `Job Id: ${this.getSelected()?.job_id} will be deleted shortly.`,
                                                dismissible: true,
                                            },
                                        ],
                                    });
                                    this.getListing().fetchRecords();
                                })
                                .catch((error) => {
                                    this.props.onFlashbarChange({
                                        items: [
                                            {
                                                type: "error",
                                                content: error.message,
                                                dismissible: true,
                                            },
                                        ],
                                    });
                                });
                        },
                    },
                ]}
                showPaginator={true}
                showFilters={true}
                showDateRange={this.props.type === "completed"}
                dateRange={{
                    type: "relative",
                    amount: 1,
                    unit: "month",
                }}
                dateRangeFilterKeyOptions={[{ value: "queue_time", label: "Queued" }]}
                filters={[
                    {
                        key: "any",
                    },
                ]}
                onFilter={(filters) => {
                    const filterString = Utils.asString(filters[0].value).trim();
                    if (Utils.isEmpty(filterString)) {
                        return [];
                    } else if (Utils.isPositiveInteger(filterString)) {
                        return [
                            {
                                key: "job_id",
                                value: filterString,
                            },
                        ];
                    } else if (filterString.includes(",")) {
                        const jobIds = filterString.split(",");
                        return [
                            {
                                key: "job_id",
                                value: jobIds.map((jobId) => jobId.trim().toLowerCase()),
                            },
                        ];
                    } else {
                        return [
                            {
                                key: "$all",
                                value: filterString,
                            },
                        ];
                    }
                }}
                onRefresh={() => {
                    this.setState(
                        {
                            jobSelected: false,
                        },
                        () => {
                            this.getListing().fetchRecords();
                        }
                    );
                }}
                onSelectionChange={() => {
                    this.setState(
                        {
                            splitPanelOpen: true,
                            jobSelected: true,
                        },
                        () => {}
                    );
                }}
                onFetchRecords={() => {
                    if (this.props.scope === "user") {
                        if (this.props.type === "active") {
                            return this.scheduler().listActiveJobs({
                                filters: this.getListing().getFilters(),
                                paginator: this.getListing().getPaginator(),
                            });
                        } else {
                            return this.scheduler().listCompletedJobs({
                                filters: this.getListing().getFilters(),
                                paginator: this.getListing().getPaginator(),
                                date_range: this.getListing().getFormatedDateRange(),
                            });
                        }
                    } else {
                        if (this.props.type === "active") {
                            return this.schedulerAdmin().listActiveJobs({
                                filters: this.getListing().getFilters(),
                                paginator: this.getListing().getPaginator(),
                            });
                        } else {
                            return this.schedulerAdmin().listCompletedJobs({
                                filters: this.getListing().getFilters(),
                                paginator: this.getListing().getPaginator(),
                                date_range: this.getListing().getFormatedDateRange(),
                            });
                        }
                    }
                }}
                columnDefinitions={columnDefinitions}
            />
        );
    }

    buildSplitPanelContent() {
        const selected = () => this.getSelected()!;
        const jobUtil = () => new JobUtils(selected());
        const jobParams = () => selected().params!;
        return (
            this.isSelected() && (
                <IdeaSplitPanel title={`JobId: ${this.getSelected()?.job_id}`}>
                    <Tabs
                        tabs={[
                            {
                                label: "Job Info",
                                id: "job-info",
                                content: (
                                    <ColumnLayout columns={3} variant="text-grid">
                                        <KeyValue title="State" value={selected().state} />
                                        <KeyValue title="Job Id" value={selected().job_id} />
                                        <KeyValue title="Job Group" value={selected().job_group} clipboard={true} />
                                        <KeyValue title="Queue" value={selected().queue} />
                                        <KeyValue title="Queue Type" value={selected().queue_type} />
                                        <KeyValue title="Scaling Mode" value={selected().scaling_mode} />
                                        <KeyValue title="Name" value={selected().name} />
                                        <KeyValue title="Project" value={selected().project} />
                                        <KeyValue title="Owner" value={selected().owner} />
                                        <KeyValue title="Queue Time" value={selected().queue_time} type="date" />
                                        <KeyValue title="Start Time" value={selected().start_time} type="date" />
                                        <KeyValue title="End Time" value={selected().end_time} type="date" />
                                        <KeyValue title="Comment" value={selected().comment} clipboard={true} />
                                    </ColumnLayout>
                                ),
                            },
                            {
                                label: "Compute Stack",
                                id: "compute-stack",
                                content: (
                                    <ColumnLayout columns={2} variant="text-grid">
                                        <KeyValueGroup title="Instance Info">
                                            <KeyValue title="Base OS" value={jobParams().base_os} />
                                            <KeyValue title="Instance AMI" value={jobParams().instance_ami} clipboard={true} />
                                            <KeyValue title="Instance Types" value={jobParams().instance_types} />
                                            <KeyValue title="Keep EBS Volumes" value={jobParams().keep_ebs_volumes} />
                                            <KeyValue title="Root Storage Size" value={jobParams().root_storage_size} type="memory" />
                                            <KeyValue title="Enable Elastic Fabric Adapter (EFA)" value={jobParams().enable_efa_support} />
                                            <KeyValue title="Force Reserved Instances" value={jobParams().force_reserved_instances} />
                                            <KeyValue title="Enable Hyper-Threading" value={jobParams().enable_ht_support} />
                                        </KeyValueGroup>

                                        <KeyValueGroup title="Network and Security">
                                            <KeyValue title="Subnet Ids" value={jobParams().subnet_ids} clipboard={true} />
                                            <KeyValue title="Security Groups" value={jobParams().security_groups} clipboard={true} />
                                            <KeyValue title="Instance Profile" value={jobParams().instance_profile} />
                                            <KeyValue title="Enable Placement Group" value={jobParams().enable_placement_group} />
                                        </KeyValueGroup>

                                        <KeyValueGroup title="Compute Requirements">
                                            <KeyValue title="Nodes" value={jobParams().nodes} />
                                            <KeyValue title="CPUs" value={jobParams().cpus} />
                                        </KeyValueGroup>

                                        <KeyValueGroup title="Spot Fleet">
                                            <KeyValue title="Is Spot?" value={jobParams().spot} />
                                            {jobUtil().isEnableSpot() && <KeyValue title="Spot Price" value={jobParams().spot_price} type="amount" />}
                                            {jobUtil().isEnableSpot() && <KeyValue title="Spot Allocation Count" value={jobParams().spot_allocation_count} />}
                                            {jobUtil().isEnableSpot() && <KeyValue title="Spot Allocation Strategy" value={jobParams().spot_allocation_strategy} />}
                                        </KeyValueGroup>

                                        {!jobUtil().isScratchStorageEnabled() && (
                                            <KeyValueGroup title="Scratch Storage">
                                                <KeyValue title="Is Enabled?" value={false} />
                                            </KeyValueGroup>
                                        )}

                                        {jobUtil().isScratchEBS() && (
                                            <KeyValueGroup title="Scratch Storage: EBS">
                                                <KeyValue title="EBS: Storage Size" value={jobParams().scratch_storage_size} type="memory" />
                                                <KeyValue title="EBS Storage IOPS" value={jobParams().scratch_storage_iops} />
                                            </KeyValueGroup>
                                        )}

                                        {jobUtil().isScratchExistingFsxLustre() && (
                                            <KeyValueGroup title="Scratch Storage: Existing FSx for Lustre">
                                                <KeyValue title="Existing FSx Lustre" value={jobParams().fsx_lustre?.existing_fsx} />
                                            </KeyValueGroup>
                                        )}
                                        {jobUtil().isScratchNewFsxLustre() && (
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
                            {
                                label: "Execution Hosts",
                                id: "execution-hosts",
                                content: (
                                    <Table
                                        items={selected().execution_hosts ? selected().execution_hosts! : []}
                                        columnDefinitions={[
                                            {
                                                id: "host",
                                                header: "Host",
                                                cell: (host) => host.host,
                                            },
                                            {
                                                id: "instance-id",
                                                header: "Instance Id",
                                                cell: (host) => host.instance_id,
                                            },
                                            {
                                                id: "instance-type",
                                                header: "Instance Type",
                                                cell: (host) => host.instance_type,
                                            },
                                            {
                                                id: "capacity-type",
                                                header: "Capacity Type",
                                                cell: (host) => host.capacity_type,
                                            },
                                            {
                                                id: "tenancy",
                                                header: "Tenancy",
                                                cell: (host) => host.tenancy,
                                            },
                                        ]}
                                    />
                                ),
                            },
                            {
                                label: "Estimated Costs",
                                id: "estimated-costs",
                                content: (
                                    <ColumnLayout columns={1}>
                                        <Table
                                            items={selected().estimated_bom_cost ? selected().estimated_bom_cost!.line_items! : []}
                                            columnDefinitions={[
                                                {
                                                    id: "title",
                                                    header: "Item",
                                                    cell: (item) => item.title,
                                                },
                                                {
                                                    id: "qty",
                                                    header: "Qty",
                                                    cell: (item) => item.quantity,
                                                },
                                                {
                                                    id: "unit",
                                                    header: "Unit",
                                                    cell: (item) => item.unit,
                                                },
                                                {
                                                    id: "unit-price",
                                                    header: "Unit Price",
                                                    cell: (item) => Utils.getFormattedAmount(item.unit_price),
                                                },
                                                {
                                                    id: "total-price",
                                                    header: "Total Price",
                                                    cell: (item) => Utils.getFormattedAmount(item.total_price),
                                                },
                                            ]}
                                        />
                                        <ColumnLayout columns={2}>
                                            <Box textAlign="left">
                                                <h3>Estimated Total Cost</h3>
                                            </Box>
                                            <Box textAlign="right">
                                                <h3>{Utils.getFormattedAmount(selected().estimated_bom_cost?.total)}</h3>
                                            </Box>
                                        </ColumnLayout>
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
        const breadcrumbs = () => {
            if (this.props.scope === "user") {
                if (this.props.type === "active") {
                    return [
                        {
                            text: "IDEA",
                            href: "#/",
                        },
                        {
                            text: "Home",
                            href: "#/",
                        },
                        {
                            text: "Active Jobs",
                            href: "#/home/active-jobs",
                        },
                    ];
                } else {
                    return [
                        {
                            text: "IDEA",
                            href: "#/",
                        },
                        {
                            text: "Home",
                            href: "#/",
                        },
                        {
                            text: "Completed Jobs",
                            href: "#/home/completed-jobs",
                        },
                    ];
                }
            } else {
                if (this.props.type === "active") {
                    return [
                        {
                            text: "IDEA",
                            href: "#/",
                        },
                        {
                            text: "Scale-Out Computing",
                            href: "#/soca/active-jobs",
                        },
                        {
                            text: "Active Jobs",
                            href: "",
                        },
                    ];
                } else {
                    return [
                        {
                            text: "IDEA",
                            href: "#/",
                        },
                        {
                            text: "Scale-Out Computing",
                            href: "#/soca/active-jobs",
                        },
                        {
                            text: "Completed Jobs",
                            href: "",
                        },
                    ];
                }
            }
        };

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
                breadcrumbItems={breadcrumbs()}
                content={<div>{this.buildListing()}</div>}
                splitPanelOpen={this.state.splitPanelOpen}
                splitPanel={this.buildSplitPanelContent()}
                onSplitPanelToggle={(event: any) => {
                    this.setState({
                        jobSelected: false,
                        splitPanelOpen: event.detail.open,
                    });
                }}
            />
        );
    }
}

function _ActiveJobs(props: JobsProps) {
    return <Jobs {...props} type="active" scope="user" />;
}

function _CompletedJobs(props: JobsProps) {
    return <Jobs {...props} type="completed" scope="user" />;
}

function _AdminActiveJobs(props: JobsProps) {
    return <Jobs {...props} type="active" scope="admin" />;
}

function _AdminCompletedJobs(props: JobsProps) {
    return <Jobs {...props} type="completed" scope="admin" />;
}

export const ActiveJobs = withRouter(_ActiveJobs);
export const CompletedJobs = withRouter(_CompletedJobs);
export const AdminActiveJobs = withRouter(_AdminActiveJobs);
export const AdminCompletedJobs = withRouter(_AdminCompletedJobs);
