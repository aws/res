import * as _ from "lodash";
import { useState, useEffect, useRef } from "react";
import { Box, Button, ColumnLayout, Container, DateRangePickerProps, ExpandableSection, Header, Modal, SelectProps, SpaceBetween, TextContent } from "@cloudscape-design/components";
import ProxyClient from "../../../client/proxy-client";
import { AppContext } from "../../../common";
import { GetCostAndUsageRequest, CostExplorerGetTagsResult, GetCostAndUsageResult, ListProjectsResult } from "../../../client/data-model";
import { OnFlashbarChangeEvent } from "../../../App";
import CsvDownloader from "react-csv-downloader";
import useFormatCostsCsv, { CSVDownloadParams } from "./useFormatCostsCsv";
import DateRangeFilter from "./date-range-filter";
import GranularityFilter from "./granularity-filter";
import { convertToDateRange } from "../utils/cost-dashboard-utils";
import ProjectsFilter from "./projects-filter";
import CostAnalysisChart from "./cost-analysis-chart";
import { OptionDefinition } from "@cloudscape-design/components/internal/components/option/interfaces";
import {COST_DASHBOARD_TAGS, PROJECTS_FILTER_SESSION_KEY, PROJECTS_REF_FILTER_SESSION_KEY, GRANULARITY_FILTER_SESSION_KEY, DATE_RANGE_FILTER_SESSION_KEY, MAX_PROJECTS_TO_SHOW, RELATIVE_DATE_RANGE_FILTER_SESSION_KEY, SHOULD_USE_RELATIVE_DATE_RANGE_SESSION_KEY} from "../utils/cost-dashboard-constants";

export enum BarChartType {
    Bar = "bar"
};

export interface DropdownFilterOptions {
    options: SelectProps.Options
    status: "pending" | "loading" | "finished" | "error"
    loaded: boolean
}
export interface SeriesEntry {
    title: string,
    type: BarChartType,
    data: { x: string, y: number }[]
    valueFormatter?: (e: number) => string
}

export interface CostAnalysisWidgetProps {
    onFlashbarChange: (event: OnFlashbarChangeEvent) => void;
    response: ListProjectsResult;
}

const CostAnalysisWidget = ({ onFlashbarChange, response }: CostAnalysisWidgetProps ) => {
    const [absoluteDateRange, setAbsoluteDateRange] = useState<DateRangePickerProps.AbsoluteValue>(convertToDateRange({
        key: "previous-6-month",
        amount: 6,
        unit: "month",
        type: "relative",
    }))
    const [relativeDateRange, setRelativeDateRange] = useState<DateRangePickerProps.RelativeValue>({
        key: "previous-6-month",
        amount: 6,
        unit: "month",
        type: "relative",
    })
    const [shouldUseRelativeDateRange, setShouldUseRelativeDateRange] = useState<boolean>(true)
    const [granularity, setGranularity] = useState<{ label: string, value: GetCostAndUsageRequest["Granularity"]}>({ label: "Monthly", value: "MONTHLY" })
    const [selectedProjects, setSelectedProjects] = useState<readonly OptionDefinition[]>([]);
    const selectedProjectsRef = useRef<string[]>([]);
    const [barChartStatus, setBarChartStatus] = useState<"loading" | "finished" | "error">("finished");
    const [xDomain, setXDomain] = useState<string[]>([]);
    const [series, setSeries] = useState<SeriesEntry[]>([]);
    const [costSumByXValue, setCostSumByXValue] = useState<{ [key: string]: number }>({});
    const [modalVisible, setModalVisible] = useState<boolean>(false);
    const [isEmptySeries, setIsEmptySeries] = useState<boolean>(false);
    const [projectsFilter, setProjectsFilter] = useState<DropdownFilterOptions>({
        options: [],
        loaded: false,
        status: "loading"
    });
    const [projectCodeToChartLabelMap, setProjectCodeToChartLabelMap] = useState<{ [key: string]: string }>({});
    const [resProjects, setResProjects] = useState<string[]>([]);
    const [csvDownloadParams, setCsvDownloadParams] = useState<CSVDownloadParams>({
        tagKey: COST_DASHBOARD_TAGS[0],
        getTagsResult: { Tags: [] },
        getCostAndUsageResult: {
            ResultsByTime: [],
            DimensionValueAttributes: []
        }
    });
    const [modalParams, setModalParams] = useState<any>({
        onClick: () => {
            setModalVisible(false);
        },
        onCancel: () => {
            setModalVisible(false);
        },
        headerText: "",
        bodyText: ""
    });
    const latestRequestIdRef = useRef<string>("");
    const [csvColumnHeaders, csvData] = useFormatCostsCsv(csvDownloadParams);
    const proxyClient: ProxyClient = AppContext.get().client().proxy();
    const defaultProjects = useRef<OptionDefinition[]>([]);
    const defaultProjectsRef = useRef<string[]>([]);

    const loadProjectsFromRes = async (): Promise<void> => {
        try {
            const projects = response.listing || [];
            const filterOptions: any = [];
            let codeToChartLabelMap: {[key: string]: string} = {};
            _.forEach(projects, function (project) {
                filterOptions.push({
                    label: `${project.title}`,
                    value: project.name,
                    description: project.name
                });
                codeToChartLabelMap[project.name!] = `${project.title}`
            });
            codeToChartLabelMap["Others"] = "Others";
            setProjectsFilter({
                loaded: true,
                options: filterOptions,
                status: "finished"
            });
            setProjectCodeToChartLabelMap(codeToChartLabelMap);
            setResProjects(projects.map((project) => project.name!));
            defaultProjects.current = filterOptions;
            defaultProjectsRef.current = projects.map((project) => project.name!);
        } catch (err: any) {
            setProjectsFilter({
                loaded: false,
                options: [],
                status: "error"
            })
            onFlashbarChange({
                items: [
                    {
                        type: "error",
                        header: "Failed to load projects from RES.",
                        content: "Please refresh the page and try again. If this error persists, please contact support.",
                        dismissible: true
                    }
                ]
            });
        }
    }

    const getTags = async (): Promise<CostExplorerGetTagsResult> => {
        let timePeriodStart = absoluteDateRange.startDate;
        let timePeriodEnd = absoluteDateRange.endDate;
        let searchEndDate = new Date(timePeriodEnd);
        searchEndDate.setDate(searchEndDate.getDate() + 1);
        timePeriodEnd = searchEndDate.toISOString().split("T")[0];
        if (granularity.value === "HOURLY") {
            timePeriodStart = timePeriodStart + "T00:00:00Z"
            timePeriodEnd = timePeriodEnd + "T00:00:00Z"
        }
        return proxyClient.costExplorerGetTags({
            TimePeriod: {
                Start: timePeriodStart,
                End: timePeriodEnd
            },
            TagKey: "res:Project",
            SortBy: [{
                Key: "UnblendedCost",
                SortOrder: "DESCENDING"
            }],
            Filter: {
                Tags: {
                    Key: "res:Project",
                    Values: resProjects
                }
            }
        });
    }

    const getTagsToDisplay = (getTagsResult: CostExplorerGetTagsResult): CostExplorerGetTagsResult => {
        if (selectedProjectsRef.current.length === 0) {
            if (getTagsResult.Tags.length > MAX_PROJECTS_TO_SHOW) {
                getTagsResult.Tags = getTagsResult.Tags.slice(0, MAX_PROJECTS_TO_SHOW);
                getTagsResult.Tags.push("Others");
            }
            return getTagsResult;
        } else {
            // Sort filter selections in order of total cost over time period
            let filteredProjects = getTagsResult.Tags.filter(value => selectedProjectsRef.current.includes(value));
            if (filteredProjects.length > MAX_PROJECTS_TO_SHOW) {
                filteredProjects = filteredProjects.slice(0, MAX_PROJECTS_TO_SHOW);
                filteredProjects.push("Others");
            }
            return { Tags: filteredProjects };
        }
    }

    const getCosts = async (nextPageToken: string = ""): Promise<GetCostAndUsageResult> => {
        let timePeriodStart = absoluteDateRange.startDate;
        let timePeriodEnd = absoluteDateRange.endDate;
        let searchEndDate = new Date(timePeriodEnd);
        searchEndDate.setDate(searchEndDate.getDate() + 1);
        timePeriodEnd = searchEndDate.toISOString().split("T")[0];
        if (granularity.value === "HOURLY") {
            timePeriodStart = timePeriodStart + "T00:00:00Z";
            timePeriodEnd = timePeriodEnd + "T00:00:00Z";
        }
        const options: GetCostAndUsageRequest = {
            TimePeriod: {
                Start: timePeriodStart,
                End: timePeriodEnd
            },
            Granularity: granularity.value!,
            Metrics: ["UnblendedCost"],
            GroupBy: [{
                Type: "TAG",
                Key: "res:Project"
            }],
            Filter: {
                Tags: {
                    Key: "res:Project",
                    Values: resProjects
                }
            }
        };
        if (selectedProjectsRef.current.length > 0) {
            options.Filter! = {
                And: [
                    {
                        Tags: {
                            Key: "res:Project",
                            Values: selectedProjectsRef.current
                        }
                    },
                    {
                        Not: {
                            Tags: {
                                Key: "res:Project",
                                Values: [""]
                            }
                        }
                    }
                ]
            };
        }
        if (nextPageToken !== "") {
            options.NextPageToken = nextPageToken;
        }
        const response = await proxyClient.getCostAndUsage(options);
        if (response.NextPageToken !== undefined) {
            const nextPage = await getCosts(response.NextPageToken);
            response.ResultsByTime = response.ResultsByTime.concat(nextPage.ResultsByTime);
            delete response.NextPageToken;
        }
        return response;
    }

    const formatXAxisDate = (xValue: string): string => {
        let formattedXValue: string;
        if (granularity.value === "MONTHLY") {
            formattedXValue = new Date(xValue).toLocaleDateString("en-US", {
                timeZone: "UTC",
                year: "numeric",
                month: "short"
            });
        } else if (granularity.value === "DAILY") {
            formattedXValue = new Date(xValue).toLocaleDateString("en-US", {
                timeZone: "UTC",
                year: "numeric",
                month: "short",
                day: "numeric"
            });
        } else {
            formattedXValue = new Date(xValue).toLocaleDateString("en-US", {
                timeZone: "UTC",
                year: "numeric",
                month: "short",
                day: "numeric",
                hour: "numeric",
                minute: "numeric"
            });
        }
        return formattedXValue;
    }

    const calculateCostsByCategory = (item: any, tags: string[]) => {
        return _.reduce(
            item.Groups,
            function(result: { [key: string]: number}, value) {
                const tag = value.Keys[0]
                const projectCodeTag = tag.substring(tag.indexOf("$") + 1)
                const cost = Number(value.Metrics.UnblendedCost.Amount);
                if (tags.includes(projectCodeTag)) {
                    result[projectCodeTag] = cost;
                } else {
                    if (result.Others !== undefined) {
                        result.Others += cost;
                    } else {
                        result.Others = cost;
                    }
                }
                return result;
            },
            {}
        );
    }

    const populateEmptyCostsChart = (xAxisSeries: string[]) => {
        let series: SeriesEntry[] = [];
        xAxisSeries.forEach((item) => {
            series.push({
                title: "Cost",
                type: BarChartType.Bar,
                data: [{
                    x: item,
                    y: 0
                }],
                valueFormatter: (e: number) =>
                "$" +
                e.toLocaleString("en-US", {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2
                })
            });
        });
        return series;
    }

    const populateCosts = async (): Promise<void> => {
        try {
            setBarChartStatus("loading");
            setIsEmptySeries(false);
            const currentRequestId = crypto.randomUUID();
            latestRequestIdRef.current = currentRequestId;
            const [getTagsResult, costResult] = await Promise.all([
                getTags(),
                getCosts()
            ]);
            setCsvDownloadParams({
                tagKey: COST_DASHBOARD_TAGS[0],
                getTagsResult: getTagsResult,
                getCostAndUsageResult: costResult
            });
            const tagsToDisplay = getTagsToDisplay({...getTagsResult});
            let xAxisSeries = [];
            let costsByTimePeriod = [];
            let costSumByXValue: { [key: string]: number } = {};

            for (const item of costResult.ResultsByTime) {
                const formattedXValue = formatXAxisDate(item.TimePeriod.Start);
                xAxisSeries.push(formattedXValue);
                const costsByCategory = calculateCostsByCategory(item, tagsToDisplay.Tags);
                costsByTimePeriod.push({
                    xValue: formattedXValue,
                    costs: costsByCategory
                });
                let costSum = 0;
                _.forEach(costsByCategory, function (value, key) {
                    costSum += value;
                });
                costSumByXValue[formattedXValue] = costSum;
            }

            let series = [];
            for (const projectCode of tagsToDisplay.Tags) {
                const userFriendlyTagLabel = projectCodeToChartLabelMap[projectCode]
                let data: { x: string, y: number }[] = [];
                costsByTimePeriod.forEach((item) => {
                    if (item.costs[projectCode] !== undefined) {
                        data.push({
                            x: item.xValue,
                            y: item.costs[projectCode]
                        });
                    }
                })
                series.push({
                    title: userFriendlyTagLabel,
                    type: BarChartType.Bar,
                    data: data,
                    valueFormatter: (e: number) =>
                    "$" +
                    e.toLocaleString("en-US", {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2
                    })
                });
            }

            if (latestRequestIdRef.current === currentRequestId) {
                if (series.length === 0 || selectedProjectsRef.current.length === 0) {
                    series = [];
                    setIsEmptySeries(true);
                }
                setSeries(series);
                setXDomain(xAxisSeries);
                setCostSumByXValue(costSumByXValue);
                setBarChartStatus("finished");
            }
        } catch (error) {
            setBarChartStatus("error");
        }
    }

    const loadFiltersFromLocalStorage = async () => {
        const projectsLocal = AppContext.get().localStorage().getItem(`${PROJECTS_FILTER_SESSION_KEY}`);
        const projectsRefLocal = AppContext.get().localStorage().getItem(`${PROJECTS_REF_FILTER_SESSION_KEY}`);
        const granularityLocal = AppContext.get().localStorage().getItem(`${GRANULARITY_FILTER_SESSION_KEY}`);
        const dateRangeLocal = AppContext.get().localStorage().getItem(`${DATE_RANGE_FILTER_SESSION_KEY}`);
        const relativeDateRangeLocal = AppContext.get().localStorage().getItem(`${RELATIVE_DATE_RANGE_FILTER_SESSION_KEY}`);
        const shouldUseRelativeDateRange = AppContext.get().localStorage().getItem(`${SHOULD_USE_RELATIVE_DATE_RANGE_SESSION_KEY}`);
        if (projectsLocal !== null && projectsRefLocal !== null) {
            setSelectedProjects(JSON.parse(projectsLocal));
            selectedProjectsRef.current = JSON.parse(projectsRefLocal);
        }
        else {
            setSelectedProjects(defaultProjects.current);
            selectedProjectsRef.current = defaultProjectsRef.current;
        }
        if (granularityLocal !== null) {
            setGranularity(JSON.parse(granularityLocal));
        }
        if (dateRangeLocal !== null) {
            setAbsoluteDateRange(JSON.parse(dateRangeLocal));
        }
        if (relativeDateRangeLocal !== null) {
            setRelativeDateRange(JSON.parse(relativeDateRangeLocal));
        }
        if (shouldUseRelativeDateRange !== null) {
            setShouldUseRelativeDateRange(shouldUseRelativeDateRange === 'true');
        }
    }

    const saveFiltersToLocalStorage = async () => {
        AppContext.get().localStorage().setItem(`${PROJECTS_FILTER_SESSION_KEY}`, JSON.stringify(selectedProjects));
        AppContext.get().localStorage().setItem(`${PROJECTS_REF_FILTER_SESSION_KEY}`, JSON.stringify(selectedProjectsRef.current));
        AppContext.get().localStorage().setItem(`${GRANULARITY_FILTER_SESSION_KEY}`, JSON.stringify(granularity));
        AppContext.get().localStorage().setItem(`${DATE_RANGE_FILTER_SESSION_KEY}`, JSON.stringify(absoluteDateRange));
        AppContext.get().localStorage().setItem(`${RELATIVE_DATE_RANGE_FILTER_SESSION_KEY}`, JSON.stringify(relativeDateRange));
        AppContext.get().localStorage().setItem(`${SHOULD_USE_RELATIVE_DATE_RANGE_SESSION_KEY}`, shouldUseRelativeDateRange.toString());
    }

    useEffect(() => {
        if (resProjects.length > 0) {
            populateCosts();
        }
    }, [absoluteDateRange, granularity, resProjects]);

    useEffect(() => {
        loadProjectsFromRes();
        loadFiltersFromLocalStorage();
    }, []);

    // Saving filters after the chart series loads to ensure we have the latest
    // filter values in the state variables.
    useEffect(() => {
        saveFiltersToLocalStorage();
    }, [series]);

    return (
        <Container
            header={<Header
                variant={"h3"}
                actions={
                    <SpaceBetween size={"xs"} direction={"horizontal"}>
                        <Button
                            variant="normal"
                            iconName="refresh"
                            onClick={() => populateCosts()}
                        />
                        <CsvDownloader columns={csvColumnHeaders} datas={csvData} filename="costs">
                            <Button
                                iconName="download"
                                variant="primary"
                                disabled={barChartStatus !== "finished"}
                                iconAlign="right"
                            >
                                Download CSV
                            </Button>
                        </CsvDownloader>
                    </SpaceBetween>
                }
                description={
                    <SpaceBetween size={"xxxs"} direction={"vertical"}>
                        <TextContent>
                            <p><small>Track expenses incurred over a period of time.</small></p>
                        </TextContent>
                    </SpaceBetween>
                }
            >
                    Cost analysis over time
            </Header>
        }
            footer={<ExpandableSection
                headerText="Display settings"
                variant="footer"
            >
                <ColumnLayout columns={2} variant={"text-grid"}>
                    <ColumnLayout columns={1} variant={"text-grid"}>
                        <ProjectsFilter
                            selectedProjects={selectedProjects}
                            selectedProjectsRef={selectedProjectsRef}
                            projectsFilter={projectsFilter}
                            setSelectedProjects={setSelectedProjects}
                            populateCosts={populateCosts}
                        />
                    </ColumnLayout>
                    <ColumnLayout columns={1} variant={"text-grid"}>
                        <SpaceBetween size={"xxxs"} direction="vertical">
                            <Header>
                                <Box color="text-body-secondary" fontWeight="bold">Time range</Box>
                            </Header>
                            <DateRangeFilter
                                granularity={granularity}
                                absoluteDateRange={absoluteDateRange}
                                setGranularity={setGranularity}
                                setAbsoluteDateRange={setAbsoluteDateRange}
                                setModalParams={setModalParams}
                                setModalVisible={setModalVisible}
                                shouldUseRelativeDateRange={shouldUseRelativeDateRange}
                                setShouldUseRelativeDateRange={setShouldUseRelativeDateRange}
                                relativeDateRange={relativeDateRange}
                                setRelativeDateRange={setRelativeDateRange}
                            />
                        </SpaceBetween>
                        <SpaceBetween size={"xxxs"} direction="vertical">
                            <Header>
                                <Box color="text-body-secondary" fontWeight="bold">Granularity</Box>
                            </Header>
                            <GranularityFilter
                                granularity={granularity}
                                absoluteDateRange={absoluteDateRange}
                                setGranularity={setGranularity}
                                setAbsoluteDateRange={setAbsoluteDateRange}
                                setModalParams={setModalParams}
                                setModalVisible={setModalVisible}
                                setShouldUseRelativeDateRange={setShouldUseRelativeDateRange}
                            />
                        </SpaceBetween>
                    </ColumnLayout>
                </ColumnLayout>
            </ExpandableSection>
        }>

            <Modal
                onDismiss={() => setModalVisible(false)}
                visible={modalVisible}
                footer={
                    <Box float="right">
                        <SpaceBetween direction="horizontal" size="xs">
                            <Button variant="link" onClick={() => modalParams.onCancel? modalParams.onCancel() : setModalVisible(false)}>Cancel</Button>
                            <Button variant="primary"
                                onClick={modalParams.onClick}
                            >
                                Continue
                            </Button>
                        </SpaceBetween>
                    </Box>
                }
                header={modalParams.headerText}
                >
                {modalParams.bodyText}
            </Modal>
            <CostAnalysisChart
                series={series}
                barChartStatus={barChartStatus}
                xDomain={xDomain}
                costSumByXValue={costSumByXValue}
                isEmptySeries={isEmptySeries}
            />
        </Container>
    )
}

export default CostAnalysisWidget;
