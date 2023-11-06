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

// Schedule Modal
import { VirtualDesktopSchedule, VirtualDesktopSession, VirtualDesktopWeekSchedule } from "../../../client/data-model";
import React, { Component, RefObject } from "react";
import IdeaTimeRangeSlider from "../../../components/time-range-slider";
import { IdeaFormField } from "../../../components/form-field";
import moment from "moment";
import { Alert, Box, Button, ColumnLayout, Form, Header, Modal, SpaceBetween } from "@cloudscape-design/components";
import { AppContext } from "../../../common";

// Day Of Week Schedule Component

interface VirtualDesktopDayOfWeekScheduleProps {
    dayOfWeek: string;
    schedule?: VirtualDesktopSchedule;
    working_hours_start: string;
    working_hours_end: string;
}

interface VirtualDesktopDayOfWeekScheduleState {
    schedule: VirtualDesktopSchedule;
}

class VirtualDesktopDayOfWeekSchedule extends Component<VirtualDesktopDayOfWeekScheduleProps, VirtualDesktopDayOfWeekScheduleState> {
    timeRangeSlider: RefObject<IdeaTimeRangeSlider>;

    constructor(props: VirtualDesktopDayOfWeekScheduleProps) {
        super(props);
        this.timeRangeSlider = React.createRef();
        this.state = {
            schedule:
                this.props.schedule && this.props.schedule.schedule_type
                    ? this.props.schedule
                    : {
                          schedule_type: "NO_SCHEDULE",
                      },
        };
    }

    getTimeRangeSlider(): IdeaTimeRangeSlider | null {
        if (this.state.schedule.schedule_type === "CUSTOM_SCHEDULE") {
            return this.timeRangeSlider.current!;
        }
        return null;
    }

    getValue(): VirtualDesktopSchedule {
        if (this.state.schedule.schedule_type === "CUSTOM_SCHEDULE") {
            return {
                schedule_type: "CUSTOM_SCHEDULE",
                start_up_time: this.getTimeRangeSlider()!.getStartTime(),
                shut_down_time: this.getTimeRangeSlider()!.getEndTime(),
            };
        } else {
            return {
                schedule_type: this.state.schedule.schedule_type,
            };
        }
    }

    render() {
        return (
            <div>
                <IdeaFormField
                    module={"dayOfWeek"}
                    param={{
                        name: "schedule_type",
                        title: this.props.dayOfWeek,
                        param_type: "select",
                        data_type: "str",
                        default: this.state.schedule.schedule_type,
                        choices: [
                            {
                                title: "Working Hours (" + this.props.working_hours_start + " - " + this.props.working_hours_end + ")",
                                value: "WORKING_HOURS",
                            },
                            {
                                title: "Stop All Day",
                                value: "STOP_ALL_DAY",
                            },
                            {
                                title: "Start All Day",
                                value: "START_ALL_DAY",
                            },
                            {
                                title: "Custom Schedule",
                                value: "CUSTOM_SCHEDULE",
                            },
                            {
                                title: "No Schedule",
                                value: "NO_SCHEDULE",
                            },
                        ],
                    }}
                    onStateChange={(event) => {
                        this.setState({
                            schedule: {
                                schedule_type: event.value,
                            },
                        });
                    }}
                />
                {this.state.schedule.schedule_type === "CUSTOM_SCHEDULE" && <IdeaTimeRangeSlider ref={this.timeRangeSlider} startTime={this.state.schedule.start_up_time ? this.state.schedule.start_up_time : "09:00"} endTime={this.state.schedule.shut_down_time ? this.state.schedule.shut_down_time : "18:00"} />}
            </div>
        );
    }
}

interface VirtualDesktopScheduleModalProps {
    onScheduleChange: (session: VirtualDesktopSession) => Promise<boolean>;
}

interface VirtualDesktopScheduleModalState {
    visible: boolean;
    session: VirtualDesktopSession | null;
    errorMessage: string | null;
    saveLoading: boolean;
    currentTime: any;
    working_hours_start: string;
    working_hours_end: string;
}

class VirtualDesktopScheduleModal extends Component<VirtualDesktopScheduleModalProps, VirtualDesktopScheduleModalState> {
    mondaySchedule: RefObject<VirtualDesktopDayOfWeekSchedule>;
    tuesdaySchedule: RefObject<VirtualDesktopDayOfWeekSchedule>;
    wednesdaySchedule: RefObject<VirtualDesktopDayOfWeekSchedule>;
    thursdaySchedule: RefObject<VirtualDesktopDayOfWeekSchedule>;
    fridaySchedule: RefObject<VirtualDesktopDayOfWeekSchedule>;
    saturdaySchedule: RefObject<VirtualDesktopDayOfWeekSchedule>;
    sundaySchedule: RefObject<VirtualDesktopDayOfWeekSchedule>;

    clockInterval: any;

    constructor(props: VirtualDesktopScheduleModalProps) {
        super(props);

        this.mondaySchedule = React.createRef();
        this.tuesdaySchedule = React.createRef();
        this.wednesdaySchedule = React.createRef();
        this.thursdaySchedule = React.createRef();
        this.fridaySchedule = React.createRef();
        this.saturdaySchedule = React.createRef();
        this.sundaySchedule = React.createRef();

        this.state = {
            visible: false,
            session: null,
            errorMessage: null,
            saveLoading: false,
            currentTime: null,
            working_hours_start: "",
            working_hours_end: "",
        };
    }

    componentDidMount() {
        AppContext.get()
            .getClusterSettingsService()
            .getVirtualDesktopSettings()
            .then((settings) => {
                this.setState({
                    working_hours_start: settings.dcv_session.working_hours.start_up_time,
                    working_hours_end: settings.dcv_session.working_hours.shut_down_time,
                });
            });
        this.clockInterval = setInterval(() => {
            this.setState({
                currentTime: moment(),
            });
        }, 1000);
    }

    componentWillUnmount() {
        clearInterval(this.clockInterval);
    }

    showSchedule(session: VirtualDesktopSession) {
        this.setState({
            visible: true,
            session: session,
        });
    }

    cancel() {
        this.setState({
            visible: false,
            session: null,
            errorMessage: null,
            saveLoading: false,
        });
    }

    save() {
        if (this.state.session) {
            let weekSchedule: VirtualDesktopWeekSchedule = {
                monday: this.mondaySchedule.current!.getValue(),
                tuesday: this.tuesdaySchedule.current!.getValue(),
                wednesday: this.wednesdaySchedule.current!.getValue(),
                thursday: this.thursdaySchedule.current!.getValue(),
                friday: this.fridaySchedule.current!.getValue(),
                saturday: this.saturdaySchedule.current!.getValue(),
                sunday: this.sundaySchedule.current!.getValue(),
            };
            this.setState(
                {
                    errorMessage: null,
                    session: {
                        ...this.state.session,
                        schedule: weekSchedule,
                    },
                    saveLoading: true,
                },
                () => {
                    this.props.onScheduleChange(this.state.session!).then((status) => {
                        if (status) {
                            this.cancel();
                        } else {
                            this.setState({
                                saveLoading: false,
                            });
                        }
                    });
                }
            );
        }
    }

    setErrorMessage(message: string) {
        this.setState({
            errorMessage: message,
        });
    }

    render() {
        return (
            this.state.visible && (
                <Modal
                    visible={true}
                    size="medium"
                    onDismiss={() => {
                        this.cancel();
                    }}
                    header={
                        <Header variant="h3" description="Setup a schedule to start/stop your virtual desktop to save and manage costs. The schedule operates at the cluster timezone setup by your cluster administrator.">
                            Schedule for {this.state.session?.name}
                        </Header>
                    }
                    footer={
                        <Box float="right">
                            <SpaceBetween size="xs" direction="horizontal">
                                <Button disabled={this.state.saveLoading} onClick={() => this.cancel()}>
                                    Cancel
                                </Button>
                                <Button loading={this.state.saveLoading} variant="primary" onClick={() => this.save()}>
                                    Save
                                </Button>
                            </SpaceBetween>
                        </Box>
                    }
                >
                    <SpaceBetween size={"m"}>
                        <Alert>
                            <strong>
                                Cluster Time: {this.state.currentTime.tz(AppContext.get().getClusterSettingsService().getClusterTimeZone()).format("LLL")} ({AppContext.get().getClusterSettingsService().getClusterTimeZone()})
                            </strong>
                            <br />
                        </Alert>
                        <Form errorText={this.state.errorMessage}>
                            <ColumnLayout columns={1}>
                                <VirtualDesktopDayOfWeekSchedule ref={this.mondaySchedule} dayOfWeek="Monday" schedule={this.state.session?.schedule?.monday} working_hours_start={this.state.working_hours_start} working_hours_end={this.state.working_hours_end} />
                                <VirtualDesktopDayOfWeekSchedule ref={this.tuesdaySchedule} dayOfWeek="Tuesday" schedule={this.state.session?.schedule?.tuesday} working_hours_start={this.state.working_hours_start} working_hours_end={this.state.working_hours_end} />
                                <VirtualDesktopDayOfWeekSchedule ref={this.wednesdaySchedule} dayOfWeek="Wednesday" schedule={this.state.session?.schedule?.wednesday} working_hours_start={this.state.working_hours_start} working_hours_end={this.state.working_hours_end} />
                                <VirtualDesktopDayOfWeekSchedule ref={this.thursdaySchedule} dayOfWeek="Thursday" schedule={this.state.session?.schedule?.thursday} working_hours_start={this.state.working_hours_start} working_hours_end={this.state.working_hours_end} />
                                <VirtualDesktopDayOfWeekSchedule ref={this.fridaySchedule} dayOfWeek="Friday" schedule={this.state.session?.schedule?.friday} working_hours_start={this.state.working_hours_start} working_hours_end={this.state.working_hours_end} />
                                <VirtualDesktopDayOfWeekSchedule ref={this.saturdaySchedule} dayOfWeek="Saturday" schedule={this.state.session?.schedule?.saturday} working_hours_start={this.state.working_hours_start} working_hours_end={this.state.working_hours_end} />
                                <VirtualDesktopDayOfWeekSchedule ref={this.sundaySchedule} dayOfWeek="Sunday" schedule={this.state.session?.schedule?.sunday} working_hours_start={this.state.working_hours_start} working_hours_end={this.state.working_hours_end} />
                            </ColumnLayout>
                        </Form>
                    </SpaceBetween>
                </Modal>
            )
        );
    }
}

export default VirtualDesktopScheduleModal;
