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
import Utils from "../../../common/utils";
import PieOrDonutChart from "../../../components/charts/pie-or-donut-chart";

export interface VirtualDesktopBaseOSChartProps {
    indexName: string;
}

interface VirtualDesktopBaseOSChartState {
    chartData: any;
    total: string;
    statusType: "loading" | "finished" | "error";
}

class VirtualDesktopBaseOSChart extends VirtualDesktopBaseChart<VirtualDesktopBaseOSChartProps, VirtualDesktopBaseOSChartState> {
    constructor(props: VirtualDesktopBaseOSChartProps) {
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
                                    base_os: {
                                        terms: {
                                            field: "base_os.raw",
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
                            let base_os = aggregations.base_os;
                            let buckets: any[] = base_os.buckets;
                            buckets.forEach((bucket) => {
                                chartData.push({
                                    title: Utils.getOsTitle(bucket.key),
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
                headerDescription={"Summary of all virtual desktop sessions by Base OS."}
                headerText={"Base OS"}
                enableSelection={false}
                statusType={this.state.statusType}
                defaultChartMode={"piechart"}
                data={this.state.chartData}
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
                ariaDescription="Pie chart showing how many sessions are of which BaseOS."
                ariaLabel="Base OS Pie Chart"
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

export default VirtualDesktopBaseOSChart;
