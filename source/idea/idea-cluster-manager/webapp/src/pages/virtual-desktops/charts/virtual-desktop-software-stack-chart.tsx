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
import { AppContext } from "../../../common";
import { BarChart, Box, Container, Header } from "@cloudscape-design/components";

export interface VirtualDesktopSoftwareStackChartProps {
    indexName: string;
}

interface VirtualDesktopSoftwareStackChartState {
    series: any;
    statusType: "loading" | "finished" | "error";
}

class VirtualDesktopSoftwareStackChart extends VirtualDesktopBaseChart<VirtualDesktopSoftwareStackChartProps, VirtualDesktopSoftwareStackChartState> {
    constructor(props: VirtualDesktopSoftwareStackChartProps) {
        super(props);
        this.state = {
            series: [],
            statusType: "loading",
        };
    }

    componentDidMount() {
        this.loadChartData();
    }

    reload() {
        this.loadChartData();
    }

    loadChartData() {
        this.setState(
            {
                statusType: "loading",
            },
            () => {
                AppContext.get()
                    .client()
                    .analytics()
                    .queryOpenSearch({
                        data: {
                            index: this.props.indexName,
                            body: {
                                size: 0,
                                aggs: {
                                    software_stack: {
                                        terms: {
                                            field: "software_stack.name.raw",
                                        },
                                    },
                                },
                            },
                        },
                    })
                    .then((result) => {
                        let series: any[] = [];
                        if (result.data?.aggregations) {
                            const aggregations: any = result.data.aggregations;
                            let software_stacks = aggregations.software_stack;
                            let buckets: any[] = software_stacks.buckets;
                            buckets.forEach((bucket) => {
                                series.push({
                                    x: bucket.key,
                                    y: bucket.doc_count,
                                });
                            });
                        }
                        this.setState({
                            series: series,
                            statusType: "finished",
                        });
                    })
                    .catch((error) => {
                        console.error(error);
                        this.setState({
                            statusType: "error",
                        });
                    });
            }
        );
    }

    render() {
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
                            data: this.state.series,
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
                    statusType={this.state.statusType}
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
