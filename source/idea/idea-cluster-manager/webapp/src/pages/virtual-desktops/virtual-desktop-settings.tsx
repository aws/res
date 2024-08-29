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

import { Button, ColumnLayout, Container, Header, Link, SpaceBetween, Table, Tabs, TextContent, Toggle } from '@cloudscape-design/components';
import IdeaForm from "../../components/form";
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import IdeaAppLayout, { IdeaAppLayoutProps } from "../../components/app-layout";
import { KeyValue, KeyValueGroup } from "../../components/key-value";
import { AppContext } from "../../common";
import Utils from "../../common/utils";
import dot from "dot-object";
import { EnabledDisabledStatusIndicator } from "../../components/common";
import { Constants } from "../../common/constants";
import { withRouter } from "../../navigation/navigation-utils";
import ConfigUtils from "../../common/config-utils";
import { SocaUserInputChoice, UpdateModuleSettingsRequestVDC, UpdateModuleSettingsValuesDCVSession } from "../../client/data-model";

export interface VirtualDesktopSettingsProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {}

export interface VirtualDesktopSettingsState {
    vdcModuleInfo: any;
    vdcSettings: any;
    clusterManager: any;
    clusterSettings: any;
    activeTabId: string;
    instanceTypeAndFamilyChoices: SocaUserInputChoice[];
}

const DEFAULT_ACTIVE_TAB_ID = "general";
const VDC_MODULE_ID = "vdc";

class VirtualDesktopSettings extends Component<VirtualDesktopSettingsProps, VirtualDesktopSettingsState> {
    generalSettingsForm: RefObject<IdeaForm>;
    updateDCVSessionSettingsForm: RefObject<IdeaForm>;
    updateDCVHostSettingsForm: RefObject<IdeaForm>;

    constructor(props: VirtualDesktopSettingsProps) {
        super(props);
        this.generalSettingsForm = React.createRef();
        this.updateDCVSessionSettingsForm = React.createRef();
        this.updateDCVHostSettingsForm = React.createRef();
        this.state = {
            vdcModuleInfo: {},
            vdcSettings: {},
            clusterManager: {},
            clusterSettings: {},
            activeTabId: DEFAULT_ACTIVE_TAB_ID,
            instanceTypeAndFamilyChoices: []
        };
    }

    buildUpdateDCVSessionSettingsForm() {
        return (
            <IdeaForm
                ref={this.updateDCVSessionSettingsForm}
                name="update-dcv-session-settings"
                modal={true}
                title="Update DCV Session Settings"
                onSubmit={() => {
                    if (!this.updateDCVSessionSettingsForm.current?.validate()) {
                        return;
                    }
                    const values = this.updateDCVSessionSettingsForm.current?.getValues();
                    const updateSettings: UpdateModuleSettingsRequestVDC = {
                        module_id: VDC_MODULE_ID,
                        settings: {
                            dcv_session: {},
                        },
                    };

                    if (values.idle_timeout !== String(dot.pick("dcv_session.idle_timeout", this.state.vdcSettings))) {
                        updateSettings.settings.dcv_session[UpdateModuleSettingsValuesDCVSession.IDLE_TIMEOUT] = values.idle_timeout;
                    }
                    if (values.idle_timeout_warning !== String(dot.pick("dcv_session.idle_timeout_warning", this.state.vdcSettings))) {
                        updateSettings.settings.dcv_session[UpdateModuleSettingsValuesDCVSession.IDLE_TIMEOUT_WARNING] = values.idle_timeout_warning;
                    }
                    if (values.cpu_utilization_threshold !== String(dot.pick("dcv_session.cpu_utilization_threshold", this.state.vdcSettings))) {
                        updateSettings.settings.dcv_session[UpdateModuleSettingsValuesDCVSession.CPU_UTILIZATION_THRESHOLD] = values.cpu_utilization_threshold;
                    }
                    if (values.allowed_sessions_per_user !== String(dot.pick("dcv_session.allowed_sessions_per_user", this.state.vdcSettings))) {
                        updateSettings.settings.dcv_session[UpdateModuleSettingsValuesDCVSession.ALLOWED_SESSIONS_PER_USER] = values.allowed_sessions_per_user;
                    }

                    if (Object.keys(updateSettings.settings.dcv_session).length > 0) {
                        AppContext.get()
                            .client()
                            .clusterSettings()
                            .updateModuleSettings(updateSettings)
                            .then(() => {
                                this.props.onFlashbarChange({
                                    items: [
                                        {
                                            type: "success",
                                            content: "DCV Session settings updated successfully.",
                                            dismissible: true,
                                        },
                                    ],
                                });
                                this.loadSettings();
                                this.updateDCVSessionSettingsForm.current?.hideModal();
                            })
                            .catch((error) => {
                                this.updateDCVSessionSettingsForm.current?.setError(error.errorCode, error.message);
                            });
                    } else {
                        this.updateDCVSessionSettingsForm.current?.setError("400", "No settings updated.");
                    }
                }}
                onCancel={() => {
                    this.updateDCVSessionSettingsForm.current?.hideModal();
                }}
                params={[
                    {
                        name: "idle_timeout",
                        title: "Idle Timeout",
                        validate: {
                            required: true,
                            min: 0,
                            max: 87600,
                        },
                        default: dot.pick("dcv_session.idle_timeout", this.state.vdcSettings),
                    },
                    {
                        name: "idle_timeout_warning",
                        title: "Idle Timeout Warning",
                        validate: {
                            required: true,
                            min: 0,
                            max: 87600,
                        },
                        default: dot.pick("dcv_session.idle_timeout_warning", this.state.vdcSettings),
                    },
                    {
                        name: "cpu_utilization_threshold",
                        title: "CPU Utilization Threshold",
                        validate: {
                            required: true,
                            min: 1,
                            max: 100,
                        },
                        default: dot.pick("dcv_session.cpu_utilization_threshold", this.state.vdcSettings),
                    },
                    {
                        name: "allowed_sessions_per_user",
                        title: "Allowed Sessions Per User",
                        validate: {
                            required: true,
                            min: 0,
                            max: 100,
                        },
                        default: dot.pick("dcv_session.allowed_sessions_per_user", this.state.vdcSettings),
                    },
                ]}
            />
        );
    }

    buildUpdateDCVHostSettingsForm() {
        return (
            <IdeaForm
                ref={this.updateDCVHostSettingsForm}
                name="update-dcv-host-settings"
                modal={true}
                title="Update DCV Host Settings"
                onSubmit={() => {
                    if (!this.updateDCVHostSettingsForm.current?.validate()) {
                        return;
                    }
                    const values = this.updateDCVHostSettingsForm.current?.getValues();
                    const updateSettings: UpdateModuleSettingsRequestVDC = {
                        module_id: VDC_MODULE_ID,
                        settings: {
                            dcv_session: {},
                        },
                    };

                    if (values.max_root_volume_memory !== String(dot.pick("dcv_session.max_root_volume_memory", this.state.vdcSettings))) {
                        updateSettings.settings.dcv_session[UpdateModuleSettingsValuesDCVSession.MAX_ROOT_VOLUME_MEMORY] = values.max_root_volume_memory;
                    }

                    updateSettings.settings.dcv_session[UpdateModuleSettingsValuesDCVSession.ALLOWED_INSTANCE_TYPES] = values.allowed_instance_types;

                    if (Object.keys(updateSettings.settings.dcv_session).length > 0) {
                        AppContext.get()
                            .client()
                            .clusterSettings()
                            .updateModuleSettings(updateSettings)
                            .then(() => {
                                this.props.onFlashbarChange({
                                    items: [
                                        {
                                            type: "success",
                                            content: "DCV Host settings updated successfully.",
                                            dismissible: true,
                                        },
                                    ],
                                });
                                this.loadSettings();
                                this.updateDCVHostSettingsForm.current?.hideModal();
                            })
                            .catch((error) => {
                                this.updateDCVHostSettingsForm.current?.setError(error.errorCode, error.message);
                            });
                    } else {
                        this.updateDCVHostSettingsForm.current?.setError("400", "No settings updated.");
                    }
                }}
                onCancel={() => {
                    this.updateDCVHostSettingsForm.current?.hideModal();
                }}
                params={[
                    {
                        name: "max_root_volume_memory",
                        title: "Max Root Volume Size",
                        validate: {
                            required: true,
                            min: 1,
                            max: 1000,
                        },
                        default: dot.pick("dcv_session.max_root_volume_memory", this.state.vdcSettings),
                    },
                    {
                        name: "allowed_instance_types",
                        title: "Allowed Instance Types",
                        data_type: "str",
                        param_type: "select",
                        multiple: true,
                        choices: this.state.instanceTypeAndFamilyChoices,
                        default: dot.pick("dcv_session.instance_types.allow", this.state.vdcSettings),
                    },
                ]}
            />
        );
    }

    componentDidMount() {
        this.loadSettings();
    }

    getInstanceChoices(inputList: any[]): String[] {
        const instanceChoices: Set<string> = new Set<string>();
        inputList.forEach((item) => {
            const instanceType = item.InstanceType;
            const instanceFamily = instanceType.split('.')[0];
            instanceChoices.add(instanceType);
            instanceChoices.add(instanceFamily);
        });
        return Array.from(instanceChoices).sort();
    }

    loadSettings() {
        let promises: Promise<any>[] = [];
        const clusterSettingsService = AppContext.get().getClusterSettingsService();
        //0
        promises.push(clusterSettingsService.getClusterSettings(false));
        //1
        promises.push(clusterSettingsService.getVirtualDesktopSettings(false));
        //2
        promises.push(clusterSettingsService.getClusterManagerSettings(false));
        //3
        promises.push(clusterSettingsService.getInstanceTypes());
        Promise.all(promises).then((result) => {
            const instanceChoices = this.getInstanceChoices(result[3]);
            const queryParams = new URLSearchParams(this.props.location.search);
            this.setState(
                {
                    vdcModuleInfo: AppContext.get().getClusterSettingsService().getModuleInfo(Constants.MODULE_VIRTUAL_DESKTOP_CONTROLLER),
                    vdcSettings: result[1],
                    clusterManager: result[2],
                    clusterSettings: result[0],
                    instanceTypeAndFamilyChoices: instanceChoices.map((instanceChoice: any) => ({
                        title: instanceChoice,
                        value: instanceChoice,
                    })),
                    activeTabId: Utils.asString(queryParams.get("tab"), DEFAULT_ACTIVE_TAB_ID),
                },
                () => {
                    this.updateDCVSessionSettingsForm.current?.registry.list().map((field) => {
                        field.setState({ default: field.props.param.default });
                    });
                    this.updateDCVHostSettingsForm.current?.registry.list().map((field) => {
                        field.setState({ default: field.props.param.default });
                    });
                    this.updateDCVSessionSettingsForm.current?.reset();
                    this.updateDCVHostSettingsForm.current?.reset();
                }
            );
        });
    }

    buildNotificationSettings() {
        let notifications = dot.pick("dcv_session.notifications", this.state.vdcSettings);
        let items: any[] = [];
        if (notifications) {
            Object.keys(notifications).forEach((settingName) => {
                items.push({
                    name: settingName,
                    enabled: Utils.asBoolean(dot.pick(`dcv_session.notifications.${settingName}.enabled`, this.state.vdcSettings)),
                    email_template: dot.pick(`dcv_session.notifications.${settingName}.email_template`, this.state.vdcSettings),
                });
            });
        }
        return (
            <Table
                items={items}
                columnDefinitions={[
                    {
                        header: "Session State",
                        cell: (e) => e.name,
                    },
                    {
                        header: "Status",
                        cell: (e) => <EnabledDisabledStatusIndicator enabled={e.enabled} />,
                    },
                    {
                        header: "Email Template Name",
                        cell: (e) => e.email_template,
                    },
                ]}
            />
        );
    }

    render() {
        const getVirtualDesktopOpenAPISpecUrl = () => {
            return `${AppContext.get().getHttpEndpoint()}${Utils.getApiContextPath(Constants.MODULE_VIRTUAL_DESKTOP_CONTROLLER)}/openapi.yml`;
        };

        const getVirtualDesktopSwaggerEditorUrl = () => {
            return `https://editor.swagger.io/?url=${getVirtualDesktopOpenAPISpecUrl()}`;
        };

        const getInternalALBUrl = () => {
            return ConfigUtils.getInternalAlbUrl(this.state.clusterSettings);
        };

        const isClusterBackupEnabled = () => {
            return Utils.asBoolean(dot.pick("backups.enabled", this.state.clusterSettings));
        };

        const isVDIBackupEnabled = () => {
            return Utils.asBoolean(dot.pick("vdi_host_backup.enabled", this.state.vdcSettings));
        };

        const isBackupEnabled = () => {
            return isVDIBackupEnabled() && isClusterBackupEnabled();
        };

        const isGatewayCertificateSelfSigned = (): boolean => {
            return !Utils.asBoolean(dot.pick("dcv_connection_gateway.certificate.provided", this.state.vdcSettings), false);
        };

        const handleQuicToggleChange = (newToggleStatus: boolean) => {
            AppContext.get().client().clusterSettings().configureQUIC(
                {
                    enable: newToggleStatus
                }
            ).then((res)=> {
                this.props.onFlashbarChange({
                    items: [
                        {
                            type: "success",
                            content: "Successfully updated QUIC configuration.",
                            dismissible: true
                        }
                    ]
                })
                const vdcSettings = {...this.state.vdcSettings}
                dot.set("dcv_session.quic_support", `${newToggleStatus}`, vdcSettings)
                this.setState({vdcSettings: vdcSettings})
            }).catch((error) =>{
                if (error.errorCode == "ROLLBACK_COMPLETE") {
                    this.props.onFlashbarChange({
                        items: [
                            {
                                type: "warning",
                                content: error.message,
                                dismissible: true
                            }
                        ]
                    })
                } else {
                    this.props.onFlashbarChange({
                        items: [
                            {
                                type: "error",
                                content: error.message,
                                dismissible: true
                            }
                        ]
                    })
                }
            });
        }

        const buildAutoScalingSettingContainer = (setting: any) => {
            return (
                <Container header={<Header variant={"h2"}>Autoscaling</Header>}>
                    <ColumnLayout variant={"text-grid"} columns={2}>
                        <KeyValue title="Min Instances" value={dot.pick("autoscaling.min_capacity", setting)} />
                        <KeyValue title="Max Instances" value={dot.pick("autoscaling.max_capacity", setting)} />
                        <KeyValue title="Scale-In Protection">
                            <EnabledDisabledStatusIndicator enabled={Utils.asBoolean(dot.pick("autoscaling.new_instances_protected_from_scale_in", setting))} />
                        </KeyValue>
                        <KeyValue title={"ARN"} value={dot.pick("asg_arn", setting)} clipboard={true} type={"ec2:asg-arn"} />
                    </ColumnLayout>
                    <KeyValueGroup title={"Scaling Policy"}>
                        <KeyValue title="CPU Target Utilization" value={dot.pick("autoscaling.cpu_utilization_scaling_policy.target_utilization_percent", setting)} suffix={"%"} />
                        <KeyValue title="Warmup time" value={dot.pick("autoscaling.cpu_utilization_scaling_policy.estimated_instance_warmup_minutes", setting)} suffix={"minutes"} />
                    </KeyValueGroup>
                </Container>
            );
        };

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
                        href: "#/virtual-desktop/dashboard",
                    },
                    {
                        text: "Settings",
                        href: "",
                    },
                ]}
                header={
                    <Header variant={"h1"} description={"Review the virtual desktop settings"}>
                        Virtual Desktop Settings
                    </Header>
                }
                contentType={"default"}
                content={
                    <SpaceBetween size={"l"}>
                        <Container>
                            <ColumnLayout variant={"text-grid"} columns={3}>
                                <KeyValue title="Module Name" value={dot.pick("name", this.state.vdcModuleInfo)} />
                                <KeyValue title="Module ID" value={dot.pick("module_id", this.state.vdcModuleInfo)} />
                                <KeyValue title="Version" value={dot.pick("version", this.state.vdcModuleInfo)} />
                            </ColumnLayout>
                        </Container>
                        <Tabs
                            activeTabId={this.state.activeTabId}
                            onChange={(event) => {
                                this.setState(
                                    {
                                        activeTabId: event.detail.activeTabId,
                                    },
                                    () => {
                                        this.props.searchParams.set("tab", event.detail.activeTabId);
                                        this.props.setSearchParams(this.props.searchParams);
                                    }
                                );
                            }}
                            tabs={[
                                {
                                    label: "General",
                                    id: "general",
                                    content: (
                                        <SpaceBetween size={"m"}>
                                            <Container header={<Header variant={"h2"}>General</Header>}>
                                                <ColumnLayout variant={"text-grid"} columns={2}>
                                                    <KeyValue title="QUIC">
                                                        <div>
                                                            <TextContent>
                                                                <p><small>Quick UDP Internet Connections (QUIC) is a protocol that attempts to improve streaming in higher latency environments.<br />Toggle on to activate QUIC in favor of TCP as the default streaming protocol for all your virtual desktops</small></p>
                                                            </TextContent>
                                                            <div style={{display: 'flex', flexDirection: 'row', gap: '4px'}}>
                                                                <EnabledDisabledStatusIndicator enabled={Utils.asBoolean(dot.pick("dcv_session.quic_support", this.state.vdcSettings))} />
                                                                <Toggle checked={Utils.asBoolean(dot.pick("dcv_session.quic_support", this.state.vdcSettings))} onChange={({ detail }) => handleQuicToggleChange(detail.checked)} />
                                                            </div>
                                                        </div>
                                                    </KeyValue>
                                                    <KeyValue title="eVDI Subnets" value={dot.pick("dcv_session.network.private_subnets", this.state.vdcSettings)} clipboard={true} />
                                                    <KeyValue title="Subnet AutoRetry">
                                                        <EnabledDisabledStatusIndicator enabled={Utils.asBoolean(dot.pick("dcv_session.network.subnet_autoretry", this.state.vdcSettings))} />
                                                    </KeyValue>
                                                    <KeyValue title="Randomize Subnets">
                                                        <EnabledDisabledStatusIndicator enabled={Utils.asBoolean(dot.pick("dcv_session.network.randomize_subnets", this.state.vdcSettings))} />
                                                    </KeyValue>
                                                </ColumnLayout>
                                            </Container>
                                            <Container
                                                header={
                                                    <Header
                                                        variant={"h2"}
                                                        info={
                                                            <Link external={true} href={"https://spec.openapis.org/oas/v3.1.0"}>
                                                                Info
                                                            </Link>
                                                        }
                                                    >
                                                        OpenAPI Specification
                                                    </Header>
                                                }
                                            >
                                                <ColumnLayout variant={"text-grid"} columns={1}>
                                                    <KeyValue title="eVDI API Spec" value={getVirtualDesktopOpenAPISpecUrl()} type={"external-link"} clipboard />
                                                </ColumnLayout>
                                            </Container>
                                        </SpaceBetween>
                                    ),
                                },
                                {
                                    label: "Notifications",
                                    id: "notifications",
                                    content: (
                                        <Container
                                            header={
                                                <Header variant={"h2"} description={"Notifications will be sent only if notifications are enabled in Cluster Settings"}>
                                                    Notifications
                                                </Header>
                                            }
                                        >
                                            {this.buildNotificationSettings()}
                                        </Container>
                                    ),
                                },
                                // {
                                //     label: "Schedule",
                                //     id: "schedule",
                                //     content: (
                                //         <SpaceBetween size={"m"}>
                                //             <Container
                                //                 header={
                                //                     <Header variant={"h2"} description={"Default schedule applied to all sessions"}>
                                //                         Default Schedule
                                //                     </Header>
                                //                 }
                                //             >
                                //                 <ColumnLayout variant={"text-grid"} columns={3}>
                                //                     <KeyValue
                                //                         title="Monday"
                                //                         value={Utils.getScheduleTypeDisplay(
                                //                             dot.pick("dcv_session.schedule.monday.type", this.state.vdcSettings),
                                //                             dot.pick("dcv_session.working_hours.start_up_time", this.state.vdcSettings),
                                //                             dot.pick("dcv_session.working_hours.shut_down_time", this.state.vdcSettings),
                                //                             dot.pick("dcv_session.schedule.monday.start_up_time", this.state.vdcSettings),
                                //                             dot.pick("dcv_session.schedule.monday.shut_down_time", this.state.vdcSettings)
                                //                         )}
                                //                     />
                                //                     <KeyValue
                                //                         title="Tuesday"
                                //                         value={Utils.getScheduleTypeDisplay(
                                //                             dot.pick("dcv_session.schedule.tuesday.type", this.state.vdcSettings),
                                //                             dot.pick("dcv_session.working_hours.start_up_time", this.state.vdcSettings),
                                //                             dot.pick("dcv_session.working_hours.shut_down_time", this.state.vdcSettings),
                                //                             dot.pick("dcv_session.schedule.tuesday.start_up_time", this.state.vdcSettings),
                                //                             dot.pick("dcv_session.schedule.tuesday.shut_down_time", this.state.vdcSettings)
                                //                         )}
                                //                     />
                                //                     <KeyValue
                                //                         title="Wednesday"
                                //                         value={Utils.getScheduleTypeDisplay(
                                //                             dot.pick("dcv_session.schedule.wednesday.type", this.state.vdcSettings),
                                //                             dot.pick("dcv_session.working_hours.start_up_time", this.state.vdcSettings),
                                //                             dot.pick("dcv_session.working_hours.shut_down_time", this.state.vdcSettings),
                                //                             dot.pick("dcv_session.schedule.wednesday.start_up_time", this.state.vdcSettings),
                                //                             dot.pick("dcv_session.schedule.wednesday.shut_down_time", this.state.vdcSettings)
                                //                         )}
                                //                     />
                                //                     <KeyValue
                                //                         title="Thursday"
                                //                         value={Utils.getScheduleTypeDisplay(
                                //                             dot.pick("dcv_session.schedule.thursday.type", this.state.vdcSettings),
                                //                             dot.pick("dcv_session.working_hours.start_up_time", this.state.vdcSettings),
                                //                             dot.pick("dcv_session.working_hours.shut_down_time", this.state.vdcSettings),
                                //                             dot.pick("dcv_session.schedule.thursday.start_up_time", this.state.vdcSettings),
                                //                             dot.pick("dcv_session.schedule.thursday.shut_down_time", this.state.vdcSettings)
                                //                         )}
                                //                     />
                                //                     <KeyValue
                                //                         title="Friday"
                                //                         value={Utils.getScheduleTypeDisplay(
                                //                             dot.pick("dcv_session.schedule.friday.type", this.state.vdcSettings),
                                //                             dot.pick("dcv_session.working_hours.start_up_time", this.state.vdcSettings),
                                //                             dot.pick("dcv_session.working_hours.shut_down_time", this.state.vdcSettings),
                                //                             dot.pick("dcv_session.schedule.friday.start_up_time", this.state.vdcSettings),
                                //                             dot.pick("dcv_session.schedule.friday.shut_down_time", this.state.vdcSettings)
                                //                         )}
                                //                     />
                                //                     <KeyValue
                                //                         title="Saturday"
                                //                         value={Utils.getScheduleTypeDisplay(
                                //                             dot.pick("dcv_session.schedule.saturday.type", this.state.vdcSettings),
                                //                             dot.pick("dcv_session.working_hours.start_up_time", this.state.vdcSettings),
                                //                             dot.pick("dcv_session.working_hours.shut_down_time", this.state.vdcSettings),
                                //                             dot.pick("dcv_session.schedule.saturday.start_up_time", this.state.vdcSettings),
                                //                             dot.pick("dcv_session.schedule.saturday.shut_down_time", this.state.vdcSettings)
                                //                         )}
                                //                     />
                                //                     <KeyValue
                                //                         title="Sunday"
                                //                         value={Utils.getScheduleTypeDisplay(
                                //                             dot.pick("dcv_session.schedule.sunday.type", this.state.vdcSettings),
                                //                             dot.pick("dcv_session.working_hours.start_up_time", this.state.vdcSettings),
                                //                             dot.pick("dcv_session.working_hours.shut_down_time", this.state.vdcSettings),
                                //                             dot.pick("dcv_session.schedule.sunday.start_up_time", this.state.vdcSettings),
                                //                             dot.pick("dcv_session.schedule.sunday.shut_down_time", this.state.vdcSettings)
                                //                         )}
                                //                     />
                                //                 </ColumnLayout>
                                //             </Container>
                                //             <Container header={<Header variant={"h2"}>Working Hours</Header>}>
                                //                 <ColumnLayout variant={"text-grid"} columns={3}>
                                //                     <KeyValue title="Start Time" value={dot.pick("dcv_session.working_hours.start_up_time", this.state.vdcSettings)} />
                                //                     <KeyValue title="End Time" value={dot.pick("dcv_session.working_hours.shut_down_time", this.state.vdcSettings)} />
                                //                 </ColumnLayout>
                                //             </Container>
                                //         </SpaceBetween>
                                //     ),
                                // },
                                {
                                    label: "Server",
                                    id: "server",
                                    content: (
                                        <SpaceBetween size={"m"}>
                                            {this.buildUpdateDCVSessionSettingsForm()}
                                            {this.buildUpdateDCVHostSettingsForm()}
                                            <Container
                                                header={
                                                    <Header
                                                        variant={"h2"}
                                                        actions={
                                                            <Button
                                                                iconName="edit"
                                                                onClick={() => {
                                                                    this.updateDCVSessionSettingsForm.current?.showModal();
                                                                }}
                                                            />
                                                        }
                                                    >
                                                        DCV Session
                                                    </Header>
                                                }
                                            >
                                                <ColumnLayout variant={"text-grid"} columns={3}>
                                                    <KeyValue title="Idle Timeout" value={dot.pick("dcv_session.idle_timeout", this.state.vdcSettings)} suffix={"minutes"} />
                                                    <KeyValue title="Idle Timeout Warning" value={dot.pick("dcv_session.idle_timeout_warning", this.state.vdcSettings)} suffix={"seconds"} />
                                                    <KeyValue title="CPU Utilization Threshold" value={dot.pick("dcv_session.cpu_utilization_threshold", this.state.vdcSettings)} suffix={"%"} />
                                                    <KeyValue title="Allowed Sessions Per User" value={dot.pick("dcv_session.allowed_sessions_per_user", this.state.vdcSettings)} />
                                                </ColumnLayout>
                                            </Container>
                                            <Container
                                                header={
                                                    <Header
                                                        variant={"h2"}
                                                        actions={
                                                            <Button
                                                                iconName="edit"
                                                                onClick={() => {
                                                                    this.updateDCVHostSettingsForm.current?.showModal();
                                                                }}
                                                            />
                                                        }
                                                    >
                                                        DCV Host
                                                    </Header>
                                                }
                                            >
                                                <ColumnLayout variant={"text-grid"} columns={2}>
                                                    <KeyValue title="Allowed Security Groups" value={dot.pick("dcv_session.additional_security_groups", this.state.vdcSettings)} />
                                                    <KeyValue title="Max Root Volume Size" value={dot.pick("dcv_session.max_root_volume_memory", this.state.vdcSettings)} suffix={"GB"} />
                                                    <KeyValue title="Allowed Instance Types" value={dot.pick("dcv_session.instance_types.allow", this.state.vdcSettings)} />
                                                    <KeyValue title="Denied Instance Types" value={dot.pick("dcv_session.instance_types.deny", this.state.vdcSettings)} />
                                                </ColumnLayout>
                                            </Container>
                                        </SpaceBetween>
                                    ),
                                },
                                {
                                    label: "Controller",
                                    id: "controller",
                                    content: (
                                        <SpaceBetween size={"m"}>
                                            <Container header={<Header variant={"h2"}>VDI Controller</Header>}>
                                                <ColumnLayout variant={"text-grid"} columns={3}>
                                                    <KeyValue title="Base OS" value={Utils.getOsTitle(dot.pick("controller.autoscaling.base_os", this.state.vdcSettings))} />
                                                    <KeyValue title="Instance Type" value={dot.pick("controller.autoscaling.instance_type", this.state.vdcSettings)} />
                                                    <KeyValue
                                                        title="Volume"
                                                        value={{
                                                            value: dot.pick("controller.autoscaling.volume_size", this.state.vdcSettings),
                                                            unit: "GB",
                                                        }}
                                                        type={"memory"}
                                                    />
                                                </ColumnLayout>
                                            </Container>
                                            {buildAutoScalingSettingContainer(dot.pick("controller", this.state.vdcSettings))}
                                        </SpaceBetween>
                                    ),
                                },
                                {
                                    label: "Broker",
                                    id: "broker",
                                    content: (
                                        <SpaceBetween size={"m"}>
                                            <Container header={<Header variant={"h2"}>NICE DCV Broker</Header>}>
                                                <ColumnLayout variant={"text-grid"} columns={3}>
                                                    <KeyValue title="Base OS" value={Utils.getOsTitle(dot.pick("dcv_broker.autoscaling.base_os", this.state.vdcSettings))} />
                                                    <KeyValue title="Instance Type" value={dot.pick("dcv_broker.autoscaling.instance_type", this.state.vdcSettings)} />
                                                    <KeyValue
                                                        title="Volume"
                                                        value={{
                                                            value: dot.pick("dcv_broker.autoscaling.volume_size", this.state.vdcSettings),
                                                            unit: "GB",
                                                        }}
                                                        type={"memory"}
                                                    />
                                                </ColumnLayout>
                                            </Container>
                                            {buildAutoScalingSettingContainer(dot.pick("dcv_broker", this.state.vdcSettings))}
                                            <Container header={<Header variant={"h2"}>Connection Details</Header>}>
                                                <ColumnLayout variant={"text-grid"} columns={3}>
                                                    <KeyValue title="Client Port" value={dot.pick("dcv_broker.client_communication_port", this.state.vdcSettings)} />
                                                    <KeyValue title="Agent Port" value={dot.pick("dcv_broker.agent_communication_port", this.state.vdcSettings)} />
                                                    <KeyValue title="Gateway Port" value={dot.pick("dcv_broker.gateway_communication_port", this.state.vdcSettings)} />
                                                    <KeyValue title="Client URL" value={`${getInternalALBUrl()}:${dot.pick("dcv_broker.client_communication_port", this.state.vdcSettings)}`} clipboard={true} />
                                                    <KeyValue title="Agent URL" value={`${getInternalALBUrl()}:${dot.pick("dcv_broker.agent_communication_port", this.state.vdcSettings)}`} clipboard={true} />
                                                    <KeyValue title="Gateway URL" value={`${getInternalALBUrl()}:${dot.pick("dcv_broker.gateway_communication_port", this.state.vdcSettings)}`} clipboard={true} />
                                                </ColumnLayout>
                                            </Container>
                                        </SpaceBetween>
                                    ),
                                },
                                {
                                    label: "Connection Gateway",
                                    id: "connection-gateway",
                                    content: (
                                        <SpaceBetween size={"m"}>
                                            <Container header={<Header variant={"h2"}>NICE DCV Connection Gateway</Header>}>
                                                <ColumnLayout variant={"text-grid"} columns={3}>
                                                    <KeyValue title="Base OS" value={Utils.getOsTitle(dot.pick("dcv_connection_gateway.autoscaling.base_os", this.state.vdcSettings))} />
                                                    <KeyValue title="Instance Type" value={dot.pick("dcv_connection_gateway.autoscaling.instance_type", this.state.vdcSettings)} />
                                                    <KeyValue
                                                        title="Volume"
                                                        value={{
                                                            value: dot.pick("dcv_connection_gateway.autoscaling.volume_size", this.state.vdcSettings),
                                                            unit: "GB",
                                                        }}
                                                        type={"memory"}
                                                    />
                                                </ColumnLayout>
                                            </Container>
                                            {buildAutoScalingSettingContainer(dot.pick("dcv_connection_gateway", this.state.vdcSettings))}
                                            <Container header={<Header variant={"h2"}>Certificate</Header>}>
                                                <ColumnLayout variant={"text-grid"} columns={isGatewayCertificateSelfSigned() ? 3 : 2}>
                                                    <KeyValue title="Type" value={isGatewayCertificateSelfSigned() ? "Self-Signed" : "Custom"} />
                                                    {!isGatewayCertificateSelfSigned() && <KeyValue title="Domain" value={dot.pick("dcv_connection_gateway.certificate.custom_dns_name", this.state.vdcSettings)} />}
                                                    <KeyValue title="Secret ARN" value={dot.pick("dcv_connection_gateway.certificate.certificate_secret_arn", this.state.vdcSettings)} clipboard={true} />
                                                    <KeyValue title="Private Key Secret ARN" value={dot.pick("dcv_connection_gateway.certificate.private_key_secret_arn", this.state.vdcSettings)} clipboard={true} />
                                                </ColumnLayout>
                                            </Container>
                                        </SpaceBetween>
                                    ),
                                },
                                {
                                    label: "Backup",
                                    id: "backups",
                                    content: (
                                        <SpaceBetween size={"l"}>
                                            <Container header={<Header variant={"h2"}>AWS Backup</Header>}>
                                                <ColumnLayout variant={"text-grid"} columns={2}>
                                                    <KeyValue title="Cluster" value={<EnabledDisabledStatusIndicator enabled={isClusterBackupEnabled()} />} type={"react-node"} />
                                                    <KeyValue title="VDI Host" value={<EnabledDisabledStatusIndicator enabled={isVDIBackupEnabled()} />} type={"react-node"} />
                                                </ColumnLayout>
                                            </Container>
                                            {isBackupEnabled() && (
                                                <Container header={<Header variant={"h2"}>Backup Plan</Header>}>
                                                    <ColumnLayout variant={"text-grid"} columns={2}>
                                                        <KeyValue title="ARN" value={dot.pick("vdi_host_backup.backup_plan.arn", this.state.vdcSettings)} clipboard={true} />
                                                        <KeyValue title="Selection" value={dot.pick("vdi_host_backup.backup_plan.selection.tags", this.state.vdcSettings)} />
                                                    </ColumnLayout>
                                                </Container>
                                            )}
                                        </SpaceBetween>
                                    ),
                                },
                                {
                                    label: "CloudWatch Logs",
                                    id: "cloudwatch-logs",
                                    content: (
                                        <Container header={<Header variant={"h2"}>CloudWatch Logs</Header>}>
                                            <ColumnLayout variant={"text-grid"} columns={3}>
                                                <KeyValue title="Status">
                                                    <EnabledDisabledStatusIndicator enabled={true} />
                                                </KeyValue>
                                                <KeyValue title="Force Flush Interval" value={5} suffix={"seconds"} />
                                                <KeyValue title="Log Retention" value={90} suffix={"days"} />
                                            </ColumnLayout>
                                        </Container>
                                    ),
                                },
                            ]}
                        />
                    </SpaceBetween>
                }
            />
        );
    }
}

export default withRouter(VirtualDesktopSettings);
