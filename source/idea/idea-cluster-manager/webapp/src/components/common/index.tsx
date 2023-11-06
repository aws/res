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

import { Button, Popover, StatusIndicator } from "@cloudscape-design/components";
import Utils from "../../common/utils";
import React from "react";

export interface EnabledDisabledStatusIndicatorProps {
    enabled: boolean;
}

export function EnabledDisabledStatusIndicator(props: EnabledDisabledStatusIndicatorProps) {
    if (props.enabled) {
        return <StatusIndicator type={"success"}>Enabled</StatusIndicator>;
    } else {
        return <StatusIndicator type={"stopped"}>Disabled</StatusIndicator>;
    }
}

export interface CopyToClipBoardProps {
    text: string;
    feedback?: string;
}
export function CopyToClipBoard(props: CopyToClipBoardProps) {
    return (
        <Popover size="small" position="top" triggerType="custom" dismissButton={false} content={Utils.isNotEmpty(props.feedback) && <StatusIndicator type="success">{props.feedback}</StatusIndicator>}>
            <Button variant={"inline-icon"} onClick={() => Utils.copyToClipBoard(props.text)} iconName={"copy"} />
        </Popover>
    );
}
