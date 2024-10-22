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
import { TableProps } from "@cloudscape-design/components/table/interfaces";
import { VirtualDesktopPermission, VirtualDesktopPermissionProfile } from "../../client/data-model";
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import { IdeaAppLayoutProps } from "../../components/app-layout";
import { Link } from "@cloudscape-design/components";
import { withRouter } from "../../navigation/navigation-utils";
import VirtualDesktopUtilsClient from "../../client/virtual-desktop-utils-client";
import { Constants } from "../../common/constants";

export interface VirtualDesktopPermissionProfilesProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {}

export interface VirtualDesktopPermissionProfilesState {
    permissionProfileSelected: boolean;
    base_permissions: VirtualDesktopPermission[];
    settings: any;
}

const VIRTUAL_DESKTOP_PERMISSION_PROFILE_TABLE_COLUMN_DEFINITIONS: TableProps.ColumnDefinition<VirtualDesktopPermissionProfile>[] = [
    {
        id: "profile_id",
        header: "Desktop sharing profile ID",
        cell: (e) => <Link href={`/#/cluster/permissions/sharing-profiles/${e.profile_id}`}>{e.profile_id}</Link>,
    },
    {
        id: "title",
        header: "Title",
        cell: (e) => e.title,
    },
    {
        id: "description",
        header: "Description",
        cell: (e) => e.description ?? "-",
    },
    {
        id: "created_on",
        header: "Created On",
        cell: (e) => new Date(e.created_on!).toLocaleString(),
    },
];

class VirtualDesktopPermissionProfiles extends Component<VirtualDesktopPermissionProfilesProps, VirtualDesktopPermissionProfilesState> {
    listing: RefObject<IdeaListView>;

    constructor(props: VirtualDesktopPermissionProfilesProps) {
        super(props);
        this.listing = React.createRef();
        this.state = {
            permissionProfileSelected: false,
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

    buildListing() {
        return (
            <IdeaListView
                ref={this.listing}
                title="Desktop sharing profiles"
                preferencesKey={"permission-profile"}
                showPreferences={true}
                variant="container"
                description="Manage your desktop sharing profiles."
                selectionType="single"
                primaryAction={{
                    id: "create-permission-profile",
                    text: "Create profile",
                    onClick: () => {
                        this.props.navigate("/cluster/permissions/sharing-profiles/configure", {
                            state: {
                                isUpdate: false,
                                from_page: "dashboard"
                            }
                        });
                    },
                }}
                secondaryActionsDisabled={!this.isSelected()}
                secondaryActions={[
                    {
                        id: "edit-permission-profile",
                        text: "Edit",
                        disabled: !this.isSelected(),
                        onClick: () => {
                            this.props.navigate("/cluster/permissions/sharing-profiles/configure", {
                                state: {
                                    isUpdate: true,
                                    profileToEdit: this.getSelectedPermissionProfile(),
                                    from_page: "dashboard"
                                }
                            })
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
                                listing: data.listing!.filter((profile) => profile.profile_id !== Constants.DCV_SETTINGS_DEFAULT_OWNER_PROFILE_ID),
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
            <div>
                {this.buildListing()}
            </div>
        );
    }
}

export default withRouter(VirtualDesktopPermissionProfiles);
