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

import { Box } from "@cloudscape-design/components";
import VirtualDesktopBaseChart from "./virtual-desktop-base-chart";
import PieOrDonutChart from "../../../components/charts/pie-or-donut-chart";

export interface VirtualDesktopAZDistributionChartProps {
    indexName: string;
}

interface VirtualDesktopAZDistributionChartState {
    chartData: any;
    total: string;
    statusType: "loading" | "finished" | "error";
}

class VirtualDesktopAZDistributionChart extends VirtualDesktopBaseChart<VirtualDesktopAZDistributionChartProps, VirtualDesktopAZDistributionChartState> {
    constructor(props: VirtualDesktopAZDistributionChartProps) {
        super(props);
        this.state = {
            chartData: [],
            total: "-",
            statusType: "loading",
        };
    }

    render() {
        return (
            <PieOrDonutChart
                headerDescription={"Summary of all virtual desktop sessions by Availability Zone."}
                headerText={"Availability Zones"}
                data={this.state.chartData}
                statusType={this.state.statusType}
                enableSelection={false}
                defaultChartMode={"piechart"}
                i18nStrings={{
                    detailsValue: "Value",
                    detailsPercentage: "Percentage",
                    filterLabel: "Filter displayed data",
                    filterPlaceholder: "Filter data",
                    filterSelectedAriaLabel: "selected",
                    detailPopoverDismissAriaLabel: "Dismiss",
                    legendAriaLabel: "Legend",
                    chartAriaRoleDescription: "pie chart",
                    segmentAriaRoleDescription: "segment",
                }}
                hideFilter={true}
                ariaDescription="Pie chart showing how many sessions are in which Availability Zones."
                ariaLabel="Availability Zone Distribution Chart"
                errorText="Error loading data."
                loadingText="Loading chart"
                recoveryText="Retry"
                innerMetricDescription="sessions"
                innerMetricValue={this.state.total}
                empty={
                    <Box textAlign="center" color="inherit">
                        <b>No sessions available</b>
                        <Box variant="p" color="inherit">
                            There are no sessions available
                        </Box>
                    </Box>
                }
            />
        );
    }
}

export default VirtualDesktopAZDistributionChart;
