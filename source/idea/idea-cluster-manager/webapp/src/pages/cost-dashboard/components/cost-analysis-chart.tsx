import * as _ from "lodash";
import { BarChart, Box, ColumnLayout } from "@cloudscape-design/components";
import { SeriesEntry } from "./cost-analysis-widget";

export interface CostAnalysisChartProps {
    series: SeriesEntry[]
    barChartStatus: "loading" | "finished" | "error"
    xDomain: string[]
    costSumByXValue: { [key: string]: number }
    isEmptySeries: boolean
}

const CostAnalysisChart = ({ series, barChartStatus, xDomain, costSumByXValue, isEmptySeries }: CostAnalysisChartProps ) => {
    return (
        <BarChart
            series={series}
            statusType={barChartStatus}
            xDomain={xDomain}
            loadingText="Loading chart"
            ariaLabel="Single data series line chart"
            height={300}
            stackedBars={true}
            hideFilter={true}
            hideLegend={isEmptySeries}
            errorText="Error loading data. Please refresh the chart."
            yTitle="Costs (USD)"
            detailPopoverFooter={xValue => (
                <ColumnLayout columns={2} disableGutters>
                    <Box float="left" variant="h5">
                        Total Cost
                    </Box>
                    <Box float="left" textAlign="left">
                        ${costSumByXValue[xValue].toLocaleString("en-US", {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2
                        })}
                    </Box>
                </ColumnLayout>
            )}
            i18nStrings={{
                yTickFormatter: function o(e) {
                    return Math.abs(e) >= 1e9
                    ? (e / 1e9).toFixed(1).replace(/\.0$/, "") +
                        "G"
                    : Math.abs(e) >= 1e6
                    ? (e / 1e6).toFixed(1).replace(/\.0$/, "") +
                        "M"
                    : Math.abs(e) >= 1e3
                    ? (e / 1e3).toFixed(1).replace(/\.0$/, "") +
                        "K"
                    : e.toFixed(2);
                }
                }}
            empty={
            <Box textAlign="center" color="inherit">
                <b>No data displayed</b>
                <Box variant="p" color="inherit">
                    <p>
                        Cost allocation tags have been enabled successfully.<br />
                        Wait up to 12 hours for cost data to update and then refresh the chart to populate data.
                    </p>
                </Box>
            </Box>
            }
        />
    )
}

export default CostAnalysisChart;
