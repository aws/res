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

import { StatusIndicator } from "@cloudscape-design/components";
import React from "react";
import { VirtualDesktopSessionState } from "../../../client/data-model";

export interface VirtualDesktopSessionStatusIndicatorProps {
    state: VirtualDesktopSessionState;
    hibernation_enabled: boolean;
}

function VirtualDesktopSessionStatusIndicator(props: VirtualDesktopSessionStatusIndicatorProps) {
    switch (props.state) {
        case "PROVISIONING":
            return (
                <StatusIndicator type="in-progress" colorOverride="blue">
                    Provisioning
                </StatusIndicator>
            );
        case "INITIALIZING":
            return (
                <StatusIndicator type="in-progress" colorOverride="blue">
                    Initializing
                </StatusIndicator>
            );
        case "CREATING":
            return (
                <StatusIndicator type="in-progress" colorOverride="blue">
                    Creating
                </StatusIndicator>
            );
        case "READY":
            return <StatusIndicator type="success">Ready</StatusIndicator>;
        case "STOPPING":
            if (props.hibernation_enabled) {
                return (
                    <StatusIndicator type="in-progress" colorOverride="blue">
                        Hibernating
                    </StatusIndicator>
                );
            } else {
                return (
                    <StatusIndicator type="in-progress" colorOverride="blue">
                        Stopping
                    </StatusIndicator>
                );
            }
        case "STOPPED":
            if (props.hibernation_enabled) {
                return (
                    <StatusIndicator type="info" colorOverride="grey">
                        Hibernated
                    </StatusIndicator>
                );
            } else {
                return (
                    <StatusIndicator type="info" colorOverride="grey">
                        Stopped
                    </StatusIndicator>
                );
            }
        case "STOPPED_IDLE":
            return (
                <StatusIndicator type="info" colorOverride="grey">
                    Stopped - Idle
                </StatusIndicator>
            );
        case "RESUMING":
            return (
                <StatusIndicator type="in-progress" colorOverride="blue">
                    Resuming
                </StatusIndicator>
            );
        case "DELETING":
            return (
                <StatusIndicator type="in-progress" colorOverride="blue">
                    Deleting
                </StatusIndicator>
            );
        case "DELETED":
            return (
                <StatusIndicator type="in-progress" colorOverride="blue">
                    Deleting
                </StatusIndicator>
            );
        case "ERROR":
            return <StatusIndicator type="error">Error</StatusIndicator>;
    }
    return <StatusIndicator type="error">Unknown</StatusIndicator>;
}

export default VirtualDesktopSessionStatusIndicator;
