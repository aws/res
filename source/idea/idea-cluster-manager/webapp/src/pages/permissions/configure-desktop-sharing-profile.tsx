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
import IdeaForm from "../../components/form";
import { SocaUserInputParamMetadata, VirtualDesktopPermission, VirtualDesktopPermissionProfile } from "../../client/data-model";
import { AppContext } from "../../common";
import VirtualDesktopUtilsClient from "../../client/virtual-desktop-utils-client";
import { Constants } from "../../common/constants";
import IdeaAppLayout, { IdeaAppLayoutProps } from "../../components/app-layout";
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import { Alert, Box, Button, ColumnLayout, Container, ExpandableSection, FormField, Header, Modal, SpaceBetween, StatusIndicator, StatusIndicatorProps, TextContent, Toggle } from "@cloudscape-design/components";
import { VirtualDesktopAdminClient } from "../../client";
import { withRouter } from "../../navigation/navigation-utils";

export interface ConfigureDesktopSharingProfileProps extends IdeaAppLayoutProps, IdeaSideNavigationProps { }

export interface ConfigureDesktopSharingProfileState {
    loading: boolean;
    ownerSettings: VirtualDesktopPermissionProfile | undefined;
    editMode: boolean;
    profileToEdit?: VirtualDesktopPermissionProfile;
    from_page: "detail" | "dashboard";
    ownerPermissions: Map<string, boolean>;
    profilePermissions: Map<string, boolean>;
    showConfirmationModal: boolean;
}

class ConfigureDesktopSharingProfile extends Component<ConfigureDesktopSharingProfileProps, ConfigureDesktopSharingProfileState> {
    form: RefObject<IdeaForm>;
    permissionProfileInputHistory: { [key: string]: boolean };

    constructor(props: ConfigureDesktopSharingProfileProps) {
        super(props);
        this.permissionProfileInputHistory = {};
        this.form = React.createRef();
        const { state } = this.props.location;
        this.state = {
            loading: true,
            ownerSettings: undefined,
            from_page: state.from_page,
            editMode: state.isUpdate ?? false,
            profileToEdit: state.profileToEdit,
            ownerPermissions: new Map<string, boolean>(),
            profilePermissions: new Map<string, boolean>(),
            showConfirmationModal: false,
        };
    }

    buildTitle(): string {
        if (this.state.editMode) {
            return `Update desktop sharing profile: ${this.state.profileToEdit?.title}`;
        }
        return "Register new desktop sharing profile";
    }

    getVirtualDesktopUtilsClient(): VirtualDesktopUtilsClient {
        return AppContext.get().client().virtualDesktopUtils();
    }

    getVirtualDesktopAdminClient(): VirtualDesktopAdminClient {
        return AppContext.get().client().virtualDesktopAdmin();
    }

    getForm(): IdeaForm | null {
        return this.form.current;
    }

    async getOwnerDesktopSettings(): Promise<void> {
        const profile = await this.getVirtualDesktopUtilsClient().getPermissionProfile({
            profile_id: Constants.DCV_SETTINGS_DEFAULT_OWNER_PROFILE_ID,
        });

        if (!profile.profile) {
            console.error("Failed to retrieve owner settings");
        }
        const ownerPermissions = new Map<string, boolean>();
        let permissions = new Map<string, boolean>();
        for (const permission of profile.profile?.permissions!) {
            ownerPermissions.set(permission.key!, permission.enabled!)
        }
        if (this.state.editMode) {
            for (const permission of this.state.profileToEdit!.permissions!) {
                permissions.set(permission.key!, permission.enabled!)
            }
        } else {
            permissions = new Map(ownerPermissions);
        }
        this.setState({
            ownerSettings: profile.profile,
            ownerPermissions: ownerPermissions,
            profilePermissions: permissions,
            loading: false,
        });
    }

    getValueOfOwnerSettingsForPermission(permissionToCheck: VirtualDesktopPermission): boolean {
        const ownerPerms = this.state.ownerSettings?.permissions;
        return ownerPerms?.find(perm => perm.key === permissionToCheck.key)?.enabled ?? true;
    }

    componentDidMount() {
        this.getOwnerDesktopSettings();
    }

    buildDefaultTitle(): string {
        if (this.state.editMode) {
            return this.state.profileToEdit?.title!;
        }
        return "";
    }

    buildDefaultDescription(): string {
        if (this.state.editMode) {
            return this.state.profileToEdit?.description!;
        }
        return "";
    }

    getDefaultValueForPermission(basePermission: VirtualDesktopPermission): boolean {
        let defaultValue = false;
        this.state.profileToEdit?.permissions?.forEach((permission) => {
            if (basePermission.key === permission.key) {
                defaultValue = this.getValueOfOwnerSettingsForPermission(permission) ? permission.enabled! : false;
                this.permissionProfileInputHistory[permission.key!] = permission.enabled!;
            }
        });
        return defaultValue;
    }

    setFlashbarMessage(type: "success" | "error", message: string) {
        this.props.onFlashbarChange({
            items: [
                {
                    type: type,
                    content: message,
                    dismissible: true,
                },
            ],
        });
    }

    createProfile(permissionProfile: VirtualDesktopPermissionProfile) {
        this.getVirtualDesktopAdminClient()
            .createPermissionProfile({
                profile: permissionProfile,
            })
            .then((_) => {
                setTimeout(() => {
                    this.setFlashbarMessage("success", `${permissionProfile.title} profile created successfully.`);
                }, 500)
                this.returnToPreviousPage();
            })
            .catch((error) => {
                this.getForm()!.setError(error.errorCode, error.message);
            });
    }

    editProfile(permissionProfile: VirtualDesktopPermissionProfile) {
        this.getVirtualDesktopAdminClient()
            .updatePermissionProfile({
                profile: permissionProfile,
            })
            .then((response) => {
                setTimeout(() => {
                    this.setFlashbarMessage("success", `${permissionProfile.title} profile updated successfully.`);
                }, 500)
                this.returnToPreviousPage()
            })
            .catch((error) => {
                this.getForm()!.setError(error.errorCode, error.message);
            });
    }

    onChangeSetting(key: string, value: boolean) {
        const profilePermissions = this.state.profilePermissions;
        profilePermissions.set(key, value);
        this.setState({ profilePermissions: profilePermissions });
    }

    isSettingAllowedGlobally(permissionKey: string): boolean {
        if (!this.state.ownerSettings) {
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

    getSettingDescription(description: string, allowedGlobally: boolean): string | JSX.Element {
        return allowedGlobally ?
            description :
            <>{description}<br /><span style={{font: "inherit", color: "#8d6605"}}>Disabled globally</span></>;
    }

    buildProfileDetailsForm(): any {
        let formParams: SocaUserInputParamMetadata[];
        if (this.state.loading) {
            formParams = [
                {
                    name: "loading",
                    title: "Loading base permissions",
                    data_type: "str",
                    param_type: "heading3",
                    readonly: true,
                    container_group_name: "profile_details",
                },
            ];
        } else {
            formParams = [
                {
                    name: "title",
                    title: "Profile name",
                    description: "Assign a name to the profile.",
                    help_text: "Must start with a letter. Must contain 1 to 64 alphanumeric characters.",
                    data_type: "str",
                    default: this.buildDefaultTitle(),
                    param_type: "text",
                    validate: {
                        required: true,
                        max: 64,
                        min: 1
                    },
                    container_group_name: "profile_details",
                },
                {
                    name: "description",
                    title: "Profile description",
                    description: "Optionally add more details to describe the specific profile.",
                    data_type: "str",
                    default: this.buildDefaultDescription(),
                    param_type: "text",
                    optional: true,
                    container_group_name: "profile_details",
                },
            ];
        }
        return <IdeaForm
            ref={this.form}
            name="create-project-permissions"
            params={formParams}
            useContainers
            showActions={false}
            containerGroups={[{ title: "Profile definition", name: "profile_details" }]}
        />
    }

    getPermissionComponent(setting: VirtualDesktopPermission) {
        const allowed: boolean = this.isSettingAllowedGlobally(setting.key!);
        const enabled: boolean = this.state.profilePermissions.get(setting.key!)! && allowed;
        return <Toggle
            checked={enabled}
            disabled={!allowed}
            onChange={(changeEvent) => this.onChangeSetting(setting.key!, changeEvent.detail.checked)}
        >
            <FormField
                label={setting.name!}
                description={this.getSettingDescription(setting.description!, allowed)}
            >
            </FormField>
        </Toggle>
    }

    getPermissionColumn(ownerProfile: VirtualDesktopPermissionProfile | undefined, filterArray: string[]) {
        return <SpaceBetween size="l" direction="vertical">
            {ownerProfile?.permissions?.filter((p) => filterArray.includes(p.key!))?.map((setting) => this.getPermissionComponent(setting))}
        </SpaceBetween>
    }

    buildPermissions() {
        const ownerProfile = this.state.ownerSettings;
        const basicSettings = ownerProfile?.permissions?.filter((p) => Constants.DCV_SETTINGS_DESKTOP_SETTINGS.getAllColumns().includes(p.key!));
        const advancedSettings = ownerProfile?.permissions?.filter((p) => Constants.DCV_SETTINGS_DESKTOP_ADVANCED_SETTINGS.getAllColumns().includes(p.key!));
        return <Container header={
            <Header 
                description="Permissions granted to this sharing profile. To enable the permissions that are 'Disabled globally', go back to the Environment boundaries and enable them there."
            >
                Permissions
            </Header>
        }>
            <SpaceBetween size="l">
                <ExpandableSection
                    defaultExpanded
                    headerText={`Desktop permissions (enabled ${basicSettings?.filter(p => p.enabled)?.length ?? 0}/${Constants.DCV_SETTINGS_DESKTOP_SETTINGS.getAllColumns().length})`}
                >
                    <br />
                    <ColumnLayout columns={3} borders="vertical">
                        {this.getPermissionColumn(ownerProfile, Constants.DCV_SETTINGS_DESKTOP_SETTINGS.column_one)}
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
        </Container>

    }

    buildConfirmationModal() {
        return <Modal
            visible={this.state.showConfirmationModal}
            onDismiss={() => this.setState({ showConfirmationModal: false })}
            header={<Header variant="h3">Save changes</Header>}
            footer={
                <Box float="right">
                    <SpaceBetween direction="horizontal" size="xs">
                        <Button variant="link" onClick={() => this.setState({ showConfirmationModal: false })}>Cancel</Button>
                        <Button variant="primary" onClick={() => this.submit()}>Save</Button>
                    </SpaceBetween>
                </Box>
            }
        >
            Update <b>{this.state.profileToEdit?.title}</b> sharing profile.
            <Alert type="info">Proceeding with this action will impact any existing desktop sharing sessions. Click save for the new settings to take effect or cancel.</Alert>
        </Modal>
    }

    returnToPreviousPage() {
        if (this.state.from_page === "dashboard") {
            this.props.navigate("/cluster/permissions", { state: {
                activeTabId: "desktop-sharing-profiles"
            }});
        } else {
            this.props.navigate(`/cluster/permissions/sharing-profiles/${this.state.profileToEdit!.profile_id}`);
        }
    }

    submit() {
        if (!this.getForm()!.validate()) {
            this.getForm()!.setError("Input error", "Incorrect parameters entered")
            return;
        }
        const details = this.getForm()!.getValues();
        const permissions: VirtualDesktopPermission[] = Array.from(this.state.profilePermissions).map(([key, enabled]) => ({
            key: key,
            enabled: enabled,
        }));
        permissions[permissions.findIndex((p) => p.key === "builtin")].enabled = false;
        const permissionProfile: VirtualDesktopPermissionProfile = {
            profile_id: this.state.editMode ? this.state.profileToEdit!.profile_id! : `${(details.title as string).trim().toLowerCase().replaceAll(/[-| ]/g, "_")}`,
            title: details.title,
            description: this.getForm()!.getValue("description"),
            permissions,
        };
        if (this.state.editMode) {
            this.editProfile(permissionProfile);
        } else {
            this.createProfile(permissionProfile);
        }
    }

    render() {
        const breadCrumbItems = [
            {
                text: "RES",
                href: "#/",
            },
            {
                text: "Permission policy: Desktop sharing profiles",
                href: "#/cluster/permissions",
            }
        ];
        if (this.state.editMode) {
            breadCrumbItems.push(...[
                {
                    text: this.state.profileToEdit?.title!,
                    href: `#/cluster/permissions/project-roles/${this.state.profileToEdit?.profile_id}`
                },
                {
                    text: "Edit",
                    href: "",
                }
            ])
        } else {
            breadCrumbItems.push({
                text: "Create profile",
                href: "",
            });
        }
        return <IdeaAppLayout
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
            breadcrumbItems={breadCrumbItems}
            header={
                <Header variant="h1">
                    {this.state.editMode ? `Edit ${this.state.profileToEdit?.title}` : "Create desktop sharing profile"}
                </Header>
            }
            content={
                <SpaceBetween size="l">
                    {this.buildConfirmationModal()}
                    {this.buildProfileDetailsForm()}
                    {this.buildPermissions()}
                    <Box float="right">
                        <SpaceBetween size="l" direction="horizontal">
                            <Button onClick={() => this.returnToPreviousPage()}>Cancel</Button>
                            <Button variant="primary" onClick={(_) => {
                                if (this.state.editMode) {
                                    this.setState({
                                        showConfirmationModal: true,
                                    })
                                } else {
                                    this.submit()
                                }
                            }}>Save changes</Button>
                        </SpaceBetween>
                    </Box>
                </SpaceBetween>
            }
        />
    }
}

export default withRouter(ConfigureDesktopSharingProfile);
