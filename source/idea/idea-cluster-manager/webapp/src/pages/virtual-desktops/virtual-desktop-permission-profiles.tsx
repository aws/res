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
import { VirtualDesktopAdminClient } from "../../client";
import { AppContext } from "../../common";
import Utils from "../../common/utils";
import { TableProps } from "@cloudscape-design/components/table/interfaces";
import { VirtualDesktopPermission, VirtualDesktopPermissionProfile } from "../../client/data-model";
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import IdeaAppLayout, { IdeaAppLayoutProps } from "../../components/app-layout";
import { Link } from "@cloudscape-design/components";
import VirtualDesktopPermissionProfileForm from "./forms/virtual-desktop-permission-profile-form";
import { withRouter } from "../../navigation/navigation-utils";
import VirtualDesktopUtilsClient from "../../client/virtual-desktop-utils-client";

export interface VirtualDesktopPermissionProfilesProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {}

export interface VirtualDesktopPermissionProfilesState {
    permissionProfileSelected: boolean;
    showCreatePermissionProfileForm: boolean;
    showEditPermissionProfileForm: boolean;
    base_permissions: VirtualDesktopPermission[];
    settings: any;
}

const VIRTUAL_DESKTOP_PERMISSION_PROFILE_TABLE_COLUMN_DEFINITIONS: TableProps.ColumnDefinition<VirtualDesktopPermissionProfile>[] = [
    {
        id: "profile_id",
        header: "Desktop Shared Setting ID",
        cell: (e) => <Link href={`/#/virtual-desktop/permission-profiles/${e.profile_id}`}>{e.profile_id}</Link>,
    },
    {
        id: "title",
        header: "Title",
        cell: (e) => e.title,
    },
    {
        id: "description",
        header: "Description",
        cell: (e) => e.description,
    },
    {
        id: "created_on",
        header: "Created On",
        cell: (e) => new Date(e.created_on!).toLocaleString(),
    },
];

class VirtualDesktopPermissionProfiles extends Component<VirtualDesktopPermissionProfilesProps, VirtualDesktopPermissionProfilesState> {
    listing: RefObject<IdeaListView>;
    createPermissionProfileForm: RefObject<VirtualDesktopPermissionProfileForm>;
    editPermissionProfileForm: RefObject<VirtualDesktopPermissionProfileForm>;

    constructor(props: VirtualDesktopPermissionProfilesProps) {
        super(props);
        this.listing = React.createRef();
        this.createPermissionProfileForm = React.createRef();
        this.editPermissionProfileForm = React.createRef();
        this.state = {
            permissionProfileSelected: false,
            showCreatePermissionProfileForm: false,
            showEditPermissionProfileForm: false,
            base_permissions: [],
            settings: {},
        };
    }

    componentDidMount() {
        AppContext.get()
            .getClusterSettingsService()
            .getVirtualDesktopSettings()
            .then((settings) => {
                this.setState({
                    settings: settings,
                });
            });

        this.getVirtualDesktopUtilsClient()
            .getBasePermissions({})
            .then((response) => {
                this.setState({
                    base_permissions: response.permissions!,
                });
            });
    }

    getListing(): IdeaListView {
        return this.listing.current!;
    }

    getVirtualDesktopUtilsClient(): VirtualDesktopUtilsClient {
        return AppContext.get().client().virtualDesktopUtils();
    }

    getVirtualDesktopAdminClient(): VirtualDesktopAdminClient {
        return AppContext.get().client().virtualDesktopAdmin();
    }

    getCreatePermissionProfileForm(): VirtualDesktopPermissionProfileForm {
        return this.createPermissionProfileForm.current!;
    }

    hideCreatePermissionProfileForm() {
        this.setState({
            showCreatePermissionProfileForm: false,
        });
    }

    showCreatePermissionProfileForm() {
        this.setState(
            {
                showCreatePermissionProfileForm: true,
            },
            () => {
                this.getCreatePermissionProfileForm().showModal();
            }
        );
    }

    buildCreatePermissionProfileForm() {
        return (
            <VirtualDesktopPermissionProfileForm
                ref={this.createPermissionProfileForm}
                onDismiss={() => {
                    this.hideCreatePermissionProfileForm();
                }}
                onSubmit={(permissionProfile: VirtualDesktopPermissionProfile) => {
                    return this.getVirtualDesktopAdminClient()
                        .createPermissionProfile({
                            profile: permissionProfile,
                        })
                        .then((_) => {
                            this.setFlashMessage(<p key={permissionProfile.profile_id}>Desktop Shared Setting: {permissionProfile.profile_id}, Create request submitted</p>, "success");
                            this.getListing().fetchRecords();
                            return Promise.resolve(true);
                        })
                        .catch((error) => {
                            this.getCreatePermissionProfileForm().setError(error.errorCode, error.message);
                            return Promise.resolve(false);
                        });
                }}
                editMode={false}
            />
        );
    }

    setFlashMessage = (content: React.ReactNode, type: "success" | "info" | "error") => {
        this.props.onFlashbarChange({
            items: [
                {
                    content: content,
                    dismissible: true,
                    type: type,
                },
            ],
        });
    };

    isSelected(): boolean {
        return this.state.permissionProfileSelected;
    }

    getSelectedPermissionProfile(): VirtualDesktopPermissionProfile | undefined {
        if (this.getListing() == null) {
            return undefined;
        }
        return this.getListing().getSelectedItems()[0];
    }

    buildEditPermissionProfileForm() {
        return (
            <VirtualDesktopPermissionProfileForm
                ref={this.editPermissionProfileForm}
                profileToEdit={this.getSelectedPermissionProfile()}
                onDismiss={() => {
                    this.hideEditPermissionProfileForm();
                }}
                onSubmit={(permissionProfile: VirtualDesktopPermissionProfile) => {
                    return this.getVirtualDesktopAdminClient()
                        .updatePermissionProfile({
                            profile: permissionProfile,
                        })
                        .then((_) => {
                            this.setFlashMessage(<p key={permissionProfile.profile_id}>Desktop Shared Setting: {permissionProfile.profile_id}, Edit request submitted</p>, "success");
                            this.getListing().fetchRecords();
                            return Promise.resolve(true);
                        })
                        .catch((error) => {
                            this.getEditPermissionProfileForm().setError(error.errorCode, error.message);
                            return Promise.resolve(false);
                        });
                }}
                editMode={true}
            />
        );
    }

    hideEditPermissionProfileForm() {
        this.setState({
            showEditPermissionProfileForm: false,
        });
    }

    showEditPermissionProfileForm() {
        this.setState(
            {
                showEditPermissionProfileForm: true,
            },
            () => {
                this.getEditPermissionProfileForm().showModal();
            }
        );
    }

    getEditPermissionProfileForm(): VirtualDesktopPermissionProfileForm {
        return this.editPermissionProfileForm.current!;
    }

    buildListing() {
        return (
            <IdeaListView
                ref={this.listing}
                title="Desktop Shared Settings"
                preferencesKey={"permission-profile"}
                showPreferences={true}
                description="Manage your Virtual Desktop Shared Settings"
                selectionType="single"
                primaryAction={{
                    id: "create-permission-profile",
                    text: "Create Desktop Shared Setting",
                    onClick: () => {
                        this.showCreatePermissionProfileForm();
                    },
                }}
                secondaryActionsDisabled={!this.isSelected()}
                secondaryActions={[
                    {
                        id: "edit-permission-profile",
                        text: "Edit Desktop Shared Setting",
                        disabled: !this.isSelected(),
                        onClick: () => {
                            this.setState(
                                {
                                    showEditPermissionProfileForm: true,
                                },
                                () => {
                                    this.showEditPermissionProfileForm();
                                }
                            );
                        },
                    },
                ]}
                showPaginator={true}
                showFilters={true}
                filters={[
                    {
                        key: "profile_id",
                    },
                ]}
                onFilter={(filters) => {
                    const token = `${filters[0].value ?? ""}`.trim().toLowerCase();
                    if (token.trim().length === 0) {
                        return [];
                    } else {
                        return [
                            {
                                key: "profile_id",
                                like: token,
                            },
                        ];
                    }
                }}
                onRefresh={() => {
                    this.setState(
                        {
                            permissionProfileSelected: false,
                        },
                        () => {
                            this.getListing().fetchRecords();
                        }
                    );
                }}
                onSelectionChange={() => {
                    this.setState({
                        permissionProfileSelected: true,
                    });
                }}
                onFetchRecords={() => {
                    return this.getVirtualDesktopUtilsClient()
                        .listPermissionProfiles({ filters: this.getListing().getFilters(), paginator: this.getListing().getPaginator() })
                        .then((data) => {
                            return {
                                ...data,
                                listing: data.listing!.filter((profile) => profile.profile_id != "admin_profile"),
                            };
                        })
                        .catch((error) => {
                            this.props.onFlashbarChange({
                                items: [
                                    {
                                        content: error.message,
                                        type: "error",
                                        dismissible: true,
                                    },
                                ],
                            });
                            throw error;
                        });
                }}
                columnDefinitions={VIRTUAL_DESKTOP_PERMISSION_PROFILE_TABLE_COLUMN_DEFINITIONS}
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
                        text: "Virtual Desktops",
                        href: "#/virtual-desktop/sessions",
                    },
                    {
                        text: "Desktop Shared Settings",
                        href: "",
                    },
                ]}
                content={
                    <div>
                        {this.state.showCreatePermissionProfileForm && this.buildCreatePermissionProfileForm()}
                        {this.state.showEditPermissionProfileForm && this.buildEditPermissionProfileForm()}
                        {this.buildListing()}
                    </div>
                }
            />
        );
    }
}

export default withRouter(VirtualDesktopPermissionProfiles);
