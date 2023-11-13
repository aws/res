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

import { TableProps } from "@cloudscape-design/components/table/interfaces";
import { HpcApplication } from "../../client/data-model";
import IdeaListView from "../../components/list-view";
import { SchedulerAdminClient } from "../../client";
import { AppContext } from "../../common";
import IdeaConfirm from "../../components/modals";
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import IdeaAppLayout, { IdeaAppLayoutProps } from "../../components/app-layout";
import Utils from "../../common/utils";
import { withRouter } from "../../navigation/navigation-utils";

export interface HpcApplicationsProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {}

export interface HpcApplicationsState {
    applicationSelected: boolean;
}

const APPLICATIONS_TABLE_COLUMN_DEFINITIONS: TableProps.ColumnDefinition<HpcApplication>[] = [
    {
        id: "thumbnail",
        header: "Thumbnail",
        cell: (application) => {
            if (application.thumbnail_data) {
                return <img width={80} src={application.thumbnail_data} alt={application.title} />;
            } else if (application.thumbnail_url) {
                return <img width={80} src={application.thumbnail_url} alt={application.title} />;
            } else {
                return <div className="application-placeholder-image">No Image</div>;
            }
        },
    },
    {
        id: "title",
        header: "Title",
        cell: (application) => application.title,
    },
    {
        id: "projects",
        header: "Projects",
        cell: (application) => {
            if (Utils.isEmpty(application.projects)) {
                return "-";
            }
            return (
                <div>
                    {application.projects?.map((project, index) => {
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
        id: "updated_on",
        header: "Updated On",
        cell: (application) => new Date(application.updated_on!).toLocaleString(),
    },
];

class HpcApplications extends Component<HpcApplicationsProps, HpcApplicationsState> {
    listing: RefObject<IdeaListView>;
    deleteApplicationConfirmModal: RefObject<IdeaConfirm>;

    constructor(props: HpcApplicationsProps) {
        super(props);
        this.listing = React.createRef();
        this.deleteApplicationConfirmModal = React.createRef();
        this.state = {
            applicationSelected: false,
        };
    }

    schedulerAdmin(): SchedulerAdminClient {
        return AppContext.get().client().schedulerAdmin();
    }

    getListing(): IdeaListView {
        return this.listing.current!;
    }

    getDeleteApplicationConfirmModal(): IdeaConfirm {
        return this.deleteApplicationConfirmModal.current!;
    }

    isSelected(): boolean {
        return this.state.applicationSelected;
    }

    getSelected(): HpcApplication | null {
        if (this.getListing() == null) {
            return null;
        }
        return this.getListing().getSelectedItem();
    }

    buildDeleteApplicationConfirmModal() {
        return (
            <IdeaConfirm
                ref={this.deleteApplicationConfirmModal}
                title="Delete Application"
                onConfirm={() => {
                    this.schedulerAdmin()
                        .deleteHpcApplication({
                            application_id: this.getSelected()?.application_id,
                        })
                        .then(() => {
                            this.getListing().fetchRecords();
                        })
                        .catch((error) => {
                            this.getListing().setFlashMessage(`Failed to delete application: ${error.message}`, "error");
                        });
                }}
            >
                Are you sure you want to delete application: <b>{this.getSelected()?.title}</b> ?
            </IdeaConfirm>
        );
    }

    buildListing() {
        return (
            <IdeaListView
                ref={this.listing}
                title="Applications"
                preferencesKey={"applications"}
                showPreferences={false}
                description="Scale-Out Applications"
                selectionType="single"
                primaryAction={{
                    id: "create-project",
                    text: "Create Application",
                    onClick: () => {
                        this.props.navigate("/soca/applications/create");
                    },
                }}
                secondaryActionsDisabled={!this.isSelected()}
                secondaryActions={[
                    {
                        id: "edit-application",
                        text: "Edit Application",
                        onClick: () => {
                            this.props.navigate(`/soca/applications/update?id=${this.getSelected()?.application_id}`);
                        },
                    },
                    {
                        id: "delete-application",
                        text: "Delete Application",
                        onClick: () => {
                            this.getDeleteApplicationConfirmModal().show();
                        },
                    },
                ]}
                showPaginator={true}
                showFilters={true}
                filters={[
                    {
                        key: "title",
                    },
                ]}
                onFilter={(filters) => {
                    const titleToken = Utils.asString(filters[0].value).trim().toLowerCase();
                    if (Utils.isEmpty(titleToken)) {
                        return [];
                    } else {
                        return [
                            {
                                key: "title",
                                like: titleToken,
                            },
                        ];
                    }
                }}
                onRefresh={() => {
                    this.setState(
                        {
                            applicationSelected: false,
                        },
                        () => {
                            this.getListing().fetchRecords();
                        }
                    );
                }}
                onSelectionChange={() => {
                    this.setState(
                        {
                            applicationSelected: true,
                        },
                        () => {}
                    );
                }}
                onFetchRecords={() => {
                    return this.schedulerAdmin().listHpcApplications({
                        filters: this.getListing().getFilters(),
                        paginator: this.getListing().getPaginator(),
                    });
                }}
                columnDefinitions={APPLICATIONS_TABLE_COLUMN_DEFINITIONS}
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
                        text: "Applications",
                        href: "",
                    },
                ]}
                content={
                    <div>
                        {this.buildDeleteApplicationConfirmModal()}
                        {this.buildListing()}
                    </div>
                }
            />
        );
    }
}

export default withRouter(HpcApplications);
