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

import React from "react";
import { getTrackBackground, Range } from "react-range";

export interface IdeaTimeRangeSliderProps {
    startTime: string;
    endTime: string;
    onChange?: (start: string, end: string) => void;
}

export interface IdeaTimeRangeSliderState {
    values: number[];
}

const MIN = 0;
const MAX = 1410;

class IdeaTimeRangeSlider extends React.Component<IdeaTimeRangeSliderProps, IdeaTimeRangeSliderState> {
    constructor(props: IdeaTimeRangeSliderProps) {
        super(props);
        this.state = {
            values: [this.convertClockTimeToMinutes(this.props.startTime), this.convertClockTimeToMinutes(this.props.endTime)],
        };
    }

    /**
     * convert 24-hour clock time to minutes
     * @param time
     */
    convertClockTimeToMinutes(time: string): number {
        let tokens = time.split(":");
        let hours = parseInt(tokens[0], 10);
        let minutes = parseInt(tokens[1], 10);
        return hours * 60 + minutes;
    }

    /**
     * converts minutes to 24-hour clock time
     * convert 0 to 00:00
     * convert 1379 to 23:59
     * @param minutes
     */
    convertMinutesToClockTime(minutes: number): string {
        let h = Math.trunc(minutes / 60);
        let m = minutes % 60;
        return `${h.toFixed().padStart(2, "0")}:${m.toFixed().padStart(2, "0")}`;
    }

    /**
     * converts minutes to 12 hour display time with am/pm
     * convert 0 to 00:00am
     * convert 1439 to 11:59pm
     * @param minutes
     */
    convertMinutesToDisplayTime(minutes: number): string {
        let h = Math.trunc(minutes / 60);
        let ampm = "am";
        if (h > 11) {
            h = h % 12;
            ampm = "pm";
        }
        let m = minutes % 60;
        return `${h.toFixed().padStart(2, "0")}:${m.toFixed().padStart(2, "0")}${ampm}`;
    }

    getStartTime(): string {
        return this.convertMinutesToClockTime(this.state.values[0]);
    }

    getEndTime(): string {
        return this.convertMinutesToClockTime(this.state.values[1]);
    }

    getDisplayStartTime(): string {
        return this.convertMinutesToDisplayTime(this.state.values[0]);
    }

    getDisplayEndTime(): string {
        return this.convertMinutesToDisplayTime(this.state.values[1]);
    }

    render() {
        return (
            <div
                style={{
                    display: "flex",
                    justifyContent: "center",
                    flexWrap: "wrap",
                }}
            >
                <Range
                    step={30}
                    min={MIN}
                    max={MAX}
                    values={this.state.values}
                    onChange={(values) => {
                        this.setState(
                            {
                                values: values,
                            },
                            () => {
                                if (this.props.onChange) {
                                    this.props.onChange(this.getStartTime(), this.getEndTime());
                                }
                            }
                        );
                    }}
                    renderTrack={({ props, children }) => {
                        return (
                            <div
                                onMouseDown={props.onMouseDown}
                                onTouchStart={props.onTouchStart}
                                style={{
                                    ...props.style,
                                    height: "36px",
                                    display: "flex",
                                    width: "100%",
                                }}
                            >
                                <div
                                    ref={props.ref}
                                    style={{
                                        height: "5px",
                                        width: "100%",
                                        borderRadius: "4px",
                                        background: getTrackBackground({
                                            values: this.state.values,
                                            colors: ["#ccc", "#0073bb", "#ccc"],
                                            min: MIN,
                                            max: MAX,
                                            rtl: false,
                                        }),
                                        alignSelf: "center",
                                    }}
                                >
                                    {children}
                                </div>
                            </div>
                        );
                    }}
                    renderThumb={({ props, isDragged }) => {
                        return (
                            <div
                                {...props}
                                style={{
                                    ...props.style,
                                    height: "16px",
                                    width: "16px",
                                    borderRadius: "4px",
                                    backgroundColor: "#FFF",
                                    display: "flex",
                                    justifyContent: "center",
                                    alignItems: "center",
                                    boxShadow: "0px 2px 6px #AAA",
                                }}
                            >
                                <div
                                    style={{
                                        height: "5px",
                                        width: "5px",
                                        backgroundColor: isDragged ? "#548BF4" : "#CCC",
                                    }}
                                />
                            </div>
                        );
                    }}
                />
                <strong>
                    {this.getDisplayStartTime()} - {this.getDisplayEndTime()}
                </strong>
            </div>
        );
    }
}

export default IdeaTimeRangeSlider;
