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
import IdeaTimeRangeSlider from "../../../components/time-range-slider";
import moment from "moment";
import { Alert, Box, Button, ColumnLayout, Form, Header, Modal, SpaceBetween } from "@cloudscape-design/components";
import { AppContext } from "../../../common";

interface WorkingHoursModalProps {
    onWorkingHoursChange: (workingHour: any) => Promise<boolean>;
}

interface VirtualDesktopScheduleModalState {
    visible: boolean;
    errorMessage: string | null;
    saveLoading: boolean;
    currentTime: any;
    working_hours_start: string;
    working_hours_end: string;
}

class WorkingHoursModal extends Component<WorkingHoursModalProps, VirtualDesktopScheduleModalState> {
    timeRangeSlider: RefObject<IdeaTimeRangeSlider>;

    clockInterval: any;

    constructor(props: WorkingHoursModalProps) {
        super(props);
        this.timeRangeSlider = React.createRef();

        this.state = {
            visible: false,
            errorMessage: null,
            saveLoading: false,
            currentTime: null,
            working_hours_start: "",
            working_hours_end: "",
        };
    }

    componentDidMount() {
        this.clockInterval = setInterval(() => {
            this.setState({
                currentTime: moment(),
            });
        }, 1000);
        AppContext.get()
            .getClusterSettingsService()
            .getVirtualDesktopSettings()
            .then((settings) => {
                this.setState({
                    visible: false,
                    working_hours_start: settings.dcv_session.working_hours.start_up_time,
                    working_hours_end: settings.dcv_session.working_hours.shut_down_time,
                });
            });
    }

    componentWillUnmount() {
        clearInterval(this.clockInterval);
    }

    showSchedule() {
        this.setState({
            visible: true
        });
    }

    cancel() {
        this.setState({
            visible: false,
            errorMessage: null,
            saveLoading: false,
        });
    }

    save() {
        let workingHours = {
            working_hours_start: this.timeRangeSlider.current!.getStartTime(),
            working_hours_end: this.timeRangeSlider.current!.getEndTime()
        }

        this.setState(
            {
                errorMessage: null,
                saveLoading: true,
            },
            () => {
                this.props.onWorkingHoursChange(workingHours)
            }
        );
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
                        <Header variant="h3" description="Setup a working hours default schedule to save and manage costs. The working hours operate at the cluster timezone setup by your cluster administrator.">
                            Working Hours
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
                        <Form errorText={this.state.errorMessage}>
                            <ColumnLayout columns={1}>
                                <Alert>
                                    <strong>
                                        Cluster Time: {this.state.currentTime.tz(AppContext.get().getClusterSettingsService().getClusterTimeZone()).format("LLL")} ({AppContext.get().getClusterSettingsService().getClusterTimeZone()})
                                    </strong>
                                    <br />
                                </Alert>
                                <IdeaTimeRangeSlider ref={this.timeRangeSlider} startTime={this.state.working_hours_start ? this.state.working_hours_start : "09:00"} endTime={this.state.working_hours_end ? this.state.working_hours_end : "18:00"} />
                            </ColumnLayout>
                        </Form>
                    </SpaceBetween>
                </Modal>
            )
        );
    }
}

export default WorkingHoursModal;
