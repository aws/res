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
import { Box, Button, ColumnLayout, Container, ExpandableSection, FormField, Header, SpaceBetween, StatusIndicator, StatusIndicatorProps } from "@cloudscape-design/components";
import IdeaAppLayout from "../../components/app-layout/app-layout";
import { AppContext } from "../../common";
import { VirtualDesktopPermission, VirtualDesktopPermissionProfile } from "../../client/data-model";
import { CopyToClipBoard } from "../../components/common";
import ConfigureDesktopSharingProfile from "./configure-desktop-sharing-profile";
import { VirtualDesktopAdminClient } from "../../client";
import { withRouter } from "../../navigation/navigation-utils";
import VirtualDesktopUtilsClient from "../../client/virtual-desktop-utils-client";
import Utils from "../../common/utils";
import { Constants } from "../../common/constants";

export interface VirtualDesktopPermissionProfileDetailProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {}

interface VirtualDesktopPermissionProfileDetailState {
    permissionProfile: VirtualDesktopPermissionProfile;
    ownerPermissions: Map<string, boolean>;
    ownerProfileLoaded: boolean;
}

class VirtualDesktopPermissionProfileDetail extends Component<VirtualDesktopPermissionProfileDetailProps, VirtualDesktopPermissionProfileDetailState> {

    constructor(props: VirtualDesktopPermissionProfileDetailProps) {
        super(props);
        this.state = {
            permissionProfile: {},
            ownerPermissions: new Map(),
            ownerProfileLoaded: false,
        };
    }

    getProfileID(): string {
        return this.props.params.profile_id;
    }

    componentDidMount() {
        this.getVirtualDesktopUtilsClient()
            .getPermissionProfile({ profile_id: Constants.DCV_SETTINGS_DEFAULT_OWNER_PROFILE_ID })
            .then((profile) => {
                const permissions = new Map<string, boolean>();
                for (const p of profile.profile!.permissions!) {
                    permissions.set(p.key!, p.enabled!);
                }
                this.setState({
                    ownerPermissions: permissions,
                    ownerProfileLoaded: true,
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

    isSettingAllowedGlobally(permissionKey: string): boolean {
        if (!this.state.ownerProfileLoaded) {
            return false;
        }

        return this.state.ownerPermissions.get(permissionKey) ?? false;
    }

    getSettingStatus(allowedGlobally: boolean, enabledLocally: boolean): string {
        if (!allowedGlobally) {
            return "Disabled globally";
        }

        return enabledLocally ? "Enabled" : "Disabled";
    }

    getSettingStatusType(allowedGlobally: boolean, enabledLocally: boolean): StatusIndicatorProps.Type {
        if (!allowedGlobally) {
            return "warning";
        }

        return enabledLocally ? "success" : "stopped";
    }

    getPermissionComponent(setting: VirtualDesktopPermission) {
        const allowed: boolean = this.isSettingAllowedGlobally(setting.key!);
        const enabled: boolean = setting.enabled! && allowed;
        return <FormField
            label={setting.name!}
            description={setting.description ?? "-"}
        >
            <StatusIndicator
                type={this.getSettingStatusType(allowed, enabled)}
                colorOverride={!allowed ? "blue" : undefined}
            >
                {this.getSettingStatus(allowed, enabled)}
            </StatusIndicator>
        </FormField>
    }

    getPermissionColumn(profile: VirtualDesktopPermissionProfile, filterArray: string[]) {
        return <SpaceBetween size="l" direction="vertical">
            {profile?.permissions?.filter((p) => filterArray.includes(p.key!))?.map((setting) => this.getPermissionComponent(setting))}
        </SpaceBetween>
    }

    buildPermissionProfile() {
        const basicSettings = this.state.permissionProfile.permissions?.filter((p) => Constants.DCV_SETTINGS_DESKTOP_SETTINGS.getAllColumns().includes(p.key!));
        const advancedSettings = this.state.permissionProfile.permissions?.filter((p) => Constants.DCV_SETTINGS_DESKTOP_ADVANCED_SETTINGS.getAllColumns().includes(p.key!));
        const totalEnabled = (basicSettings?.filter(p => p.enabled)?.length ?? 0) + (advancedSettings?.filter(p => p.enabled)?.length ?? 0);
        return (
            <Container
                header={
                    <Header
                        variant="h2"
                        counter={`(${totalEnabled})`}
                        description={<Box>
                            Permissions granted to this sharing profile.
                            To enable the permissions that are 'Disabled globally', go back to the Environment boundaries and enable them there.
                        </Box>}
                    >
                        Permissions
                    </Header>
                }
            >
                <SpaceBetween size="l">
                    <ExpandableSection
                        defaultExpanded
                        headerText={`Desktop sharing permissions (enabled ${basicSettings?.filter(p => p.enabled)?.length ?? 0}/${Constants.DCV_SETTINGS_DESKTOP_SETTINGS.getAllColumns().length})`}
                    >
                        <br />
                        <ColumnLayout columns={3} borders="vertical">
                            {this.getPermissionColumn(this.state.permissionProfile, Constants.DCV_SETTINGS_DESKTOP_SETTINGS.column_one)}
                            {this.getPermissionColumn(this.state.permissionProfile, Constants.DCV_SETTINGS_DESKTOP_SETTINGS.column_two)}
                            {this.getPermissionColumn(this.state.permissionProfile, Constants.DCV_SETTINGS_DESKTOP_SETTINGS.column_three)}
                        </ColumnLayout>
                    </ExpandableSection>
                    <ExpandableSection
                        headerText={`Desktop sharing advanced permissions (enabled ${advancedSettings?.filter(p => p.enabled)?.length ?? 0}/${Constants.DCV_SETTINGS_DESKTOP_ADVANCED_SETTINGS.getAllColumns().length})`}
                    >
                        <br />
                        <ColumnLayout columns={3} borders="vertical">
                            {this.getPermissionColumn(this.state.permissionProfile, Constants.DCV_SETTINGS_DESKTOP_ADVANCED_SETTINGS.column_one)}
                            {this.getPermissionColumn(this.state.permissionProfile, Constants.DCV_SETTINGS_DESKTOP_ADVANCED_SETTINGS.column_two)}
                            {this.getPermissionColumn(this.state.permissionProfile, Constants.DCV_SETTINGS_DESKTOP_ADVANCED_SETTINGS.column_three)}
                        </ColumnLayout>
                    </ExpandableSection>
                </SpaceBetween>
            </Container>
        );
    }

    getVirtualDesktopUtilsClient(): VirtualDesktopUtilsClient {
        return AppContext.get().client().virtualDesktopUtils();
    }

    getVirtualDesktopAdminClient(): VirtualDesktopAdminClient {
        return AppContext.get().client().virtualDesktopAdmin();
    }

    buildHeaderActions() {
        return (
            <Button variant={"primary"} onClick={() => {
                this.props.navigate("/cluster/permissions/sharing-profiles/configure", {
                    state: {
                        isUpdate: true,
                        profileToEdit: this.state.permissionProfile,
                        from_page: "detail"
                    }
                })
            }}>
                {" "}
                Edit{" "}
            </Button>
        );
    }

    buildDetails() {
        return (
            <SpaceBetween size={"l"}>
                <Container header={<Header variant={"h2"}>Profile overview</Header>}>
                    <ColumnLayout variant={"text-grid"} columns={3}>
                        <FormField label="Profile ID">
                            <CopyToClipBoard
                                text={this.state.permissionProfile.profile_id!}
                                feedback="ID copied"
                            /> {this.state.permissionProfile.profile_id}
                        </FormField>
                        <FormField label="Description">{this.state.permissionProfile.description ?? "-"}</FormField>
                        <SpaceBetween size="l">
                            <FormField label="Creation date">
                                {this.state.permissionProfile.created_on ? Utils.convertToRelativeTime(Date.parse(this.state.permissionProfile.created_on!)) : "-"}
                            </FormField>
                            <FormField label="Last updated">
                                {this.state.permissionProfile.updated_on ? Utils.convertToRelativeTime(Date.parse(this.state.permissionProfile.updated_on!)) : "-"}
                            </FormField>
                        </SpaceBetween>
                    </ColumnLayout>
                </Container>
                {this.state.ownerProfileLoaded && this.buildPermissionProfile()}
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
                sideNavActivePath={"/cluster/permissions"}
                onFlashbarChange={this.props.onFlashbarChange}
                flashbarItems={this.props.flashbarItems}
                breadcrumbItems={[
                    {
                        text: "RES",
                        href: "#/",
                    },
                    {
                        text: "Permission policy: Desktop sharing profiles",
                        href: "#/cluster/permissions",
                    },
                    {
                        text: this.getProfileID(),
                        href: "",
                    },
                ]}
                header={
                    <Header variant={"h1"} actions={this.buildHeaderActions()}>
                        {this.state.permissionProfile.title}
                    </Header>
                }
                contentType={"default"}
                content={
                    <div>
                        {this.buildDetails()}
                    </div>
                }
            />
        );
    }
}

export default withRouter(VirtualDesktopPermissionProfileDetail);
