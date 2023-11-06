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
import Box from "@cloudscape-design/components/box";
import Utils from "../../common/utils";
import { ColumnLayout, Link } from "@cloudscape-design/components";
import { AppContext } from "../../common";
import { CopyToClipBoard } from "../common";

export interface KeyValueProps {
    title: string;
    value?: any;
    clipboard?: boolean;
    children?: JSX.Element;
    type?: "memory" | "date" | "amount" | "boolean" | "react-node" | "link" | "external-link" | "ec2:instance-id" | "ec2:security-group-id" | "ec2:asg-arn" | "ec2:asg-name" | "cognito:user-pool-id" | "s3:bucket-name";
    suffix?: string;
    renderType?: "key-value" | "metric";
}

export interface KeyValueState {}

export interface KeyValueGroupProps {
    title: string;
    children: React.ReactNode | React.ReactNode[];
}

export interface KeyValueGroupState {}

export class KeyValue extends Component<KeyValueProps, KeyValueState> {
    isMemoryType(): boolean {
        if (this.props.type == null) {
            return false;
        }
        return this.props.type === "memory";
    }

    isDateType(): boolean {
        if (this.props.type == null) {
            return false;
        }
        return this.props.type === "date";
    }

    isAmountType(): boolean {
        if (this.props.type == null) {
            return false;
        }
        return this.props.type === "amount";
    }

    isBooleanType(): boolean {
        if (Utils.isBoolean(this.props.value)) {
            return true;
        }
        return this.props.type != null && this.props.type === "boolean";
    }

    isReactNodeType(): boolean {
        if (this.props.type == null) {
            return false;
        }
        return this.props.type === "react-node";
    }

    getRenderType(): string {
        if (Utils.isEmpty(this.props.renderType)) {
            return "key-value";
        }
        return this.props.renderType!;
    }

    isRenderTypeMetric(): boolean {
        return this.getRenderType() === "metric";
    }

    isClipboardCopy(): boolean {
        if (this.props.clipboard == null) {
            return false;
        }
        return this.props.clipboard;
    }

    isValueEmpty(): boolean {
        if (this.props.children != null) {
            return false;
        }
        if (typeof this.props.value === "undefined") {
            return true;
        }
        if (this.props.value == null) {
            return true;
        }
        return Utils.isEmpty(this.props.value);
    }

    getValue(): string | string[] | JSX.Element {
        if (this.props.children != null) {
            return this.props.children;
        }

        if (this.isBooleanType()) {
            if (Utils.isTrue(this.props.value)) {
                return "Yes";
            } else {
                return "No";
            }
        }

        if (this.isMemoryType()) {
            return Utils.getFormattedMemory(this.props.value);
        }

        if (this.isAmountType()) {
            return Utils.getFormattedAmount(this.props.value);
        }

        if (this.isDateType()) {
            return new Date(this.props.value).toLocaleString();
        }

        if (this.isReactNodeType()) {
            return this.props.value;
        }

        if (Utils.isArray(this.props.value)) {
            return this.props.value;
        } else {
            let value = Utils.asString(this.props.value);
            if (Utils.isNotEmpty(this.props.suffix)) {
                return `${value} ${this.props.suffix}`;
            } else {
                return value;
            }
        }
    }

    getFormattedValue() {
        let value = this.getValue();
        if (this.props.type == null) {
            if (Utils.isEmpty(value)) {
                return "-";
            }
            return value;
        }

        if (Utils.isEmpty(value)) {
            return "-";
        }

        switch (this.props.type) {
            case "ec2:instance-id":
                return (
                    <span>
                        <Link external={true} href={Utils.getEc2InstanceUrl(AppContext.get().getAwsRegion(), Utils.asString(value))}>
                            {value}
                        </Link>
                        &nbsp;&nbsp;
                        <Link external={true} href={Utils.getSessionManagerConnectionUrl(AppContext.get().getAwsRegion(), Utils.asString(value))}>
                            (Connect)
                        </Link>
                    </span>
                );
            case "ec2:security-group-id":
                return (
                    <Link external={true} href={Utils.getSecurityGroupUrl(AppContext.get().getAwsRegion(), Utils.asString(value))}>
                        {value}
                    </Link>
                );
            case "ec2:asg-arn":
                let arn = Utils.asString(value);
                let split = arn.split("/");
                let name = split[split.length - 1];
                return (
                    <Link external={true} href={Utils.getASGUrl(AppContext.get().getAwsRegion(), name)}>
                        {value}
                    </Link>
                );
            case "ec2:asg-name":
                return (
                    <Link external={true} href={Utils.getASGUrl(AppContext.get().getAwsRegion(), Utils.asString(value))}>
                        {value}
                    </Link>
                );
            case "cognito:user-pool-id":
                return (
                    <Link external={true} href={Utils.getCognitoUserPoolUrl(AppContext.get().getAwsRegion(), Utils.asString(value))}>
                        {value}
                    </Link>
                );
            case "s3:bucket-name":
                return (
                    <Link external={true} href={Utils.getS3BucketUrl(AppContext.get().getAwsRegion(), Utils.asString(value))}>
                        {value}
                    </Link>
                );
            case "link":
                return <Link href={Utils.asString(value)}>{value}</Link>;
            case "external-link":
                return (
                    <Link external={true} href={Utils.asString(value)}>
                        {value}
                    </Link>
                );
        }

        return value;
    }

    buildValue() {
        if (this.isRenderTypeMetric()) {
            return (
                <div style={{ margin: "10px 0" }}>
                    <span
                        style={{
                            fontSize: "x-large",
                        }}
                    >
                        {this.getValue()}
                    </span>
                </div>
            );
        } else {
            if (this.isClipboardCopy() && !this.isValueEmpty()) {
                if (Utils.isArray(this.props.value)) {
                    let values: string[] = this.props.value;
                    return (
                        <div>
                            {values.map((value, index) => {
                                return (
                                    <li key={`${this.props.title}-${index}`}>
                                        <span>
                                            <CopyToClipBoard text={Utils.asString(value)} feedback={`${this.props.title} (${index + 1}) copied`} /> {Utils.asString(value)}
                                        </span>
                                    </li>
                                );
                            })}
                        </div>
                    );
                } else {
                    return (
                        <span>
                            <CopyToClipBoard text={Utils.asString(this.getValue())} feedback={`${this.props.title} copied`} /> {this.getFormattedValue()}
                        </span>
                    );
                }
            } else {
                if (Utils.isArray(this.props.value)) {
                    let values: string[] = this.props.value;
                    return (
                        <div>
                            {values.map((value, index) => {
                                return <li key={`${this.props.title}-${index}`}>{Utils.asString(value)}</li>;
                            })}
                        </div>
                    );
                } else {
                    return this.getFormattedValue();
                }
            }
        }
    }

    render() {
        return (
            <div>
                <Box margin={{ bottom: "xxxs" }} color="text-body-secondary" fontWeight={"bold"}>
                    {this.props.title}
                </Box>
                {this.buildValue()}
            </div>
        );
    }
}

export class KeyValueGroup extends Component<KeyValueGroupProps, KeyValueGroupState> {
    render() {
        return (
            <Box>
                <h3>{this.props.title}</h3>
                <ColumnLayout columns={2}>{this.props.children}</ColumnLayout>
            </Box>
        );
    }
}
