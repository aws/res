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
import { IdeaAppLayoutProps } from "../../components/app-layout";
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import { Button, ColumnLayout, Container, Header, SpaceBetween } from "@cloudscape-design/components";
import IdeaAppLayout from "../../components/app-layout/app-layout";
import { KeyValue } from "../../components/key-value";
import { AppContext } from "../../common";
import { VirtualDesktopPermission, VirtualDesktopPermissionProfile } from "../../client/data-model";
import Tabs from "../../components/tabs/tabs";
import { EnabledDisabledStatusIndicator } from "../../components/common";
import VirtualDesktopPermissionProfileForm from "./forms/virtual-desktop-permission-profile-form";
import { VirtualDesktopAdminClient } from "../../client";
import { withRouter } from "../../navigation/navigation-utils";
import VirtualDesktopUtilsClient from "../../client/virtual-desktop-utils-client";

export interface VirtualDesktopPermissionProfileDetailProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {}

interface VirtualDesktopPermissionProfileDetailState {
    permissionProfile: VirtualDesktopPermissionProfile;
    settings: any;
    settingsLoaded: boolean;
    showEditPermissionProfileForm: boolean;
}

class VirtualDesktopPermissionProfileDetail extends Component<VirtualDesktopPermissionProfileDetailProps, VirtualDesktopPermissionProfileDetailState> {
    editPermissionProfileForm: RefObject<VirtualDesktopPermissionProfileForm>;

    constructor(props: VirtualDesktopPermissionProfileDetailProps) {
        super(props);
        this.editPermissionProfileForm = React.createRef();
        this.state = {
            permissionProfile: {},
            settings: {},
            settingsLoaded: false,
            showEditPermissionProfileForm: false,
        };
    }

    getProfileID(): string {
        return this.props.params.profile_id;
    }

    componentDidMount() {
        AppContext.get()
            .getClusterSettingsService()
            .getVirtualDesktopSettings()
            .then((settings) => {
                this.setState({
                    settings: settings,
                    settingsLoaded: true,
                });
            });

        this.getVirtualDesktopUtilsClient()
            .getPermissionProfile({
                profile_id: this.getProfileID(),
            })
            .then((result) => {
                this.setState({
                    permissionProfile: result.profile!,
                });
            });
    }

    buildPermissionProfile() {
        return (
            <Container header={<Header variant={"h2"}>Permission Details</Header>}>
                {
                    <ColumnLayout columns={3} variant={"text-grid"}>
                        {this.state.permissionProfile?.permissions?.map((permission: VirtualDesktopPermission, index: number) => {
                            return (
                                <KeyValue key={permission.key!} title={permission.name!}>
                                    <EnabledDisabledStatusIndicator enabled={permission.enabled!} />
                                </KeyValue>
                            );
                        })}
                        <KeyValue title="Created On" value={this.state.permissionProfile.created_on} type={"date"} />
                        <KeyValue title="Updated On" value={this.state.permissionProfile.updated_on} type={"date"} />
                    </ColumnLayout>
                }
            </Container>
        );
    }

    getVirtualDesktopUtilsClient(): VirtualDesktopUtilsClient {
        return AppContext.get().client().virtualDesktopUtils();
    }

    getVirtualDesktopAdminClient(): VirtualDesktopAdminClient {
        return AppContext.get().client().virtualDesktopAdmin();
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

    buildHeaderActions() {
        return (
            <Button variant={"primary"} onClick={() => this.showEditPermissionProfileForm()}>
                {" "}
                Edit{" "}
            </Button>
        );
    }

    buildDetails() {
        return (
            <SpaceBetween size={"l"}>
                <Container header={<Header variant={"h2"}>General Information</Header>}>
                    <ColumnLayout variant={"text-grid"} columns={3}>
                        <KeyValue title="Desktop Shared Setting ID" value={this.state.permissionProfile.profile_id} />
                        <KeyValue title="Title" value={this.state.permissionProfile.title} />
                        <KeyValue title="Description" value={this.state.permissionProfile.description} />
                    </ColumnLayout>
                </Container>
                <Tabs
                    tabs={[
                        {
                            label: "Permissions",
                            id: "permissions",
                            content: this.state.settingsLoaded && this.buildPermissionProfile(),
                        },
                    ]}
                />
            </SpaceBetween>
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

    buildEditForm() {
        return (
            <VirtualDesktopPermissionProfileForm
                ref={this.editPermissionProfileForm}
                profileToEdit={this.state.permissionProfile}
                onDismiss={() => {
                    this.hideEditPermissionProfileForm();
                }}
                onSubmit={(permissionProfile: VirtualDesktopPermissionProfile) => {
                    return this.getVirtualDesktopAdminClient()
                        .updatePermissionProfile({
                            profile: permissionProfile,
                        })
                        .then((response) => {
                            this.setFlashMessage(<p key={permissionProfile.profile_id}>Desktop Shared Setting: {permissionProfile.profile_id}, Edit request submitted</p>, "success");
                            this.setState({
                                permissionProfile: response.profile!,
                            });
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
                sideNavActivePath={"/virtual-desktop/permission-profiles"}
                onFlashbarChange={this.props.onFlashbarChange}
                flashbarItems={this.props.flashbarItems}
                breadcrumbItems={[
                    {
                        text: "RES",
                        href: "#/",
                    },
                    {
                        text: "Virtual Desktop",
                        href: "#/virtual-desktop/sessions",
                    },
                    {
                        text: "Desktop Shared Settings",
                        href: "#/virtual-desktop/permission-profiles",
                    },
                    {
                        text: this.getProfileID(),
                        href: "",
                    },
                ]}
                header={
                    <Header variant={"h1"} actions={this.buildHeaderActions()}>
                        Desktop Shared Setting: {this.state.permissionProfile.title}
                    </Header>
                }
                contentType={"default"}
                content={
                    <div>
                        {this.buildDetails()}
                        {this.state.showEditPermissionProfileForm && this.buildEditForm()}
                    </div>
                }
            />
        );
    }
}

export default withRouter(VirtualDesktopPermissionProfileDetail);
