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
import { AppContext } from "../../../common";
import VirtualDesktopBaseChart from "./virtual-desktop-base-chart";
import PieOrDonutChart from "../../../components/charts/pie-or-donut-chart";

export interface VirtualDesktopStateChartProps {
    indexName: string;
}

interface VirtualDesktopStateChartState {
    chartData: any;
    total: string;
    statusType: "loading" | "finished" | "error";
}

class VirtualDesktopStateChart extends VirtualDesktopBaseChart<VirtualDesktopStateChartProps, VirtualDesktopStateChartState> {
    constructor(props: VirtualDesktopStateChartProps) {
        super(props);
        this.state = {
            chartData: [],
            total: "-",
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
                                    state: {
                                        terms: {
                                            field: "state.raw",
                                        },
                                    },
                                },
                            },
                        },
                    })
                    .then((result) => {
                        let chartData: any = [];
                        if (result.data?.aggregations) {
                            const aggregations: any = result.data.aggregations;
                            let state = aggregations.state;
                            let buckets: any[] = state.buckets;
                            buckets.forEach((bucket) => {
                                chartData.push({
                                    title: bucket.key,
                                    value: bucket.doc_count,
                                });
                            });
                        }
                        let hits: any = result.data?.hits;
                        this.setState({
                            chartData: chartData,
                            total: `${hits.total.value}`,
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
            <PieOrDonutChart
                headerDescription={"Summary of all virtual desktop sessions by state."}
                headerText={"Session State"}
                data={this.state.chartData}
                enableSelection={false}
                statusType={this.state.statusType}
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

export default VirtualDesktopStateChart;
