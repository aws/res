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
import { Alert, Button, ColumnLayout, Container, ExpandableSection, FlashbarProps, FormField, Header, Link, SpaceBetween, Toggle, Spinner } from "@cloudscape-design/components";
import { VirtualDesktopAdminClient } from "../../client";
import VirtualDesktopUtilsClient from "../../client/virtual-desktop-utils-client";
import BackendClient from "../../client/backend-client";


export interface GlobalPermissionsProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {}

export interface GlobalPermissionsState {
    globalPermissionsStatus: Map<string, boolean>;
    ownerSettings: VirtualDesktopPermissionProfile | undefined;
    isSshToggleInProgress: boolean;
    isPublic: boolean;
}

class GlobalPermissions extends Component<GlobalPermissionsProps, GlobalPermissionsState> {
    listing: RefObject<IdeaListView>;

    constructor(props: GlobalPermissionsProps) {
        super(props);
        this.listing = React.createRef();
        this.state = {
            globalPermissionsStatus: new Map<string, boolean>(),
            ownerSettings: undefined,
            isSshToggleInProgress: false,
            isPublic: true
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

    backendClient(): BackendClient {
        return AppContext.get().client().backend();
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

    onChangeSSH = (value: boolean) => {
        this.setState({ isSshToggleInProgress: true });
        this.setFlashbarMessage("success", `SSH access is being ${value ? "enabled" : "disabled"}. The application will auto-reload once the change takes effect.`);
        this.backendClient().config({ssh_enabled: value}).then(() => {
            this.setState({
                globalPermissionsStatus: new Map(this.state.globalPermissionsStatus).set(Constants.SSH_CONFIG_FEATURE_TITLE, value)
            });

            // Check if the SSH config change has taken effect
            const maxRetries = 10;
            let retryCount = 0;

            const checkSshStatus = () => {
                this.clusterSettingsClient().getModuleSettings({
                    module_id: Constants.MODULE_BASTION_HOST
                }).then((response) => {
                    const isSshEnabled = dot.pick(Constants.BASTION_HOST_INSTANCE_ID_KEY_NAME, response.settings) !== undefined;

                    if (isSshEnabled === value) {
                        // SSH status matches the desired state, reload the page
                        this.setState({ isSshToggleInProgress: false });
                        window.location.reload();
                    } else {
                        // SSH status hasn't changed yet, check again after a short delay
                        retryCount++;
                        if (retryCount < maxRetries) {
                            setTimeout(checkSshStatus, 2000); // Check every 2 seconds
                        } else {
                            this.setState({ isSshToggleInProgress: false });
                            this.setFlashbarMessage("warning", "SSH status change is taking longer than expected. Please refresh the page manually.");
                        }
                    }
                }).catch((error) => {
                    console.error("Error checking SSH status:", error);
                    this.setState({ isSshToggleInProgress: false });
                    this.setFlashbarMessage("error", "Failed to verify SSH status change. Please refresh the page manually.");
                });
            };

            // Start checking SSH status
            checkSshStatus();

        }).catch((e) => {
            this.setFlashbarMessage("error", `Failed to ${value ? "enable" : "disable"} SSH access.`);
            this.setState({ isSshToggleInProgress: false });
        });
    }


    onChangeOwnerSetting(key: string, value: boolean, name: string) {
        const profileToUpdate = structuredClone(this.state.ownerSettings!);
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
            this.setState({
                ownerSettings: profileToUpdate,
                globalPermissionsStatus: new Map(this.state.globalPermissionsStatus).set(key, value)
            });
        }).catch((e) => {
            this.setFlashbarMessage("error", `Failed to ${value ? "enable" : "disable"} the ${name} permission due to internal software error. Please contact AWS support.`);
        });
    }

    async getGlobalPermissions(): Promise<void> {
        const newGlobalPermissionsStatus = new Map<string, boolean>();
        const sharedStorageModuleSettings = await this.clusterSettingsClient().getModuleSettings({ module_id: Constants.MODULE_SHARED_STORAGE });
        newGlobalPermissionsStatus.set(Constants.SHARED_STORAGE_FILE_BROWSER_FEATURE_TITLE, dot.pick(Constants.SHARED_STORAGE_FILE_BROWSER_KEY, sharedStorageModuleSettings.settings))

        const bastionHostModuleSettings = await this.clusterSettingsClient().getModuleSettings({ module_id: Constants.MODULE_BASTION_HOST });
        newGlobalPermissionsStatus.set(Constants.SSH_CONFIG_FEATURE_TITLE, dot.pick(Constants.BASTION_HOST_INSTANCE_ID_KEY_NAME, bastionHostModuleSettings.settings))
        const isPublic = dot.pick(Constants.BASTION_HOST_IS_PUBLIC_KEY_NAME, bastionHostModuleSettings.settings);

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

        this.setState({ globalPermissionsStatus: newGlobalPermissionsStatus, ownerSettings, isPublic });
    }

    getPermissionComponent(setting: VirtualDesktopPermission) {
        return <Toggle
            checked={this.state.globalPermissionsStatus.get(setting.key!) ?? false}
            onChange={(changeEvent) => {this.onChangeOwnerSetting(setting.key!, changeEvent.detail.checked, setting.name!)}}
        >
            <FormField
                label={
                    <span style={{ fontWeight: 'normal' }}>
                        {setting.name}
                    </span>
                }
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
        const isSSHEnabled = this.state.globalPermissionsStatus.get(Constants.SSH_CONFIG_FEATURE_TITLE) ?? false;
        const ownerProfile = this.state.ownerSettings;
        const basicSettings = ownerProfile?.permissions?.filter((p) => Constants.DCV_SETTINGS_DESKTOP_SETTINGS.getAllColumns().includes(p.key!));
        const advancedSettings = ownerProfile?.permissions?.filter((p) => Constants.DCV_SETTINGS_DESKTOP_ADVANCED_SETTINGS.getAllColumns().includes(p.key!));
        return (
            <SpaceBetween size="l">
                <ExpandableSection
                    headerText={
                        <span style={{ fontWeight: 'lighter' }}>
                        File browser and SSH permissions (enabled {(isFileBrowserEnabled ? 1 : 0) + (isSSHEnabled ? 1 : 0)}/2)
                        </span>
                    }
                >
                    <SpaceBetween size="m" direction="vertical">
                        <SpaceBetween size="m" direction="horizontal">
                            <Toggle
                                checked={isFileBrowserEnabled}
                                onChange={(changeEvent) => this.onChangeFileBrowser(changeEvent.detail.checked)}
                            />
                            <FormField
                                label={
                                    <span style={{ fontWeight: 'normal' }}>
                                        File browser
                                    </span>
                                }
                                description="Display File browser in the navigation menu and access data via web portal."
                            />
                        </SpaceBetween>
                        <SpaceBetween size="m" direction="vertical">
                            <SpaceBetween size="m" direction="horizontal">
                                <Toggle
                                    checked={isSSHEnabled}
                                    onChange={(changeEvent) => this.onChangeSSH(changeEvent.detail.checked)}
                                    disabled={this.state.isSshToggleInProgress || !this.state.isPublic}
                                />
                                <FormField
                                    label={
                                        <span style={{ fontWeight: 'normal' }}>
                                            SSH access
                                        </span>
                                    }
                                    description="Access data and desktops via Secure Shell (SSH). Enabling displays 'SSH access instructions' in the navigation menu. Disabling SSH removes the menu item."
                                />
                            </SpaceBetween>
                        </SpaceBetween>
                    </SpaceBetween>
                    <Alert
                        statusIconAriaLabel="info"
                        type="info"
                        dismissible={false}
                    >
                        Enabling SSH access adds the Bastion host, which may take several minutes to provision. You are responsible for any EC2 charges associated with the bastion host. Disabling SSH terminates the host.
                        <Link href="#/cluster/status" external={true} variant="secondary"> View module status</Link>
                    </Alert>
                </ExpandableSection>

                <ExpandableSection
                    headerText={
                        <span style={{ fontWeight: 'lighter' }}>
                        Desktop permissions (enabled {basicSettings?.filter(p => p.enabled && p.key !== "unsupervised_access")?.length ?? 0}/{Constants.DCV_SETTINGS_DESKTOP_SETTINGS.getAllColumns().filter(x => x !== "unsupervised_access").length})
                        </span>
                    }
                >
                    <Alert
                        statusIconAriaLabel="info"
                        type="info"
                        dismissible={false}
                    >
                        The following permissions are critical, before disabling/enabling them, review implications.
                        <Link href="https://docs.aws.amazon.com/dcv/latest/adminguide/security-authorization-file-create-permission.html" external={true} variant="secondary"> Learn more</Link>
                    </Alert>
                    <br />
                    <ColumnLayout columns={3} borders="vertical">
                        {this.getPermissionColumn(ownerProfile, Constants.DCV_SETTINGS_DESKTOP_SETTINGS.column_one.filter(x => x !== "unsupervised_access"))}
                        {this.getPermissionColumn(ownerProfile, Constants.DCV_SETTINGS_DESKTOP_SETTINGS.column_two)}
                        {this.getPermissionColumn(ownerProfile, Constants.DCV_SETTINGS_DESKTOP_SETTINGS.column_three)}
                    </ColumnLayout>
                </ExpandableSection>
                <ExpandableSection
                    headerText={
                        <span style={{ fontWeight: 'lighter' }}>
                        Desktop advanced settings (enabled {advancedSettings?.filter(p => p.enabled)?.length ?? 0}/{Constants.DCV_SETTINGS_DESKTOP_ADVANCED_SETTINGS.getAllColumns().length})
                        </span>
                    }
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
                >Environment boundaries</Header>}
            >
                {this.buildListing()}
            </Container>
        );
    }
}

export default withRouter(GlobalPermissions);
