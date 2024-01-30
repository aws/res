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
import { VirtualDesktopSession } from '../../../client/data-model'

export interface VirtualDesktopStateChartProps {
    loading: boolean
    sessions: VirtualDesktopSession[];
}

class VirtualDesktopStateChart extends VirtualDesktopBaseChart<VirtualDesktopStateChartProps> {
    render() {
        const states = this.props.sessions.reduce((eax: {[key: string]: number}, item: any) => {
            eax[item.state] = (eax[item.state] || 0) + 1;
            return eax;
        }, {})
 
        let chartData: {title: string, value: number}[] = Object.entries(states).map(([key, value]) => {return {title: key, value: value}});

        const statusType = this.props.loading ? 'loading' : 'finished'

        return (
            <PieOrDonutChart
                headerDescription={"Summary of all virtual desktop sessions by state."}
                headerText={"Session State"}
                data={chartData}
                enableSelection={false}
                statusType={statusType}
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
                ariaDescription="Pie chart showing how many sessions are in what state."
                ariaLabel="Instance Types Donut Chart"
                errorText="Error loading data."
                loadingText="Loading chart"
                recoveryText="Retry"
                innerMetricDescription="sessions"
                innerMetricValue={this.props.sessions.length.toString()}
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

export default VirtualDesktopStateChart;
