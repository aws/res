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

enum DaysOfWeek {
    MONDAY = 'Monday',
    TUESDAY = 'Tuesday', 
    WEDNESDAY = 'Wednesday',
    THURSDAY = 'Thursday',
    FRIDAY = 'Friday',
    SATURDAY = 'Saturday',
    SUNDAY = 'Sunday'
}

// Day Of Week Schedule Component

interface VirtualDesktopDayOfWeekScheduleProps {
    dayOfWeek: string;
    schedule?: any;
    working_hours_start: string;
    working_hours_end: string;
    modalType: string;
}

interface VirtualDesktopDayOfWeekScheduleState {
    schedule: VirtualDesktopSchedule;
}

class VirtualDesktopDayOfWeekSchedule extends Component<VirtualDesktopDayOfWeekScheduleProps, VirtualDesktopDayOfWeekScheduleState> {
    timeRangeSlider: RefObject<IdeaTimeRangeSlider>;

    constructor(props: VirtualDesktopDayOfWeekScheduleProps) {
        super(props);
        this.timeRangeSlider = React.createRef();
        if (props.modalType === "default") {
            this.state = {
	             schedule: this.props.schedule
	                 ? {
	                       schedule_type: this.props.schedule.type || this.props.schedule.schedule_type || "NO_SCHEDULE",
	                       start_up_time: this.props.schedule.start_up_time,
	                       shut_down_time: this.props.schedule.shut_down_time,
	                   }
	                 : {
	                       schedule_type: "NO_SCHEDULE",
	                   },
	         };
            return
        }
       
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
    onScheduleChange: (item: VirtualDesktopSession | any) => Promise<boolean>;
    modalType: string;
    start_up_time?: string;
    shut_down_time?: string;
}   

interface VirtualDesktopScheduleModalState {
    visible: boolean;
    session: VirtualDesktopSession | null;
    errorMessage: string | null;
    saveLoading: boolean;
    currentTime: any;
    working_hours_start: string;
    working_hours_end: string;
    modalType: string;
    defaultSchedule: any | null;
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
            modalType: props.modalType,
            visible: false,
            session: null,
            errorMessage: null,
            saveLoading: false,
            currentTime: null,
            working_hours_start: "",
            working_hours_end: "",
            defaultSchedule: null,
        };
    }

    async resetModal() {
         if (this.state.modalType === "session") {
            AppContext.get()
            .getClusterSettingsService()
            .getVirtualDesktopSettings()
            .then((settings) => {
                this.setState({
                    working_hours_start: settings.dcv_session.working_hours.start_up_time,
                    working_hours_end: settings.dcv_session.working_hours.shut_down_time,
                    defaultSchedule: settings.dcv_session.schedule,
                });
            });
             
        } else if (this.state.modalType === "default") {
            AppContext.get()
            .getClusterSettingsService()
            .getVirtualDesktopSettings()
            .then((settings) => {
                this.setState({
                    visible: false,
                    working_hours_start: settings.dcv_session.working_hours.start_up_time,
                    working_hours_end: settings.dcv_session.working_hours.shut_down_time,
                    defaultSchedule: settings.dcv_session.schedule,
                });
            });
        }
        
        this.clockInterval = setInterval(() => {
            this.setState({
                currentTime: moment(),
            });
        }, 1000);   
    }        
   
    componentDidMount() {
       this.resetModal()
    }

    componentWillUnmount() {
        clearInterval(this.clockInterval);
    }

    async showSchedule(item: VirtualDesktopSession | VirtualDesktopWeekSchedule) {
        await this.resetModal();

        if (this.state.modalType === "session") {
            this.setState({
                visible: true,
                session: item as VirtualDesktopSession,
            });
        } 
        if (this.state.modalType === "default") {
            this.setState({
                visible: true,
                defaultSchedule: item as VirtualDesktopWeekSchedule || null,
            });
        }
    }

    cancel() {
        this.setState({
            visible: false,
            session: null,
            errorMessage: null,
            saveLoading: false,
        });
    }

    saveDefaultSchedule(weekSchedule: VirtualDesktopWeekSchedule) {
        this.setState(
            {
                errorMessage: null,
                saveLoading: true,
            },
            () => {
                this.props.onScheduleChange(weekSchedule as any).then((status) => {
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

    saveSessionSchedule(weekSchedule: VirtualDesktopWeekSchedule) {
         if (this.state.session) {
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

    save() {
        let weekSchedule: VirtualDesktopWeekSchedule = {
                monday: this.mondaySchedule.current!.getValue(),
                tuesday: this.tuesdaySchedule.current!.getValue(),
                wednesday: this.wednesdaySchedule.current!.getValue(),
                thursday: this.thursdaySchedule.current!.getValue(),
                friday: this.fridaySchedule.current!.getValue(),
                saturday: this.saturdaySchedule.current!.getValue(),
                sunday: this.sundaySchedule.current!.getValue(),
       };
       if (this.state.modalType === "session") {
            this.saveSessionSchedule(weekSchedule)
       }
       if (this.state.modalType === "default") {
            this.saveDefaultSchedule(weekSchedule)
       }
    }

    async resetToDefault() {
        if (this.state.modalType === "session" && this.state.defaultSchedule && this.state.session) {
            const settings = await AppContext.get()
                .getClusterSettingsService()
                .getVirtualDesktopSettings();
            
            const transformSchedule = (schedule: any): VirtualDesktopWeekSchedule => {
                const transformed: any = {};
                Object.keys(schedule).forEach(day => {
                    const daySchedule = schedule[day];
                    const scheduleEntry: any = {
                        schedule_type: daySchedule.type || daySchedule.schedule_type,
                    };
                    if (daySchedule.start_up_time) {
                        scheduleEntry.start_up_time = daySchedule.start_up_time;
                    }
                    if (daySchedule.shut_down_time) {
                        scheduleEntry.shut_down_time = daySchedule.shut_down_time;
                    }
                    transformed[day] = scheduleEntry;
                });
                return transformed;
            };
            
            const transformed = transformSchedule(settings.dcv_session.schedule);
            
            this.setState({
                session: {
                    ...this.state.session,
                    schedule: transformed,
                },
            })
        }
    }

    setErrorMessage(message: string) {
        this.setState({
            errorMessage: message,
        });
    }

    renderDaySchedules() {
        const days = Object.values(DaysOfWeek);
        const refs = [this.mondaySchedule, this.tuesdaySchedule, this.wednesdaySchedule, 
                    this.thursdaySchedule, this.fridaySchedule, this.saturdaySchedule, this.sundaySchedule];
        
        const scheduleData = this.state.modalType === "session" 
            ? this.state.session?.schedule
            : this.state.defaultSchedule;

        return (
            <ColumnLayout columns={1}>
                {days.map((day, index) => (
                    <VirtualDesktopDayOfWeekSchedule 
                        key={`${day}-${JSON.stringify(scheduleData?.[day.toLowerCase()])}`}
                        modalType={this.state.modalType}
                        ref={refs[index]}
                        dayOfWeek={day}
                        schedule={scheduleData?.[day.toLowerCase()]}
                        working_hours_start={this.state.working_hours_start}
                        working_hours_end={this.state.working_hours_end}
                    />
                ))}
            </ColumnLayout>
        );
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
                            {this.state.session?.name ? `Schedule for ${this.state.session.name}` : "Default Schedule"}
                        </Header>
                    }
                    footer={
                        <Box>
                            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                <div>
                                    {this.state.modalType === "session" && this.state.defaultSchedule && (
                                        <Button loading={this.state.saveLoading} onClick={() => this.resetToDefault()}>
                                            Reset
                                        </Button>
                                    )}  
                                </div>
                                <SpaceBetween size="xs" direction="horizontal">
                                    <Button disabled={this.state.saveLoading} onClick={() => this.cancel()}>
                                        Cancel
                                    </Button>
                                    <Button loading={this.state.saveLoading} variant="primary" onClick={() => this.save()}>
                                        Save
                                    </Button>
                                </SpaceBetween>
                            </div>
                        </Box>
                    }
                >
                    <SpaceBetween size={"m"}>
                        <Alert>
                            {this.state.currentTime ? (
                                <strong>
                                    Cluster Time: {this.state.currentTime.tz(AppContext.get().getClusterSettingsService().getClusterTimeZone()).format("LLL")} ({AppContext.get().getClusterSettingsService().getClusterTimeZone()})
                                </strong>
                            ) : (
                                <strong/>
                            )}
                            <br />
                        </Alert>
                        <Form errorText={this.state.errorMessage}>
                            {this.renderDaySchedules()}
                        </Form>
                    </SpaceBetween>
                </Modal>
            )
        );
    }
}

export default VirtualDesktopScheduleModal;
