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

import { VirtualDesktopClient } from "../../../client";
import { VirtualDesktopSchedule, VirtualDesktopSession } from "../../../client/data-model";
import React, { Component } from "react";
import Utils from "../../../common/utils";
import "moment-timezone";
import moment from "moment";
import { AppContext } from "../../../common";
import { Box, Button, ButtonDropdown, ColumnLayout, Popover, SpaceBetween, StatusIndicator } from "@cloudscape-design/components";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faClock, faDownload, faExternalLinkAlt, faQuestionCircle } from "@fortawesome/free-solid-svg-icons";
import VirtualDesktopSessionStatusIndicator from "./virtual-desktop-session-status-indicator";
import { ButtonDropdownProps } from "@cloudscape-design/components/button-dropdown/interfaces";
import { KeyValue } from "../../../components/key-value";

interface VirtualDesktopSessionCardProps {
    virtualDesktopClient: VirtualDesktopClient;
    isSharedSession?: boolean;
    isActiveDirectory: boolean;
    session: VirtualDesktopSession;
    screenshot?: string;
    onMounted: () => void;
    onDeleteSession?: (session: VirtualDesktopSession) => Promise<boolean>;
    onStartSession?: (session: VirtualDesktopSession) => Promise<boolean>;
    onStopSession?: (session: VirtualDesktopSession) => Promise<boolean>;
    onRebootSession?: (session: VirtualDesktopSession) => Promise<boolean>;
    onDownloadDcvSessionFile: (session: VirtualDesktopSession) => Promise<boolean>;
    onLaunchSession: (session: VirtualDesktopSession) => Promise<boolean>;
    onUpdateSession?: (session: VirtualDesktopSession) => Promise<boolean>;
    onUpdateSessionPermission?: (session: VirtualDesktopSession) => Promise<boolean>;
    onConnectHelp: (session: VirtualDesktopSession) => Promise<boolean>;
    onShowSchedule?: (session: VirtualDesktopSession) => Promise<boolean>;
}

interface VirtualDesktopSessionCardState {
    view: string;
}

interface VirtualDesktopScheduleDescriptionProps {
    session: VirtualDesktopSession;
}

function VirtualDesktopScheduleDescription(props: VirtualDesktopScheduleDescriptionProps) {
    const day = moment().tz(AppContext.get().getClusterSettingsService().getClusterTimeZone()).day();
    let schedule;
    switch (day) {
        case 0:
            schedule = props.session.schedule?.sunday;
            break;
        case 1:
            schedule = props.session.schedule?.monday;
            break;
        case 2:
            schedule = props.session.schedule?.tuesday;
            break;
        case 3:
            schedule = props.session.schedule?.wednesday;
            break;
        case 4:
            schedule = props.session.schedule?.thursday;
            break;
        case 5:
            schedule = props.session.schedule?.friday;
            break;
        case 6:
            schedule = props.session.schedule?.saturday;
            break;
    }
    let label = "No Schedule";
    if (schedule) {
        if (schedule.schedule_type === "WORKING_HOURS") {
            label = "Working Hours";
        } else if (schedule.schedule_type === "STOP_ALL_DAY") {
            label = "Stopped All Day";
        } else if (schedule.schedule_type === "START_ALL_DAY") {
            label = "Running All Day";
        } else if (schedule.schedule_type === "CUSTOM_SCHEDULE") {
            label = `Custom Schedule - ${schedule.start_up_time} - ${schedule.shut_down_time}`;
        }
    }

    const getScheduleInfo = (schedule?: VirtualDesktopSchedule) => {
        if (typeof schedule === "undefined") {
            return "No Schedule";
        }
        switch (schedule.schedule_type!) {
            case "WORKING_HOURS":
                return "Working Hours";
            case "START_ALL_DAY":
                return "Running all day";
            case "STOP_ALL_DAY":
                return "Stopped all day";
            case "CUSTOM_SCHEDULE":
                return `${schedule.start_up_time} - ${schedule.shut_down_time}`;
        }
        return "No schedule";
    };

    return (
        <Popover
            dismissAriaLabel="Close"
            header={`Schedule Info`}
            content={
                <ColumnLayout columns={2}>
                    <KeyValue title={"Sunday"} value={getScheduleInfo(props.session.schedule?.sunday)} />
                    <KeyValue title={"Monday"} value={getScheduleInfo(props.session.schedule?.monday)} />
                    <KeyValue title={"Tuesday"} value={getScheduleInfo(props.session.schedule?.tuesday)} />
                    <KeyValue title={"Wednesday"} value={getScheduleInfo(props.session.schedule?.wednesday)} />
                    <KeyValue title={"Thursday"} value={getScheduleInfo(props.session.schedule?.thursday)} />
                    <KeyValue title={"Friday"} value={getScheduleInfo(props.session.schedule?.friday)} />
                    <KeyValue title={"Saturday"} value={getScheduleInfo(props.session.schedule?.saturday)} />
                </ColumnLayout>
            }
        >
            <small>{label}</small>
        </Popover>
    );
}

class VirtualDesktopSessionCard extends Component<VirtualDesktopSessionCardProps, VirtualDesktopSessionCardState> {
    constructor(props: VirtualDesktopSessionCardProps) {
        super(props);
        this.state = {
            view: "preview",
        };
    }

    componentDidMount() {
        this.props.onMounted();
    }

    getSession(): VirtualDesktopSession {
        return this.props.session;
    }

    canConnect = (): boolean => this.props.session.state === "READY";

    canDownloadDcvSessionFile = () => this.getSession().state === "READY";

    canUpdateSession = () => this.getSession().state === "STOPPED" || this.getSession().state === "STOPPED_IDLE";

    canUpdateSessionPermission = () => {
        if (this.getSession().base_os === "windows" && !this.props.isActiveDirectory) {
            return false;
        }
        return !(this.getSession().state === "DELETING" || this.getSession().state === "DELETED");
    };

    canReboot = () => this.getSession().state === "READY" || this.getSession().state === "ERROR";

    canStop = () => this.getSession().state === "READY";

    canDelete = () => {
        const status = this.getSession().state;
        return !!status;
    };

    canStart = () => this.getSession().state === "STOPPED" || this.getSession().state === "STOPPED_IDLE";

    hasSchedule = (): boolean => {
        const schedule = this.props.session.schedule;
        return Utils.isNotEmpty(schedule?.monday) || Utils.isNotEmpty(schedule?.tuesday) || Utils.isNotEmpty(schedule?.wednesday) || Utils.isNotEmpty(schedule?.thursday) || Utils.isNotEmpty(schedule?.friday) || Utils.isNotEmpty(schedule?.saturday) || Utils.isNotEmpty(schedule?.sunday);
    };

    buildHeader() {
        return (
            <SpaceBetween size="xs" direction="vertical">
                <div>
                    <Box float="left" variant="h3">
                        {this.props.session.name}
                        {this.props.isSharedSession && `: ${this.props.session.owner}`}
                    </Box>
                    <Box float="right">
                        <Button disabled={!this.canConnect()} onClick={() => this.props.onLaunchSession(this.getSession()).finally()} variant="link">
                            <FontAwesomeIcon icon={faExternalLinkAlt} /> Connect
                        </Button>
                    </Box>
                </div>
                <SpaceBetween size="s" direction={"horizontal"}>
                    <VirtualDesktopSessionStatusIndicator state={this.props.session.state!} hibernation_enabled={this.props.session.hibernation_enabled!} />
                    <small style={{ color: "grey" }}>{Utils.getOsTitle(this.props.session.software_stack?.base_os)}</small>
                    <small style={{ color: "grey" }}>{this.props.session.server?.instance_type}</small>
                    {this.hasSchedule() && (
                        <small style={{ color: "grey" }}>
                            <FontAwesomeIcon icon={faClock} />
                            &nbsp;{<VirtualDesktopScheduleDescription session={this.props.session} />}
                        </small>
                    )}
                </SpaceBetween>
            </SpaceBetween>
        );
    }

    getScreenshotImageUrl(): string {
        if (!this.props.screenshot) {
            return "";
        }
        return `data:image/jpeg;base64,${this.props.screenshot}`;
    }

    buildScreenShotImage() {
        const imageUrl = this.getScreenshotImageUrl();
        if (Utils.isEmpty(imageUrl)) {
            let display_message: string;
            let showSpinner = false;
            switch (this.getSession().state) {
                case "CREATING":
                    display_message = "Your session is being created ...";
                    break;
                case "INITIALIZING":
                    display_message = "Your session is initializing ...";
                    break;
                case "PROVISIONING":
                    display_message = "Your virtual desktop is being provisioned ...";
                    break;
                case "RESUMING":
                    display_message = "Your virtual desktop is resuming ...";
                    break;
                case "READY":
                    display_message = "Loading preview";
                    showSpinner = true;
                    break;
                default:
                    display_message = "No preview available.";
                    break;
            }
            if (showSpinner) {
                return (
                    <div className="virtual-desktop-placeholder-image">
                        <StatusIndicator type={"loading"} />
                    </div>
                );
            } else {
                return <div className="virtual-desktop-placeholder-image">{display_message}</div>;
            }
        } else {
            return (
                <div
                    onClick={() => {
                        if (this.canConnect()) {
                            this.props.onLaunchSession(this.getSession()).finally();
                        }
                    }}
                    style={{
                        cursor: "pointer",
                        backgroundImage: `url('${imageUrl}')`,
                        backgroundSize: "cover",
                        width: "100%",
                        height: "300px",
                    }}
                />
            );
        }
    }

    buildSessionInfo() {
        return (
            <Box padding={{ top: "xl", bottom: "xl" }}>
                <ul>
                    <li>
                        <strong>RES Session Id</strong> {this.getSession().idea_session_id}
                    </li>
                    <li>
                        <strong>DCV Session Id</strong> {this.getSession().dcv_session_id}
                    </li>
                    <li>
                        <strong>OS</strong> {Utils.getOsTitle(this.getSession().software_stack?.base_os)}
                    </li>
                    <li>
                        <strong>Session State</strong> {this.getSession().state}
                    </li>
                    <li>
                        <strong>Instance Type</strong> {this.getSession().server?.instance_type}
                    </li>
                    <li>
                        <strong>Private IP</strong> {this.getSession().server?.private_ip}{" "}
                    </li>
                    <li>
                        <strong>Instance AMI</strong> {this.getSession().software_stack?.ami_id}
                    </li>
                    <li>
                        <strong>Instance Id</strong> {this.getSession().server?.instance_id}
                    </li>
                    <li>
                        <strong>Created On</strong> {new Date(this.getSession().created_on!).toLocaleString()}
                    </li>
                </ul>
            </Box>
        );
    }

    buildActionDropDownItems(): ButtonDropdownProps.ItemOrGroup[] {
        let dropDownItems: ButtonDropdownProps.ItemOrGroup[] = [
            {
                id: "connect",
                text: "Connect",
                disabled: !this.canConnect(),
                href: "#",
                external: true,
            },
        ];

        if (!this.props.isSharedSession) {
            dropDownItems.push({
                id: "session-permissions",
                text: "Share Desktop",
                disabled: !this.canUpdateSessionPermission(),
                disabledReason: "Windows sessions support session sharing for active directory only",
            });
        }

        dropDownItems.push({
            id: "toggle-info",
            text: this.state.view === "info" ? "Show Preview" : "Show Info",
        });

        if (!this.props.isSharedSession) {
            dropDownItems.push({
                id: "schedule",
                text: "Schedule",
            });
            dropDownItems.push({
                id: "update-session",
                text: "Update",
                disabled: !this.canUpdateSession(),
                disabledReason: "Can only update session when it is in the Stopped state.",
            });
            dropDownItems.push({
                id: "states",
                text: "Change Desktop State",
                items: [
                    {
                        id: "start",
                        text: "Start",
                        disabled: !this.canStart(),
                    },
                    {
                        id: "stop",
                        text: this.getSession().hibernation_enabled ? "Hibernate" : "Stop",
                        disabled: !this.canStop(),
                    },
                    {
                        id: "reboot",
                        text: "Reboot",
                        disabled: !this.canReboot(),
                    },
                    {
                        id: "terminate",
                        text: "Terminate",
                        disabled: !this.canDelete(),
                    },
                ],
            });
        }
        return dropDownItems;
    }

    buildActions() {
        return (
            <div>
                <Box float="left">
                    <SpaceBetween size="xxxs" direction="horizontal">
                        <Button disabled={!this.canDownloadDcvSessionFile()} onClick={() => this.props.onDownloadDcvSessionFile(this.getSession()).finally()}>
                            <FontAwesomeIcon icon={faDownload} /> DCV Session File
                        </Button>
                        <Button variant="normal" onClick={() => this.props.onConnectHelp(this.getSession())}>
                            <FontAwesomeIcon icon={faQuestionCircle} />
                        </Button>
                    </SpaceBetween>
                </Box>
                <Box float="right">
                    <SpaceBetween size="xs" direction="horizontal">
                        <ButtonDropdown
                            onItemClick={(event) => {
                                if (event.detail.id === "terminate") {
                                    if (this.props.onDeleteSession) {
                                        this.props.onDeleteSession(this.getSession()).finally();
                                    }
                                } else if (event.detail.id === "connect") {
                                    event.preventDefault();
                                    this.props.onLaunchSession(this.getSession()).finally();
                                } else if (event.detail.id === "stop") {
                                    if (this.props.onStopSession) {
                                        this.props.onStopSession(this.getSession()).finally();
                                    }
                                } else if (event.detail.id === "start") {
                                    if (this.props.onStartSession) {
                                        this.props.onStartSession(this.getSession()).finally();
                                    }
                                } else if (event.detail.id === "reboot") {
                                    if (this.props.onRebootSession) {
                                        this.props.onRebootSession(this.getSession()).finally();
                                    }
                                } else if (event.detail.id === "toggle-info") {
                                    if (this.state.view === "info") {
                                        this.setState({
                                            view: "preview",
                                        });
                                    } else {
                                        this.setState({
                                            view: "info",
                                        });
                                    }
                                } else if (event.detail.id === "schedule") {
                                    if (this.props.onShowSchedule) {
                                        this.props.onShowSchedule(this.getSession()).finally();
                                    }
                                } else if (event.detail.id === "update-session") {
                                    if (this.props.onUpdateSession) {
                                        this.props.onUpdateSession(this.getSession()).finally();
                                    }
                                } else if (event.detail.id === "session-permissions") {
                                    if (this.props.onUpdateSessionPermission) {
                                        this.props.onUpdateSessionPermission(this.getSession()).finally();
                                    }
                                }
                            }}
                            items={this.buildActionDropDownItems()}
                            expandableGroups
                        >
                            Actions
                        </ButtonDropdown>
                    </SpaceBetween>
                </Box>
            </div>
        );
    }

    render() {
        return (
            <SpaceBetween direction="vertical" size="xs">
                {this.buildHeader()}
                {this.state.view === "preview" && this.buildScreenShotImage()}
                {this.state.view === "info" && this.buildSessionInfo()}
                {this.buildActions()}
            </SpaceBetween>
        );
    }
}

export default VirtualDesktopSessionCard;
