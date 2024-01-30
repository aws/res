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
import VirtualDesktopBaseChart from "./virtual-desktop-base-chart";
import { BarChart, Box, Container, Header } from "@cloudscape-design/components";
import { VirtualDesktopSession } from '../../../client/data-model'

export interface VirtualDesktopSoftwareStackChartProps {
    loading: boolean
    sessions: VirtualDesktopSession[];
}

class VirtualDesktopSoftwareStackChart extends VirtualDesktopBaseChart<VirtualDesktopSoftwareStackChartProps> {
    render() {
        const states = this.props.sessions.reduce((eax: {[key: string]: number}, item: any) => {
            eax[item.software_stack.name] = (eax[item.software_stack.name] || 0) + 1;
            return eax;
        }, {})
 
        let chartData: {x: string, y: number}[] = Object.entries(states).map(([key, value]) => {return {x: key, y: value}});

        const statusType = this.props.loading ? 'loading' : 'finished'

        return (
            <Container
                header={
                    <Header variant={"h2"} description={"Summary of all virtual desktop sessions by Software Stack."}>
                        Software Stacks
                    </Header>
                }
            >
                <BarChart
                    series={[
                        {
                            title: "Sessions",
                            type: "bar",
                            data: chartData,
                        },
                    ]}
                    i18nStrings={{
                        filterLabel: "Filter displayed data",
                        filterPlaceholder: "Filter data",
                        filterSelectedAriaLabel: "selected",
                        legendAriaLabel: "Legend",
                        chartAriaRoleDescription: "Bar chart",
                    }}
                    horizontalBars
                    hideFilter={true}
                    ariaLabel="Single data series line chart"
                    errorText="Error loading data."
                    height={300}
                    statusType={statusType}
                    loadingText="Loading chart"
                    recoveryText="Retry"
                    xScaleType="categorical"
                    xTitle="Software Stacks"
                    yTitle="No. of Sessions"
                    empty={
                        <Box textAlign="center" color="inherit">
                            <b>No sessions available</b>
                            <Box variant="p" color="inherit">
                                There are no sessions available
                            </Box>
                        </Box>
                    }
                />
            </Container>
        );
    }
}

export default VirtualDesktopSoftwareStackChart;
