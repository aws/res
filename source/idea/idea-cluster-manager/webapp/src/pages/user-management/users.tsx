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
import IdeaListView from "../../components/list-view";
import { TableProps } from "@cloudscape-design/components/table/interfaces";
import { User } from "../../client/data-model";
import { AccountsClient } from "../../client";
import Utils from "../../common/utils";
import IdeaConfirm from "../../components/modals";
import { StatusIndicator } from "@cloudscape-design/components";
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import IdeaAppLayout, { IdeaAppLayoutProps } from "../../components/app-layout";
import { withRouter } from "../../navigation/navigation-utils";

export interface UsersProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {}

export interface UsersState {
    userSelected: boolean;
}

const RES_SPECIFIC_NON_PROJECT_GROUPS = ["cluster-manager-administrators-module-group", "cluster-manager-users-module-group", "managers-cluster-group", "scheduler-administrators-module-group", "scheduler-users-module-group", "vdc-administrators-module-group", "vdc-users-module-group"];

export const USER_TABLE_COLUMN_DEFINITIONS: TableProps.ColumnDefinition<User>[] = [
    {
        id: "username",
        header: "Username",
        cell: (e) => e.username,
    },
    {
        id: "uid",
        header: "UID",
        cell: (e) => e.uid,
    },
    {
        id: "gid",
        header: "GID",
        cell: (e) => e.gid,
    },
    {
        id: "email",
        header: "Email",
        cell: (e) => e.email,
    },
    {
        id: "sudo",
        header: "Is Sudo?",
        cell: (e) => (e.sudo ? "Yes" : "No"),
    },
    {
        id: "user_role",
        header: "Role",
        cell: (e) => e.role,
    },
    {
        id: "is_active",
        header: "Is Active",
        cell: (e) => (e.is_active ? "Yes" : "No"),
    },
    {
        id: "enabled",
        header: "Status",
        cell: (e) => (e.enabled ? <StatusIndicator type="success">Enabled</StatusIndicator> : <StatusIndicator type="stopped">Disabled</StatusIndicator>),
    },
    {
        id: "groups",
        header: "Groups",
        cell: (user) => {
            if (user.additional_groups) {
                return (
                    <div>
                        {user.additional_groups.map((group, index) => {
                            if (!RES_SPECIFIC_NON_PROJECT_GROUPS.includes(group) && group != `${user.username}-user-group`) {
                                return <li key={index}>{group}</li>;
                            }
                        })}
                    </div>
                );
            } else {
                return "-";
            }
        },
    },
    {
        id: "synced_on",
        header: "Synced On",
        cell: (e) => new Date(e.synced_on!).toLocaleString(),
    },
];

class Users extends Component<UsersProps, UsersState> {
    toggleAdminUserConfirmModal: RefObject<IdeaConfirm>;
    toggleUserEnabledConfirmModal: RefObject<IdeaConfirm>;
    listing: RefObject<IdeaListView>;

    constructor(props: UsersProps) {
        super(props);
        this.toggleAdminUserConfirmModal = React.createRef();
        this.toggleUserEnabledConfirmModal = React.createRef();
        this.listing = React.createRef();
        this.state = {
            userSelected: false,
        };
    }

    authAdmin(): AccountsClient {
        return AppContext.get().client().accounts();
    }

    getToggleAdminUserConfirmModal(): IdeaConfirm {
        return this.toggleAdminUserConfirmModal.current!;
    }

    getToggleUserEnabledConfirmModal(): IdeaConfirm {
        return this.toggleUserEnabledConfirmModal.current!;
    }

    getListing(): IdeaListView {
        return this.listing.current!;
    }

    buildToggleAdminUserConfirmModal() {
        let message;
        if (this.isSelectedUserAdmin()) {
            message = "Are you sure you want to revoke admin rights from: ";
        } else {
            message = "Are you sure you want to grant admin rights to: ";
        }
        return (
            <IdeaConfirm
                ref={this.toggleAdminUserConfirmModal}
                title={this.isSelectedUserAdmin() ? "Revoke Admin Rights" : "Grant Admin Rights"}
                onConfirm={() => {
                    const username = this.getSelectedUser()?.username;
                    if (this.isSelectedUserAdmin()) {
                        this.authAdmin()
                            .removeAdminUser({
                                username: username,
                            })
                            .then((_) => {
                                this.getListing().fetchRecords();
                                this.setFlashMessage(`Admin rights were revoked from User: ${username}.`, "success");
                            })
                            .catch((error) => {
                                this.setFlashMessage(`Failed to revoke admin rights: ${error.message}`, "error");
                            });
                    } else {
                        this.authAdmin()
                            .addAdminUser({
                                username: username,
                            })
                            .then((_) => {
                                this.getListing().fetchRecords();
                                this.setFlashMessage(`User: ${username} was successfully granted admin rights.`, "success");
                            })
                            .catch((error) => {
                                this.setFlashMessage(`Failed to grant admin rights: ${error.message}`, "error");
                            });
                    }
                }}
            >
                {message} <b>{this.getSelectedUser()?.username}</b> ?
            </IdeaConfirm>
        );
    }

    buildToggleUserEnabledConfirmModal() {
        let message;
        if (this.isSelectedUserEnabled()) {
            message = "Are you sure you want to disable user: ";
        } else {
            message = "Are you sure you want to enable user: ";
        }
        return (
            <IdeaConfirm
                ref={this.toggleUserEnabledConfirmModal}
                title={this.isSelectedUserEnabled() ? "Disable User" : "Enable User"}
                onConfirm={() => {
                    const username = this.getSelectedUser()?.username;
                    if (this.isSelectedUserEnabled()) {
                        this.authAdmin()
                            .disableUser({
                                username: username,
                            })
                            .then((_) => {
                                this.getListing().fetchRecords();
                                this.setFlashMessage(`User: ${username} disabled successfully.`, "success");
                            })
                            .catch((error) => {
                                this.setFlashMessage(`Failed to disable user: ${error.message}`, "error");
                            });
                    } else {
                        this.authAdmin()
                            .enableUser({
                                username: username,
                            })
                            .then((_) => {
                                this.getListing().fetchRecords();
                                this.setFlashMessage(`User: ${username} enabled successfully.`, "success");
                            })
                            .catch((error) => {
                                this.setFlashMessage(`Failed to enable user: ${error.message}`, "error");
                            });
                    }
                }}
            >
                {message} <b>{this.getSelectedUser()?.username}</b> ?
            </IdeaConfirm>
        );
    }

    setFlashMessage(message: string, type: "success" | "info" | "error") {
        this.props.onFlashbarChange({
            items: [
                {
                    content: message,
                    type: type,
                    dismissible: true,
                },
            ],
        });
    }

    isSelected(): boolean {
        return this.state.userSelected;
    }

    getSelectedUser(): User | null {
        if (this.getListing() == null) {
            return null;
        }
        return this.getListing().getSelectedItem<User>();
    }

    isSelectedUserAdmin(): boolean {
        if (!this.isSelected()) {
            return false;
        }
        const selectedUser = this.getSelectedUser();
        if (selectedUser == null) {
            return false;
        }
        return Utils.asString(selectedUser.role) == 'admin';
    }

    isSelectedUserEnabled(): boolean {
        if (!this.isSelected()) {
            return false;
        }
        const selectedUser = this.getSelectedUser();
        if (selectedUser == null) {
            return false;
        }
        return selectedUser.enabled!;
    }

    buildListing() {
        return (
            <IdeaListView
                ref={this.listing}
                preferencesKey={"users"}
                showPreferences={false}
                title="Users"
                description="Environment user management"
                selectionType="single"
                secondaryActionsDisabled={!this.isSelected()}
                secondaryActions={[
                    {
                        id: "toggle-admin-user",
                        text: this.isSelectedUserAdmin() ? "Remove as Admin User" : "Set as Admin User",
                        onClick: () => {
                            this.getToggleAdminUserConfirmModal().show();
                        },
                    },
                    {
                        id: "toggle-user-enabled",
                        text: this.isSelectedUserEnabled() ? "Disable User" : "Enable User",
                        onClick: () => {
                            this.getToggleUserEnabledConfirmModal().show();
                        },
                    },
                ]}
                showPaginator={true}
                showFilters={true}
                filters={[
                    {
                        key: "username",
                    },
                ]}
                onFilter={(filters) => {
                    const usernameToken = Utils.asString(filters[0].value).trim().toLowerCase();
                    if (Utils.isEmpty(usernameToken)) {
                        return [];
                    } else {
                        return [
                            {
                                key: "username",
                                like: usernameToken,
                            },
                        ];
                    }
                }}
                onRefresh={() => {
                    this.setState(
                        {
                            userSelected: false,
                        },
                        () => {
                            this.getListing().fetchRecords();
                        }
                    );
                }}
                onSelectionChange={() => {
                    this.setState({
                        userSelected: true,
                    });
                }}
                onFetchRecords={() => {
                    return this.authAdmin().listUsers({
                        filters: this.getListing().getFilters(),
                        paginator: this.getListing().getPaginator(),
                    });
                }}
                columnDefinitions={USER_TABLE_COLUMN_DEFINITIONS}
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
                        text: "RES",
                        href: "#/",
                    },
                    {
                        text: "Environment Management",
                        href: "#/cluster/status",
                    },
                    {
                        text: "Users",
                        href: "",
                    },
                ]}
                content={
                    <div>
                        {this.buildToggleAdminUserConfirmModal()}
                        {this.buildToggleUserEnabledConfirmModal()}
                        {this.buildListing()}
                    </div>
                }
            />
        );
    }
}

export default withRouter(Users);
