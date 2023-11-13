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
import { Box } from "@cloudscape-design/components";

export interface PasswordStrengthCheckProps {
    password?: string;
}

interface PasswordStrengthCheckState {
    length: string;
    special_char: string;
    uppercase: string;
    lowercase: string;
    numeric: string;
}

export class PasswordStrengthCheck extends Component<PasswordStrengthCheckProps, PasswordStrengthCheckState> {
    constructor(props: PasswordStrengthCheckProps) {
        super(props);
        this.state = {
            length: "initial",
            special_char: "initial",
            uppercase: "initial",
            lowercase: "initial",
            numeric: "initial",
        };
    }

    public checkPassword(password: string): boolean {
        const hasNumber = /(?=.*\d)/.test(password);
        const hasUpper = /(?=.*[A-Z])/.test(password);
        const hasLower = /(?=.*[a-z])/.test(password);
        const lengthOk = password.trim().length >= 8;
        const hasSpecialChar = /(?=.*[-+_!@#$%^&*.,?=()><])/.test(password);
        this.setState({
            length: lengthOk ? "success" : "error",
            special_char: hasSpecialChar ? "success" : "error",
            uppercase: hasUpper ? "success" : "error",
            lowercase: hasLower ? "success" : "error",
            numeric: hasNumber ? "success" : "error",
        });
        return hasNumber && hasUpper && hasLower && lengthOk && hasSpecialChar;
    }

    private getColor = (status: string): "text-status-inactive" | "text-status-success" | "text-status-error" => {
        switch (status) {
            case "initial":
                return "text-status-inactive";
            case "success":
                return "text-status-success";
        }
        return "text-status-error";
    };

    render() {
        return (
            <div>
                <Box variant="strong" padding={{ bottom: "l" }}>
                    Password Rules
                </Box>
                <div>
                    <li>
                        <Box display="inline-block" color={this.getColor(this.state.length)}>
                            Must be at least 8 characters long
                        </Box>
                    </li>
                    <li>
                        <Box display="inline-block" color={this.getColor(this.state.special_char)}>
                            Contains at least 1 special character
                        </Box>
                    </li>
                    <li>
                        <Box display="inline-block" color={this.getColor(this.state.uppercase)}>
                            Contains at least 1 uppercase letter
                        </Box>
                    </li>
                    <li>
                        <Box display="inline-block" color={this.getColor(this.state.lowercase)}>
                            Contains at least 1 lowercase letter
                        </Box>
                    </li>
                    <li>
                        <Box display="inline-block" color={this.getColor(this.state.numeric)}>
                            Contains at least 1 number
                        </Box>
                    </li>
                </div>
            </div>
        );
    }
}
