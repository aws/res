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

import React, { Component } from "react";
import { IdeaAppLayoutProps } from "../../components/app-layout";
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import { ColumnLayout, Container, Grid, Header, SpaceBetween, Tabs } from "@cloudscape-design/components";
import IdeaAppLayout from "../../components/app-layout/app-layout";
import { KeyValue } from "../../components/key-value";
import { AppContext } from "../../common";
import { VirtualDesktopSession, VirtualDesktopSessionPermission } from "../../client/data-model";
import VirtualDesktopSessionStatusIndicator from "./components/virtual-desktop-session-status-indicator";
import Utils from "../../common/utils";
import dot from "dot-object";
import { withRouter } from "../../navigation/navigation-utils";

export interface VirtualDesktopSessionDetailProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {}

interface VirtualDesktopSessionDetailState {
    session: VirtualDesktopSession;
    sessionPermissions: VirtualDesktopSessionPermission[];
    activeTabId: string;
    workingHours: {
        start: string;
        end: string;
    };
}

const DEFAULT_ACTIVE_TAB_ID = "details";

class VirtualDesktopSessionDetail extends Component<VirtualDesktopSessionDetailProps, VirtualDesktopSessionDetailState> {
    constructor(props: VirtualDesktopSessionDetailProps) {
        super(props);
        this.state = {
            session: {},
            sessionPermissions: [],
            activeTabId: DEFAULT_ACTIVE_TAB_ID,
            workingHours: {
                start: "",
                end: "",
            },
        };
    }

    getIdeaSessionId(): string {
        return this.props.params.idea_session_id;
    }

    getSessionOwner(): string {
        let owner = this.props.searchParams.get("owner");
        if (owner) {
            return owner;
        }
        return AppContext.get().auth().getUsername();
    }

    componentDidMount() {
        AppContext.get()
            .getClusterSettingsService()
            .getVirtualDesktopSettings()
            .then((settings) => {
                const queryParams = new URLSearchParams(this.props.location.search);
                this.setState({
                    workingHours: {
                        start: dot.pick("dcv_session.working_hours.start_up_time", settings),
                        end: dot.pick("dcv_session.working_hours.shut_down_time", settings),
                    },
                    activeTabId: Utils.asString(queryParams.get("tab"), DEFAULT_ACTIVE_TAB_ID),
                });
            });

        AppContext.get()
            .client()
            .virtualDesktopAdmin()
            .getSessionInfo({
                session: {
                    idea_session_id: this.getIdeaSessionId(),
                    owner: this.getSessionOwner(),
                },
            })
            .then((result) => {
                this.setState({
                    session: result.session!,
                });
            });

        AppContext.get()
            .client()
            .virtualDesktopAdmin()
            .listSessionPermissions({
                idea_session_id: this.getIdeaSessionId(),
            })
            .then((response) => {
                this.setState({
                    sessionPermissions: response.listing!,
                });
            });
    }

    buildPermissionTab() {
        if (Utils.isEmpty(this.state.sessionPermissions)) {
            return <p> None </p>;
        } else {
            this.state.sessionPermissions.map((permission) => {
                return (
                    <Grid gridDefinition={[{ colspan: 4 }, { colspan: 4 }, { colspan: 4 }]}>
                        <KeyValue title={"Actor"} value={permission.actor_name} />
                        <KeyValue title={"Desktop Shared Setting"} value={permission.permission_profile?.profile_id} />
                        <KeyValue title={"Expiry"} value={permission.expiry_date} type={"date"} />
                    </Grid>
                );
            });
        }
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
                sideNavActivePath={"/virtual-desktop/sessions"}
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
                        text: "Sessions",
                        href: "#/virtual-desktop/sessions",
                    },
                    {
                        text: this.getIdeaSessionId(),
                        href: "",
                    },
                ]}
                header={<Header variant={"h1"}>Session: {this.state.session.name}</Header>}
                contentType={"default"}
                content={
                    <SpaceBetween size={"l"}>
                        <Container header={<Header variant={"h2"}>General Information</Header>}>
                            <ColumnLayout variant={"text-grid"} columns={3}>
                                <KeyValue title="Session Name" value={this.state.session.name} />
                                <KeyValue title="Owner" value={this.state.session.owner} />
                                <KeyValue title="State" value={<VirtualDesktopSessionStatusIndicator state={this.state.session.state!} hibernation_enabled={this.state.session.hibernation_enabled!} />} type="react-node" />
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
                                    label: "Details",
                                    id: "details",
                                    content: (
                                        <Container header={<Header variant={"h2"}>Session Details</Header>}>
                                            <ColumnLayout columns={3} variant={"text-grid"}>
                                                <KeyValue title="RES Session ID" value={this.state.session.idea_session_id} clipboard={true} />
                                                <KeyValue title="DCV Session ID" value={this.state.session.dcv_session_id} clipboard={true} />
                                                <KeyValue title="Description" value={this.state.session.description} />
                                                <KeyValue title="Session Type" value={this.state.session.type} />
                                                <KeyValue title="Hibernation Enabled" value={this.state.session.hibernation_enabled} type="boolean" />
                                                <KeyValue title="Created On" value={this.state.session.created_on} type="date" />
                                                <KeyValue title="Updated On" value={this.state.session.updated_on} type="date" />
                                            </ColumnLayout>
                                        </Container>
                                    ),
                                },
                                {
                                    label: "Server",
                                    id: "server",
                                    content: (
                                        <Container header={<Header variant={"h2"}>Server</Header>}>
                                            <ColumnLayout columns={3} variant={"text-grid"}>
                                                <KeyValue title="Instance ID" value={this.state.session.server?.instance_id} type={"ec2:instance-id"} />
                                                <KeyValue title="Private IP" value={this.state.session.server?.private_ip} clipboard={true} />
                                                <KeyValue title="Instance Type" value={this.state.session.server?.instance_type} />
                                            </ColumnLayout>
                                        </Container>
                                    ),
                                },
                                {
                                    label: "Software Stack",
                                    id: "software-stack",
                                    content: (
                                        <Container header={<Header variant={"h2"}>Software Stack</Header>}>
                                            <ColumnLayout columns={3} variant={"text-grid"}>
                                                <KeyValue title="Name" value={this.state.session.software_stack?.name} />
                                                <KeyValue title="Software Stack ID" value={this.state.session.software_stack?.stack_id} clipboard={true} />
                                                <KeyValue title="Base OS" value={Utils.getOsTitle(this.state.session.software_stack?.base_os)} />
                                                <KeyValue title="AMI ID" value={this.state.session.software_stack?.ami_id} clipboard={true} />
                                                <KeyValue title="Minimum Storage Size" value={this.state.session.software_stack?.min_storage} type="memory" />
                                                <KeyValue title="Architecture" value={this.state.session.software_stack?.architecture} />
                                                <KeyValue title="GPU" value={this.state.session.software_stack?.gpu?.replaceAll("_", " ")} />
                                            </ColumnLayout>
                                        </Container>
                                    ),
                                },
                                {
                                    label: "Project",
                                    id: "project",
                                    content: (
                                        <Container header={<Header variant={"h2"}>Project</Header>}>
                                            <ColumnLayout columns={3} variant={"text-grid"}>
                                                <KeyValue title="ID" value={this.state.session.project?.project_id} />
                                                <KeyValue title="Code" value={this.state.session.project?.name} />
                                                <KeyValue title="Title" value={this.state.session.project?.title} />
                                            </ColumnLayout>
                                        </Container>
                                    ),
                                },
                                {
                                    label: "Permissions",
                                    id: "permissions",
                                    content: (
                                        <Container header={<Header variant={"h2"}>Permissions</Header>}>
                                            <SpaceBetween size={"xl"}>{this.buildPermissionTab()}</SpaceBetween>
                                        </Container>
                                    ),
                                },
                                {
                                    label: "Schedule",
                                    id: "schedule",
                                    content: (
                                        <Container header={<Header variant={"h2"}>Schedule</Header>}>
                                            <ColumnLayout columns={3} variant={"text-grid"}>
                                                <KeyValue title="Monday" value={Utils.getScheduleDisplay(this.state.session.schedule?.monday, this.state.workingHours.start, this.state.workingHours.end)} />
                                                <KeyValue title="Tuesday" value={Utils.getScheduleDisplay(this.state.session.schedule?.tuesday, this.state.workingHours.start, this.state.workingHours.end)} />
                                                <KeyValue title="Wednesday" value={Utils.getScheduleDisplay(this.state.session.schedule?.wednesday, this.state.workingHours.start, this.state.workingHours.end)} />
                                                <KeyValue title="Thursday" value={Utils.getScheduleDisplay(this.state.session.schedule?.thursday, this.state.workingHours.start, this.state.workingHours.end)} />
                                                <KeyValue title="Friday" value={Utils.getScheduleDisplay(this.state.session.schedule?.friday, this.state.workingHours.start, this.state.workingHours.end)} />
                                                <KeyValue title="Saturday" value={Utils.getScheduleDisplay(this.state.session.schedule?.saturday, this.state.workingHours.start, this.state.workingHours.end)} />
                                                <KeyValue title="Sunday" value={Utils.getScheduleDisplay(this.state.session.schedule?.sunday, this.state.workingHours.start, this.state.workingHours.end)} />
                                            </ColumnLayout>
                                        </Container>
                                    ),
                                },
                                {
                                    label: "Monitoring",
                                    id: "monitoring",
                                    content: (
                                        <Container header={<Header variant={"h2"}>Monitoring (Coming Soon)</Header>}>
                                            <li>
                                                eVDI Session <u>detailed</u> monitoring needs <b>Metrics and Monitoring</b> module to be enabled.
                                            </li>
                                            <li>
                                                If <b>Metrics and Monitoring</b> is enabled, metrics collected via CloudWatch or Prometheus will be queried and rendered.
                                            </li>
                                            <li>
                                                If <b>Metrics and Monitoring</b> is not enabled, default EC2 Instance metrics available from CloudWatch will be rendered.
                                            </li>
                                        </Container>
                                    ),
                                },
                                {
                                    label: "Session Health",
                                    id: "session-health",
                                    disabled: this.state.session.state !== "READY",
                                    content: (
                                        <Container header={<Header variant={"h2"}>Session Health (Coming Soon)</Header>}>
                                            <li>Additional eVDI Session information from NICE DCV Broker will be displayed.</li>
                                        </Container>
                                    ),
                                },
                                {
                                    label: "Cost Estimates",
                                    id: "cost-estimates",
                                    content: (
                                        <Container header={<Header variant={"h2"}>Cost Estimates (Coming Soon)</Header>}>
                                            <li>eVDI Session cost estimates based on EC2 Instance Type, Usage and Capacity Type will be provided.</li>
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

export default withRouter(VirtualDesktopSessionDetail);
