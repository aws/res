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
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import IdeaAppLayout, { IdeaAppLayoutProps } from "../../components/app-layout";
import IdeaListView from "../../components/list-view";
import Utils from "../../common/utils";
import { TableProps } from "@cloudscape-design/components/table/interfaces";
import { HpcLicenseResource } from "../../client/data-model";
import { SchedulerAdminClient } from "../../client";
import { AppContext } from "../../common";
import IdeaForm from "../../components/form";
import { ClusterSettingsService } from "../../service";
import { Link, Popover, StatusIndicator } from "@cloudscape-design/components";
import { withRouter } from "../../navigation/navigation-utils";

export interface HpcLicensesProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {}

export interface HpcLicensesState {
    licenseResourceSelected: boolean;
    createModalType: string;
    showCreateForm: boolean;
}

const LICENSE_RESOURCES_TABLE_COLUMN_DEFINITIONS: TableProps.ColumnDefinition<HpcLicenseResource>[] = [
    {
        id: "title",
        header: "Title",
        cell: (resource) => resource.title,
    },
    {
        id: "name",
        header: "Name",
        cell: (resource) => resource.name,
    },
    {
        id: "reserved_count",
        header: "Reserved Count",
        cell: (resource) => (resource.reserved_count ? resource.reserved_count : 0),
    },
    {
        id: "available_count",
        header: "Available Count",
        cell: (resource) => <CheckLicenseAvailability resource_name={resource.name!} />,
    },
    {
        id: "created_on",
        header: "Created On",
        cell: (resource) => new Date(resource.created_on!).toLocaleString(),
    },
];

interface CheckLicenseAvailabilityProps {
    resource_name: string;
}

interface CheckLicenseAvailabilityState {
    error_message: string;
    available_count: number;
    status?: boolean;
    loading: boolean;
}

class CheckLicenseAvailability extends Component<CheckLicenseAvailabilityProps, CheckLicenseAvailabilityState> {
    constructor(props: CheckLicenseAvailabilityProps) {
        super(props);
        this.state = {
            available_count: 0,
            status: undefined,
            error_message: "",
            loading: false,
        };
    }

    getAvailableCount() {
        if (typeof this.state.status === "undefined") {
            return (
                <StatusIndicator type={"in-progress"} colorOverride={"grey"}>
                    &nbsp;
                </StatusIndicator>
            );
        } else {
            if (this.state.status) {
                if (this.state.available_count === 0) {
                    return <StatusIndicator type={"warning"}>No Licences Available</StatusIndicator>;
                } else {
                    return <StatusIndicator type={"success"}>{this.state.available_count === 1 ? "1 license" : `${this.state.available_count} licenses`} available</StatusIndicator>;
                }
            } else {
                return (
                    <Popover dismissButton={false} position="top" size="small" triggerType="custom" content={this.state.error_message}>
                        <StatusIndicator type={"error"}>Failed</StatusIndicator>
                    </Popover>
                );
            }
        }
    }

    checkAvailability = () => {
        this.setState(
            {
                loading: true,
            },
            () => {
                AppContext.get()
                    .client()
                    .schedulerAdmin()
                    .checkHpcLicenseResourceAvailability({
                        name: this.props.resource_name,
                    })
                    .then((result) => {
                        this.setState({
                            available_count: Utils.asNumber(result.available_count, 0),
                            status: true,
                            loading: false,
                        });
                    })
                    .catch((error) => {
                        this.setState({
                            status: false,
                            error_message: error.message,
                            loading: false,
                        });
                    });
            }
        );
    };

    render() {
        return (
            <div>
                {!this.state.loading && (
                    <div>
                        <span>{this.getAvailableCount()}</span>&nbsp;&nbsp;(
                        <Link fontSize="body-s" onFollow={this.checkAvailability}>
                            Check Availability
                        </Link>
                        )
                    </div>
                )}
                {this.state.loading && <StatusIndicator type="loading" />}
            </div>
        );
    }
}

class HpcLicenses extends Component<HpcLicensesProps, HpcLicensesState> {
    listing: RefObject<IdeaListView>;
    createForm: RefObject<IdeaForm>;

    constructor(props: HpcLicensesProps) {
        super(props);
        this.listing = React.createRef();
        this.createForm = React.createRef();
        this.state = {
            licenseResourceSelected: false,
            createModalType: "",
            showCreateForm: false,
        };
    }

    isSelected(): boolean {
        return this.state.licenseResourceSelected;
    }

    getSelected(): HpcLicenseResource | null {
        if (this.getListing() == null) {
            return null;
        }
        return this.getListing().getSelectedItem();
    }

    getListing(): IdeaListView {
        return this.listing.current!;
    }

    getCreateForm(): IdeaForm {
        return this.createForm.current!;
    }

    schedulerAdmin(): SchedulerAdminClient {
        return AppContext.get().client().schedulerAdmin();
    }

    clusterSettings(): ClusterSettingsService {
        return AppContext.get().getClusterSettingsService();
    }

    buildListing() {
        return (
            <IdeaListView
                ref={this.listing}
                preferencesKey={"licenses"}
                showPreferences={false}
                title="Licenses"
                description="Scale-Out License Resource Management"
                selectionType="single"
                primaryAction={{
                    id: "create-license-resource",
                    text: "Create License Resource",
                    onClick: () => {
                        this.props.navigate("/soca/licenses/create");
                    },
                }}
                secondaryActionsDisabled={!this.isSelected()}
                secondaryActions={[
                    {
                        id: "edit-license-resource",
                        text: "Edit License Resource",
                        onClick: () => {
                            this.props.navigate(`/soca/licenses/update?name=${this.getSelected()?.name}`);
                        },
                    },
                ]}
                showPaginator={true}
                showFilters={true}
                filters={[
                    {
                        key: "name",
                    },
                ]}
                onFilter={(filters) => {
                    const licenseResourceNameToken = Utils.asString(filters[0].value).trim().toLowerCase();
                    if (Utils.isEmpty(licenseResourceNameToken)) {
                        return [];
                    } else {
                        return [
                            {
                                key: "name",
                                like: licenseResourceNameToken,
                            },
                        ];
                    }
                }}
                onRefresh={() => {
                    this.setState(
                        {
                            licenseResourceSelected: false,
                        },
                        () => {
                            this.getListing().fetchRecords();
                        }
                    );
                }}
                onSelectionChange={() => {
                    this.setState(
                        {
                            licenseResourceSelected: true,
                        },
                        () => {}
                    );
                }}
                onFetchRecords={() => {
                    return this.schedulerAdmin().listHpcLicenseResources({
                        filters: this.getListing().getFilters(),
                        paginator: this.getListing().getPaginator(),
                        date_range: this.getListing().getDateRange(),
                    });
                }}
                columnDefinitions={LICENSE_RESOURCES_TABLE_COLUMN_DEFINITIONS}
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
                        text: "Licenses",
                        href: "",
                    },
                ]}
                content={this.buildListing()}
            />
        );
    }
}

export default withRouter(HpcLicenses);
