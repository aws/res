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
import { AppContext } from "../../common";
import { Group } from "../../client/data-model";
import IdeaListView from "../../components/list-view";
import IdeaSplitPanel from "../../components/split-panel";
import { USER_TABLE_COLUMN_DEFINITIONS } from "./users";
import Utils from "../../common/utils";
import IdeaConfirm from "../../components/modals";
import { AccountsClient } from "../../client";
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import IdeaAppLayout, { IdeaAppLayoutProps } from "../../components/app-layout";
import { StatusIndicator } from "@cloudscape-design/components";
import { withRouter } from "../../navigation/navigation-utils";

export interface GroupsProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {}

export interface GroupsState {
    splitPanelOpen: boolean;
    groupSelected: boolean;
    userInGroupSelected: boolean;
}

class Groups extends Component<GroupsProps, GroupsState> {
    deleteGroupConfirmModal: RefObject<IdeaConfirm>;
    listing: RefObject<IdeaListView>;
    userListing: RefObject<IdeaListView>;

    constructor(props: GroupsProps) {
        super(props);
        this.deleteGroupConfirmModal = React.createRef();
        this.listing = React.createRef();
        this.userListing = React.createRef();
        this.state = {
            splitPanelOpen: false,
            groupSelected: false,
            userInGroupSelected: false,
        };
    }

    authAdmin(): AccountsClient {
        return AppContext.get().client().accounts();
    }

    getEnableDisableGroupConfirmModal(): IdeaConfirm {
        return this.deleteGroupConfirmModal.current!;
    }

    getListing(): IdeaListView {
        return this.listing.current!;
    }

    getUserListing(): IdeaListView {
        return this.userListing.current!;
    }

    isSelected(): boolean {
        return this.state.groupSelected;
    }

    isSelectedGroupEnabled(): boolean {
        if (!this.isSelected()) {
            return false;
        }
        return Utils.asBoolean(this.getSelected()?.enabled);
    }

    getSelected(): Group | null {
        if (this.getListing() == null) {
            return null;
        }
        return this.getListing().getSelectedItem();
    }

    isUserInGroupSelected(): boolean {
        return this.state.userInGroupSelected;
    }

    buildEnableDisableGroupConfirmModal() {
        let message;
        if (this.isSelectedGroupEnabled()) {
            message = "Are you sure you want to disable group: ";
        } else {
            message = "Are you sure you want to enable group: ";
        }
        return (
            <IdeaConfirm
                ref={this.deleteGroupConfirmModal}
                title={this.isSelectedGroupEnabled() ? "Disable Group" : "Enable Group"}
                onConfirm={() => {
                    const groupName = this.getSelected()!.name!;
                    if (this.isSelectedGroupEnabled()) {
                        this.authAdmin()
                            .disableGroup({
                                group_name: groupName,
                            })
                            .then((_) => {
                                this.setState(
                                    {
                                        groupSelected: false,
                                    },
                                    () => {
                                        this.props.onFlashbarChange({
                                            items: [
                                                {
                                                    type: "success",
                                                    content: `Group: ${groupName} disabled successfully.`,
                                                    dismissible: true,
                                                },
                                            ],
                                        });
                                        this.getListing().fetchRecords();
                                    }
                                );
                            })
                            .catch((error) => {
                                this.props.onFlashbarChange({
                                    items: [
                                        {
                                            type: "error",
                                            content: `Failed to disable group: ${error.message}`,
                                            dismissible: true,
                                        },
                                    ],
                                });
                            });
                    } else {
                        this.authAdmin()
                            .enableGroup({
                                group_name: groupName,
                            })
                            .then((_) => {
                                this.setState(
                                    {
                                        groupSelected: false,
                                    },
                                    () => {
                                        this.props.onFlashbarChange({
                                            items: [
                                                {
                                                    type: "success",
                                                    content: `Group: ${groupName} enabled successfully.`,
                                                    dismissible: true,
                                                },
                                            ],
                                        });
                                        this.getListing().fetchRecords();
                                    }
                                );
                            })
                            .catch((error) => {
                                this.props.onFlashbarChange({
                                    items: [
                                        {
                                            type: "error",
                                            content: `Failed to enable group: ${error.message}`,
                                            dismissible: true,
                                        },
                                    ],
                                });
                            });
                    }
                }}
            >
                {message} <b>{this.getSelected()?.name}</b> ?
            </IdeaConfirm>
        );
    }



    buildListView() {
        return (
            <IdeaListView
                ref={this.listing}
                title="Groups"
                preferencesKey={"groups"}
                showPreferences={false}
                description="Environment user group management"
                secondaryActionsDisabled={!this.isSelected()}
                secondaryActions={[
                    {
                        id: "enable-disable-group",
                        text: this.isSelectedGroupEnabled() ? "Disable Group" : "Enable group",
                        onClick: () => {
                            this.getEnableDisableGroupConfirmModal().show();
                        },
                    },
                ]}
                showPaginator={true}
                showFilters={true}
                filters={[
                    {
                        key: "group_name",
                    },
                ]}
                onFilter={(filters) => {
                    const groupNameToken = Utils.asString(filters[0].value).trim().toLowerCase();
                    if (Utils.isEmpty(groupNameToken)) {
                        return [];
                    } else {
                        return [
                            {
                                key: "group_name",
                                like: groupNameToken,
                            },
                        ];
                    }
                }}
                onRefresh={() => {
                    this.setState(
                        {
                            groupSelected: false,
                        },
                        () => {
                            this.getListing().fetchRecords();
                        }
                    );
                }}
                selectionType="single"
                onSelectionChange={(_) => {
                    this.setState(
                        {
                            groupSelected: true,
                            userInGroupSelected: false,
                        },
                        () => {
                            this.getUserListing().fetchRecords();
                        }
                    );
                }}
                onFetchRecords={() => {
                    return AppContext.get()
                        .client()
                        .accounts()
                        .listGroups({
                            paginator: this.getListing().getPaginator(),
                            filters: [
                                ...this.getListing().getFilters(),
                                {
                                    key: "group_type",
                                    eq: "project",
                                },
                            ],
                        });
                }}
                columnDefinitions={[
                    {
                        id: "title",
                        header: "Title",
                        cell: (e) => e.title,
                    },
                    {
                        id: "name",
                        header: "Group Name",
                        cell: (e) => e.name,
                    },
                    {
                        id: "type",
                        header: "Type",
                        cell: (e) => e.type,
                    },
                    {
                        id: "group_role",
                        header: "Role",
                        cell: (e) => e.role,
                    },
                    {
                        id: "enabled",
                        header: "Status",
                        cell: (e) => (e.enabled ? <StatusIndicator type="success">Enabled</StatusIndicator> : <StatusIndicator type="stopped">Disabled</StatusIndicator>),
                    },
                    {
                        id: "gid",
                        header: "GID",
                        cell: (e) => e.gid,
                    },
                ]}
            />
        );
    }

    buildSplitPanelContent() {
        return (
            this.isSelected() && (
                <IdeaSplitPanel title={`Users in ${this.getSelected()?.name}`}>
                    <IdeaListView
                        ref={this.userListing}
                        variant={"embedded"}
                        stickyHeader={false}
                        onFetchRecords={() => {
                            if (this.getSelected() == null) {
                                return Promise.resolve({});
                            }
                            return AppContext.get()
                                .client()
                                .accounts()
                                .listUsersInGroup({
                                    group_names: [this.getSelected()!.name!],
                                });
                        }}
                        selectionType="multi"
                        onSelectionChange={(event) => {
                            this.setState({
                                userInGroupSelected: event.detail.selectedItems.length > 0,
                            });
                        }}
                        columnDefinitions={USER_TABLE_COLUMN_DEFINITIONS}
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
                        text: "RES",
                        href: "#/",
                    },
                    {
                        text: "Environment Management",
                        href: "#/cluster/status",
                    },
                    {
                        text: "Groups",
                        href: "",
                    },
                ]}
                content={
                    <div>
                        {this.buildEnableDisableGroupConfirmModal()}
                        {this.buildListView()}
                    </div>
                }
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

export default withRouter(Groups);
