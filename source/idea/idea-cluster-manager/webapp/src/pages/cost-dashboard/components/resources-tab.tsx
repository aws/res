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
import { Grid } from "@cloudscape-design/components";
import VirtualDesktopBaseChart from "../../virtual-desktops/charts/virtual-desktop-base-chart";
import VirtualDesktopInstanceTypesChart from "../../virtual-desktops/charts/virtual-desktop-instance-types-chart";
import VirtualDesktopStateChart from "../../virtual-desktops/charts/virtual-desktop-state-chart";
import VirtualDesktopBaseOSChart from "../../virtual-desktops/charts/virtual-desktop-baseos-chart";
import VirtualDesktopSoftwareStackChart from "../../virtual-desktops/charts/virtual-desktop-software-stack-chart";
import VirtualDesktopProjectChart from "../../virtual-desktops/charts/virtual-desktop-project-chart";
import { VirtualDesktopSession } from '../../../client/data-model'

export interface ResourcesTabProps {
    sessions: VirtualDesktopSession[];
    loading: boolean
}

class ResourcesTab extends Component<ResourcesTabProps> {
    allCharts: RefObject<VirtualDesktopBaseChart>[];
    instanceTypesChart: RefObject<VirtualDesktopInstanceTypesChart>;
    stateChart: RefObject<VirtualDesktopInstanceTypesChart>;
    baseOsChart: RefObject<VirtualDesktopBaseOSChart>;
    projectChart: RefObject<VirtualDesktopProjectChart>;
    softwareStackChart: RefObject<VirtualDesktopSoftwareStackChart>;

    constructor(props: ResourcesTabProps) {
        super(props);
        this.instanceTypesChart = React.createRef();
        this.stateChart = React.createRef();
        this.baseOsChart = React.createRef();
        this.softwareStackChart = React.createRef();
        this.projectChart = React.createRef();
        this.allCharts = [this.instanceTypesChart, this.stateChart, this.baseOsChart];
    }

    render() {
        return (
            <Grid gridDefinition={[{ colspan: { xxs: 12, xs: 6 } }, { colspan: { xxs: 12, xs: 6 } }, { colspan: { xxs: 12, xs: 6 } }, { colspan: { xxs: 12, xs: 6 } }, { colspan: { xxs: 12, xs: 6 } }, { colspan: { xxs: 12, xs: 6 } }]}>
                <VirtualDesktopInstanceTypesChart ref={this.instanceTypesChart} loading={this.props.loading} sessions={this.props.sessions}/>
                <VirtualDesktopStateChart ref={this.stateChart} loading={this.props.loading} sessions={this.props.sessions}/>
                <VirtualDesktopBaseOSChart ref={this.baseOsChart} loading={this.props.loading} sessions={this.props.sessions}/>
                <VirtualDesktopProjectChart ref={this.projectChart} loading={this.props.loading} sessions={this.props.sessions}/>
                <VirtualDesktopSoftwareStackChart ref={this.softwareStackChart} loading={this.props.loading} sessions={this.props.sessions}/>
            </Grid>
        );
    }
}

export default ResourcesTab;
