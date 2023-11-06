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
import { SocaComputeNode } from "../../client/data-model";
import { AppContext } from "../../common";
import { SchedulerAdminClient } from "../../client";
import Utils from "../../common/utils";
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import IdeaAppLayout, { IdeaAppLayoutProps } from "../../components/app-layout";
import { withRouter } from "../../navigation/navigation-utils";

export interface HpcNodesProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {}

export interface HpcNodesState {
    nodeSelected: boolean;
}

export const NODE_TABLE_COLUMN_DEFINITIONS: TableProps.ColumnDefinition<SocaComputeNode>[] = [
    {
        id: "id",
        header: "Job Id",
        cell: (node) => node.job_id,
    },
    {
        id: "compute_stack",
        header: "Stack Name",
        cell: (node) => node.compute_stack,
    },
    {
        id: "instance_type",
        header: "Instance Type",
        cell: (node) => node.instance_type,
    },
    {
        id: "host",
        header: "Host",
        cell: (node) => node.host,
    },
    {
        id: "instance_id",
        header: "Instance Id",
        cell: (node) => node.instance_id,
    },
    {
        id: "is_running",
        header: "Is Running?",
        cell: (node) => (node.terminated ? "No" : "Yes"),
    },
    {
        id: "launch-time",
        header: "Launch Time",
        cell: (node) => new Date(node.launch_time!).toLocaleString(),
    },
];

class HpcNodes extends Component<HpcNodesProps, HpcNodesState> {
    listing: RefObject<IdeaListView>;

    constructor(props: HpcNodesProps) {
        super(props);
        this.listing = React.createRef();
        this.state = {
            nodeSelected: false,
        };
    }

    schedulerAdmin(): SchedulerAdminClient {
        return AppContext.get().client().schedulerAdmin();
    }

    getListing(): IdeaListView {
        return this.listing.current!;
    }

    isSelected(): boolean {
        return this.state.nodeSelected;
    }

    getSelected(): SocaComputeNode | null {
        if (this.getListing() == null) {
            return null;
        }
        return this.getListing().getSelectedItem();
    }

    buildListing() {
        return (
            <IdeaListView
                ref={this.listing}
                preferencesKey={"hpc-nodes"}
                showPreferences={true}
                title="Nodes"
                description="Scale-Out Compute Nodes"
                selectionType="single"
                showPaginator={true}
                showFilters={true}
                showDateRange={true}
                dateRange={{
                    type: "relative",
                    amount: 1,
                    unit: "month",
                }}
                dateRangeFilterKeyOptions={[{ value: "launch_time", label: "Launched" }]}
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
                            nodeSelected: false,
                        },
                        () => {
                            this.getListing().fetchRecords();
                        }
                    );
                }}
                onSelectionChange={() => {
                    this.setState(
                        {
                            nodeSelected: true,
                        },
                        () => {}
                    );
                }}
                onFetchRecords={() => {
                    return this.schedulerAdmin().listNodes({
                        filters: this.getListing().getFilters(),
                        paginator: this.getListing().getPaginator(),
                        date_range: this.getListing().getFormatedDateRange(),
                    });
                }}
                columnDefinitions={NODE_TABLE_COLUMN_DEFINITIONS}
            />
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
                        text: "Nodes",
                        href: "",
                    },
                ]}
                content={this.buildListing()}
            />
        );
    }
}

export default withRouter(HpcNodes);
