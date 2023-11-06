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
import { Tabs } from "@cloudscape-design/components";
import { TabsProps } from "@cloudscape-design/components/tabs/interfaces";

export interface IdeaTabsProps {
    onRefresh?: () => void;
    refresh?: boolean;
    headerText?: string;
    tabs: ReadonlyArray<TabsProps.Tab>;
}

export interface IdeaTabsState {}

class IdeaTabs extends Component<IdeaTabsProps, IdeaTabsState> {
    render() {
        return <Tabs tabs={this.props.tabs} />;
    }
}

export default IdeaTabs;
