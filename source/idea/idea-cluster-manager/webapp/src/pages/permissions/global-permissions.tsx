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
import { VirtualDesktopPermission, VirtualDesktopPermissionProfile } from "../../client/data-model";
import { Constants } from "../../common/constants";
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import { IdeaAppLayoutProps } from "../../components/app-layout";
import { withRouter } from "../../navigation/navigation-utils";
import ClusterSettingsClient from "../../client/cluster-settings-client";
import dot from "dot-object";
import { ColumnLayout, Container, ExpandableSection, FlashbarProps, FormField, Header, SpaceBetween, Toggle } from "@cloudscape-design/components";
import { VirtualDesktopAdminClient } from "../../client";
import VirtualDesktopUtilsClient from "../../client/virtual-desktop-utils-client";


export interface GlobalPermissionsProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {}

export interface GlobalPermissionsState {
    globalPermissionsStatus: Map<string, boolean>;
    fileBrowserSectionExpanded: boolean;
    desktopPermissionsSectionExpanded: boolean;
    desktopAdvancedSectionExpanded: boolean;
    ownerSettings: VirtualDesktopPermissionProfile | undefined;
}

class GlobalPermissions extends Component<GlobalPermissionsProps, GlobalPermissionsState> {
    listing: RefObject<IdeaListView>;

    constructor(props: GlobalPermissionsProps) {
        super(props);
        this.listing = React.createRef();
        this.state = {
            globalPermissionsStatus: new Map<string, boolean>(),
            fileBrowserSectionExpanded: true,
            desktopPermissionsSectionExpanded: false,
            desktopAdvancedSectionExpanded: false,
            ownerSettings: undefined,
        };
    }

    componentDidMount(): void {
        this.getGlobalPermissions();
    }

    clusterSettingsClient(): ClusterSettingsClient {
        return AppContext.get().client().clusterSettings();
    }

    virtualDesktopAdminClient(): VirtualDesktopAdminClient {
        return AppContext.get().client().virtualDesktopAdmin();
    }

    virtualDesktopUtilsClient(): VirtualDesktopUtilsClient {
        return AppContext.get().client().virtualDesktopUtils();
    }

    getListing(): IdeaListView {
        return this.listing.current!;
    }

    setFlashbarMessage(type: FlashbarProps.Type, content: string, header?: React.ReactNode, action?: React.ReactNode) {
        this.props.onFlashbarChange({
          items: [
            {
              type,
              header,
              content,
              action,
              dismissible: true,
            }
          ]
        })
    }

    onChangeFileBrowser = (value: boolean) => {
        this.clusterSettingsClient().updateModuleSettings({
            module_id: Constants.MODULE_SHARED_STORAGE,
            settings:{
                enable_file_browser: value,
            }
        }).then(() => {
            this.setFlashbarMessage("success", `The file browser has been ${value ? "enabled" : "disabled"}.`);
            this.setState({ 
                globalPermissionsStatus: new Map(this.state.globalPermissionsStatus).set(Constants.SHARED_STORAGE_FILE_BROWSER_FEATURE_TITLE, value)
            });
            window.location.reload();
        }).catch((e) => {
            this.setFlashbarMessage("error", `Failed to ${value ? "enable" : "disable"} the file browser.`);
        });
    }

    onChangeOwnerSetting(key: string, value: boolean) {
        const profileToUpdate = this.state.ownerSettings!;
        const permissions = profileToUpdate.permissions!;
        for (const permission of permissions) {
            if (permission.key === key) {
                permission.enabled = value;
                break;
            }
        }
        profileToUpdate.permissions = permissions;
        this.virtualDesktopAdminClient().updatePermissionProfile({
            profile: profileToUpdate,
        }).then(() => {
            this.setFlashbarMessage("success", `The ${key} permission has been ${value ? "enabled" : "disabled"}.`);
            this.setState({
                ownerSettings: profileToUpdate,
                globalPermissionsStatus: new Map(this.state.globalPermissionsStatus).set(key, value)
            });
        }).catch((e) => {
            this.setFlashbarMessage("error", `Failed to ${value ? "enable" : "disable"} the ${key} permission.`);
        });
    }

    async getGlobalPermissions(): Promise<void> {
        const newGlobalPermissionsStatus = new Map<string, boolean>();
        const sharedStorageModuleSettings = await this.clusterSettingsClient().getModuleSettings({ module_id: Constants.MODULE_SHARED_STORAGE });
        newGlobalPermissionsStatus.set(Constants.SHARED_STORAGE_FILE_BROWSER_FEATURE_TITLE, dot.pick(Constants.SHARED_STORAGE_FILE_BROWSER_KEY, sharedStorageModuleSettings.settings))
        
        const ownerSettings = (await this.virtualDesktopUtilsClient().getPermissionProfile({
            profile_id: Constants.DCV_SETTINGS_DEFAULT_OWNER_PROFILE_ID,
        })).profile!;

        for (const permission of ownerSettings.permissions!) {
            if (permission.key === "builtin") {
                permission.enabled = false;
                continue;
            }
            newGlobalPermissionsStatus.set(permission.key!, permission.enabled!);
        }
        
        this.setState({ globalPermissionsStatus: newGlobalPermissionsStatus, ownerSettings });
    }

    getPermissionComponent(setting: VirtualDesktopPermission) {
        return <Toggle
            checked={this.state.globalPermissionsStatus.get(setting.key!) ?? false}
            onChange={(changeEvent) => this.onChangeOwnerSetting(setting.key!, changeEvent.detail.checked)}
        >
            <FormField
                label={setting.name!}
                description={setting.description!}
            ></FormField>
        </Toggle>;
    }

    getPermissionColumn(ownerProfile: VirtualDesktopPermissionProfile | undefined, filterArray: string[]) {
        return <SpaceBetween size="l" direction="vertical">
            {ownerProfile?.permissions?.filter((p) => filterArray.includes(p.key!))?.map((setting) => this.getPermissionComponent(setting))}
        </SpaceBetween>
    }

    buildListing() {
        const isFileBrowserEnabled = this.state.globalPermissionsStatus.get(Constants.SHARED_STORAGE_FILE_BROWSER_FEATURE_TITLE) ?? false;
        const ownerProfile = this.state.ownerSettings;
        const basicSettings = ownerProfile?.permissions?.filter((p) => Constants.DCV_SETTINGS_DESKTOP_SETTINGS.getAllColumns().includes(p.key!));
        const advancedSettings = ownerProfile?.permissions?.filter((p) => Constants.DCV_SETTINGS_DESKTOP_ADVANCED_SETTINGS.getAllColumns().includes(p.key!));
        return (
            <SpaceBetween size="l">
                <ExpandableSection
                    headerText={`File browser permissions (enabled ${isFileBrowserEnabled ? 1 : 0}/1)`}
                    expanded={this.state.fileBrowserSectionExpanded}
                >
                    <SpaceBetween size="m" direction="horizontal">
                        <Toggle
                            checked={isFileBrowserEnabled}
                            onChange={(changeEvent) => this.onChangeFileBrowser(changeEvent.detail.checked)}
                        ></Toggle>
                        <FormField
                            label="Access data"
                            description="Display File browser in the navigation menu and access data via web portal."
                        ></FormField>
                    </SpaceBetween>
                </ExpandableSection>
                <ExpandableSection
                    headerText={`Desktop permissions (enabled ${basicSettings?.filter(p => p.enabled)?.length ?? 0}/${Constants.DCV_SETTINGS_DESKTOP_SETTINGS.getAllColumns().length})`}
                >
                    <br />
                    <ColumnLayout columns={3} borders="vertical">
                        {this.getPermissionColumn(ownerProfile, Constants.DCV_SETTINGS_DESKTOP_SETTINGS.column_one.filter(x => x !== "unsupervised_access"))}
                        {this.getPermissionColumn(ownerProfile, Constants.DCV_SETTINGS_DESKTOP_SETTINGS.column_two)}
                        {this.getPermissionColumn(ownerProfile, Constants.DCV_SETTINGS_DESKTOP_SETTINGS.column_three)}
                    </ColumnLayout>
                </ExpandableSection>
                <ExpandableSection
                    headerText={`Desktop advanced settings (enabled ${advancedSettings?.filter(p => p.enabled)?.length ?? 0}/${Constants.DCV_SETTINGS_DESKTOP_ADVANCED_SETTINGS.getAllColumns().length})`}
                >
                    <br />
                    <ColumnLayout columns={3} borders="vertical">
                        {this.getPermissionColumn(ownerProfile, Constants.DCV_SETTINGS_DESKTOP_ADVANCED_SETTINGS.column_one)}
                        {this.getPermissionColumn(ownerProfile, Constants.DCV_SETTINGS_DESKTOP_ADVANCED_SETTINGS.column_two)}
                        {this.getPermissionColumn(ownerProfile, Constants.DCV_SETTINGS_DESKTOP_ADVANCED_SETTINGS.column_three)}
                    </ColumnLayout>
                </ExpandableSection>
            </SpaceBetween>
        );
    }

    render() {
        return (
            <Container
                header={<Header
                    variant="h2"
                    description="Define the environment boundaries to set the maximum permissions applicable to users. Then create and manage project roles and desktop sharing profiles. Enabled permissions in the environment boundaries can be modified in roles and profiles listed below, while disabling permissions overwrites their status and automatically turns them to 'Disabled globally'."
                >Environment boundaries</Header>}
            >
                {this.buildListing()}
            </Container>
        );
    }
}

export default withRouter(GlobalPermissions);
