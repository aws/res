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
import { Link } from "@cloudscape-design/components";
import Box from "@cloudscape-design/components/box";

import { SocaUserInputParamMetadata } from "../../client/data-model";

export interface IdeaFormReviewFieldProps {
    param: SocaUserInputParamMetadata;
    value: any;
}

export interface IdeaFormReviewFieldState {
    showPassword: boolean;
}

class IdeaFormReviewField extends Component<IdeaFormReviewFieldProps, IdeaFormReviewFieldState> {
    constructor(props: IdeaFormReviewFieldProps) {
        super(props);
        this.state = {
            showPassword: false,
        };
    }

    getParamName(): string {
        return this.props.param.name!;
    }

    isMultiple(): boolean {
        if (this.props.param.multiple != null) {
            return this.props.param.multiple;
        }
        return false;
    }

    isMultiline(): boolean {
        if (this.props.param.multiline != null) {
            return this.props.param.multiline;
        }
        return false;
    }

    isAmount(): boolean {
        if (this.props.param.data_type != null) {
            return this.props.param.data_type === "amount";
        }
        return false;
    }

    isMemory(): boolean {
        if (this.props.param.data_type != null) {
            return this.props.param.data_type === "memory";
        }
        return false;
    }

    isPassword(): boolean {
        return this.props.param.param_type === "password";
    }

    buildFormattedMultilineValue(value: string) {
        return (
            <ul>
                {value.split(/\r?\n/).map((line, index) => {
                    return <li key={index}>{line}</li>;
                })}
            </ul>
        );
    }

    buildFormattedMultipleValue(values: any[]) {
        return (
            <div>
                {values.map((value, index) => {
                    if (this.isMultiline()) {
                        return <li key={index}>{this.buildFormattedMultilineValue(value)}</li>;
                    } else {
                        return <li key={index}>{value}</li>;
                    }
                })}
            </div>
        );
    }

    buildPassword(value: string) {
        const password = () => {
            if (this.state.showPassword) {
                return value;
            } else {
                return "********";
            }
        };
        const toggle = () => {
            this.setState({
                showPassword: !this.state.showPassword,
            });
        };
        return (
            <span>
                {password()}
                &nbsp;&nbsp;
                <span onClick={(_) => toggle()}>
                    <Link variant={"secondary"} fontSize={"body-s"}>
                        {this.state.showPassword ? "Hide" : "Show"}
                    </Link>
                </span>
            </span>
        );
    }

    getParamValue() {
        let paramValue = this.props.value;
        if (paramValue == null) {
            return "-";
        }
        if (this.isPassword()) {
            return this.buildPassword(paramValue);
        }
        if (this.isMultiple()) {
            return this.buildFormattedMultipleValue(paramValue);
        } else if (typeof paramValue === "boolean") {
            if (paramValue) {
                return "Yes";
            } else {
                return "No";
            }
        } else if (this.isMultiline()) {
            return this.buildFormattedMultilineValue(paramValue);
        } else if (this.isAmount()) {
            return `${paramValue.amount} ${paramValue.unit}`;
        } else if (this.isMemory()) {
            return `${paramValue.value}${paramValue.unit}`;
        } else {
            return paramValue;
        }
    }

    render() {
        return (
            <div>
                <Box margin={{ bottom: "xxxs" }} color="text-label">
                    {this.props.param.title}
                </Box>
                <div>{this.getParamValue()}</div>
            </div>
        );
    }
}

export default IdeaFormReviewField;
