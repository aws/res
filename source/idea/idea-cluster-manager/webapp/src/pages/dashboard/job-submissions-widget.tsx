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

import { Box, Button, LineChart } from "@cloudscape-design/components";
import { AppContext } from "../../common";
import { useEffect } from "react";

export function JobSubmissionsWidget() {
    useEffect(() => {
        AppContext.get()
            .client()
            .analytics()
            .queryOpenSearch({
                data: {
                    index: "idea-test1_jobs",
                    body: {
                        size: 0,
                        aggs: {
                            jobs: {
                                date_histogram: {
                                    field: "queue_time",
                                    calendar_interval: "hour",
                                },
                            },
                        },
                    },
                },
            })
            .then((result) => {
                console.log(result);
            });
    });

    const start = new Date();
    const end = new Date();
    start.setDate(start.getDate() - 7);

    return (
        <LineChart
            series={[
                {
                    title: "Jobs Submitted",
                    type: "line",
                    data: [
                        { x: new Date(1651950000000), y: 3 },
                        { x: new Date(1651953600000), y: 54 },
                    ],
                },
            ]}
            xDomain={[start, end]}
            yDomain={[0, 1000]}
            i18nStrings={{
                filterLabel: "Filter displayed data",
                filterPlaceholder: "Filter data",
                filterSelectedAriaLabel: "selected",
                legendAriaLabel: "Legend",
                chartAriaRoleDescription: "line chart",
                xTickFormatter: (e) =>
                    e
                        .toLocaleDateString("en-US", {
                            month: "short",
                            day: "numeric",
                            hour: "numeric",
                            minute: "numeric",
                            hour12: !1,
                        })
                        .split(",")
                        .join("\n"),
                yTickFormatter: undefined,
            }}
            ariaLabel="Single data series line chart"
            errorText="Error loading data."
            height={200}
            hideFilter
            hideLegend
            loadingText="Loading chart"
            recoveryText="Retry"
            xScaleType="time"
            xTitle="Time (UTC)"
            yTitle="Jobs Submitted"
            empty={
                <Box textAlign="center" color="inherit">
                    <b>No data available</b>
                    <Box variant="p" color="inherit">
                        There is no data available
                    </Box>
                </Box>
            }
            noMatch={
                <Box textAlign="center" color="inherit">
                    <b>No matching data</b>
                    <Box variant="p" color="inherit">
                        There is no matching data to display
                    </Box>
                    <Button>Clear filter</Button>
                </Box>
            }
        />
    );
}
