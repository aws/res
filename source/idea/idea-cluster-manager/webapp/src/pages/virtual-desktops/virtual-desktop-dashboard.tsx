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

import IdeaAppLayout, { IdeaAppLayoutProps } from "../../components/app-layout";
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import React, { Component, RefObject } from "react";
import { Button, Grid, Header, SpaceBetween } from "@cloudscape-design/components";
import VirtualDesktopInstanceTypesChart from "./charts/virtual-desktop-instance-types-chart";
import { AppContext } from "../../common";
import VirtualDesktopBaseChart from "./charts/virtual-desktop-base-chart";
import VirtualDesktopStateChart from "./charts/virtual-desktop-state-chart";
import VirtualDesktopBaseOSChart from "./charts/virtual-desktop-baseos-chart";
import VirtualDesktopAZDistributionChart from "./charts/virtual-desktop-az-distribution";
import VirtualDesktopSoftwareStackChart from "./charts/virtual-desktop-software-stack-chart";
import { Constants } from "../../common/constants";
import dot from "dot-object";
import VirtualDesktopProjectChart from "./charts/virtual-desktop-project-chart";
import { withRouter } from "../../navigation/navigation-utils";

export interface VirtualDesktopDashboardProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {}

export interface VirtualDesktopDashboardState {
    moduleInfo: any;
    settings: any;
    settingsLoaded: boolean;
}

class VirtualDesktopDashboard extends Component<VirtualDesktopDashboardProps, VirtualDesktopDashboardState> {
    allCharts: RefObject<VirtualDesktopBaseChart>[];
    instanceTypesChart: RefObject<VirtualDesktopInstanceTypesChart>;
    stateChart: RefObject<VirtualDesktopInstanceTypesChart>;
    baseOsChart: RefObject<VirtualDesktopBaseOSChart>;
    projectChart: RefObject<VirtualDesktopProjectChart>;
    azDistributionChart: RefObject<VirtualDesktopBaseOSChart>;
    softwareStackChart: RefObject<VirtualDesktopSoftwareStackChart>;

    constructor(props: VirtualDesktopDashboardProps) {
        super(props);
        this.instanceTypesChart = React.createRef();
        this.stateChart = React.createRef();
        this.baseOsChart = React.createRef();
        this.azDistributionChart = React.createRef();
        this.softwareStackChart = React.createRef();
        this.projectChart = React.createRef();
        this.allCharts = [this.instanceTypesChart, this.stateChart, this.baseOsChart, this.azDistributionChart];
        this.state = {
            moduleInfo: {},
            settings: {},
            settingsLoaded: false,
        };
    }

    componentDidMount() {
        AppContext.get()
            .getClusterSettingsService()
            .getVirtualDesktopSettings()
            .then((settings) => {
                let moduleInfo = AppContext.get().getClusterSettingsService().getModuleInfo(Constants.MODULE_VIRTUAL_DESKTOP_CONTROLLER);
                this.setState({
                    moduleInfo: moduleInfo,
                    settings: settings,
                    settingsLoaded: true,
                });
            });
    }

    reloadAllCharts() {
        this.allCharts.forEach((chartRef) => {
            chartRef.current!.reload();
        });
    }

    render() {
        return (
            <IdeaAppLayout
                ideaPageId={this.props.ideaPageId}
                toolsOpen={this.props.toolsOpen}
                tools={this.props.tools}
                onToolsChange={this.props.onToolsChange}
                onPageChange={this.props.onPageChange}
                sideNavHeader={this.props.sideNavHeader}
                sideNavItems={this.props.sideNavItems}
                onSideNavChange={this.props.onSideNavChange}
                onFlashbarChange={this.props.onFlashbarChange}
                flashbarItems={this.props.flashbarItems}
                breadcrumbItems={[
                    {
                        text: "RES",
                        href: "#/",
                    },
                    {
                        text: "Virtual Desktop",
                        href: "#/virtual-desktop/dashboard",
                    },
                    {
                        text: "Dashboard",
                        href: "",
                    },
                ]}
                header={
                    <Header
                        variant={"h1"}
                        actions={
                            <SpaceBetween size={"xs"} direction={"horizontal"}>
                                <Button
                                    variant="normal"
                                    iconName="refresh"
                                    onClick={() => {
                                        this.reloadAllCharts();
                                    }}
                                />
                                <Button
                                    variant={"primary"}
                                    onClick={() => {
                                        this.props.navigate("/virtual-desktop/sessions");
                                    }}
                                >
                                    View Sessions
                                </Button>
                            </SpaceBetween>
                        }
                    >
                        Virtual Desktop Dashboard
                    </Header>
                }
                contentType={"default"}
                content={
                    <Grid gridDefinition={[{ colspan: { xxs: 12, xs: 6 } }, { colspan: { xxs: 12, xs: 6 } }, { colspan: { xxs: 12, xs: 6 } }, { colspan: { xxs: 12, xs: 6 } }, { colspan: { xxs: 12, xs: 6 } }, { colspan: { xxs: 12, xs: 6 } }]}>
                        {this.state.settingsLoaded && <VirtualDesktopInstanceTypesChart ref={this.instanceTypesChart} indexName={dot.pick("opensearch.dcv_session.alias", this.state.settings)} />}
                        {this.state.settingsLoaded && <VirtualDesktopStateChart ref={this.stateChart} indexName={dot.pick("opensearch.dcv_session.alias", this.state.settings)} />}
                        {this.state.settingsLoaded && <VirtualDesktopBaseOSChart ref={this.baseOsChart} indexName={dot.pick("opensearch.dcv_session.alias", this.state.settings)} />}
                        {this.state.settingsLoaded && <VirtualDesktopProjectChart ref={this.projectChart} indexName={dot.pick("opensearch.dcv_session.alias", this.state.settings)} />}
                        {this.state.settingsLoaded && <VirtualDesktopAZDistributionChart ref={this.azDistributionChart} indexName={dot.pick("opensearch.dcv_session.alias", this.state.settings)} />}
                        {this.state.settingsLoaded && <VirtualDesktopSoftwareStackChart ref={this.softwareStackChart} indexName={dot.pick("opensearch.dcv_session.alias", this.state.settings)} />}
                    </Grid>
                }
            />
        );
    }
}

export default withRouter(VirtualDesktopDashboard);
