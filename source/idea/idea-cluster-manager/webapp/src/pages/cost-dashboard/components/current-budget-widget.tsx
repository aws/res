import { useState, useEffect, useRef } from "react";
import { Container, Header, Button, SpaceBetween, BarChart, Box, ExpandableSection, ColumnLayout, SelectProps } from "@cloudscape-design/components";
import { colorChartsPaletteCategorical1, colorChartsThresholdNegative, colorBackgroundControlDisabled } from '@cloudscape-design/design-tokens';
import { ListProjectsResult, SocaFilter } from "../../../client/data-model";
import { AppContext } from "../../../common";
import { ProjectsClient } from "../../../client/";
import ProjectsFilter from "./projects-filter";
import { OptionDefinition } from "@cloudscape-design/components/internal/components/option/interfaces";

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

export interface CurrentBudgetProps {
    navigate: (path: string) => void;
}

const CurrentBudgetWidget = (props: CurrentBudgetProps) => {
    const { navigate } = props;
    const [barChartStatus, setBarChartStatus] = useState<"loading" | "finished" | "error">("loading");
    const [series, setSeries] = useState<SeriesEntry[]>([]);
    const [projectsFilter, setProjectsFilter] = useState<DropdownFilterOptions>({
        options: [],
        loaded: false,
        status: "loading"
    });
    const [selectedProjects, setSelectedProjects] = useState<readonly OptionDefinition[]>([]);
    const selectedProjectsRef = useRef<string[]>([]);

    const fetchBudgets = async (filter: SocaFilter[] = []) => {
        const projectsClient: ProjectsClient = AppContext.get().client().projects();
        const response: ListProjectsResult = await projectsClient.listProjects({ filters: filter });
        const projects = response.listing || [];
        const filteredProjects = projects.filter((project) => project.enable_budgets);
        const projectsWithBudgetUsage = filteredProjects.map((project) => {
            const actualSpend = project.budget!.actual_spend!.amount;
            const budgetLimit = project.budget!.budget_limit!.amount;
            const spent = actualSpend;
            const exceeding = actualSpend > budgetLimit ? actualSpend - budgetLimit : 0;
            const remaining = actualSpend <= budgetLimit ? budgetLimit - actualSpend : 0;
            return {
                ...project,
                spent,
                exceeding,
                remaining
            };
        });
        const sortedProjects = projectsWithBudgetUsage.sort((a, b) => b.spent - a.spent);
        return sortedProjects;
    };

    const populateFilterOptions = async () => {
        try {
            const projects = await fetchBudgets();
            const filterOptions: any[] = projects.map((project) => ({
                label: `${project.title}`,
                value: project.name,
                description: project.name
            }));
            setProjectsFilter({
                loaded: true,
                options: filterOptions,
                status: "finished"
            });

            const topProjects = projects.slice(0, 5);
            setSelectedProjects(topProjects.map(project => ({
                label: `${project.title}`,
                value: project.name,
                description: project.name
            })));
            selectedProjectsRef.current = topProjects.map(project => project.name).filter((name): name is string => name !== undefined);
        } catch (error) {
            setProjectsFilter({
                loaded: false,
                options: [],
                status: "error"
            });
        }
    };

    const populateBudget = async (): Promise<void> => {
        try {
            setBarChartStatus("loading");

            const selectedProjectsArray = selectedProjectsRef.current;
            const filter: SocaFilter[] = selectedProjectsArray.map(selection => ({
                key: "name",
                eq: selection
            }));

            if (filter.length === 0) {
                setSeries([]);
                setBarChartStatus("finished");
                return;
            }

            const projects = await fetchBudgets(filter);

            const categories = [
                { key: 'spent', label: 'Spent', color: colorChartsPaletteCategorical1 },
                { key: 'exceeding', label: 'Exceeding', color: colorChartsThresholdNegative },
                { key: 'remaining', label: 'Remaining', color: colorBackgroundControlDisabled }
            ];

            const seriesData: SeriesEntry[] = categories.map(category => ({
                title: category.label,
                type: BarChartType.Bar,
                data: projects.map(project => ({
                    x: `${project.title}`,
                    y: project[category.key as 'spent' | 'exceeding' | 'remaining'],
                })),
                color: category.color,
                valueFormatter: (e: number) =>
                    e.toLocaleString("en-US", {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2
                    }) + " USD",
            }));

            setSeries(seriesData);
            setBarChartStatus("finished");
        } catch (error) {
            setBarChartStatus("error");
        }
    };

    const buildBarChart = () => (
        <BarChart
            ariaLabel="Single data series line chart"
            series={series}
            statusType={barChartStatus}
            loadingText="Loading chart"
            height={300}
            horizontalBars={true}
            hideFilter={true}
            xTitle="Project name"
            yTitle="Budget (USD)"
            stackedBars={true}
            errorText="Error loading data. Please refresh the chart."
            empty={
                <Box textAlign="center" color="inherit">
                    <b>No data displayed</b>
                    <Box variant="p" color="inherit">
                        To display data expand and modify the display settings below.
                    </Box>
                </Box>
            }
        />
    );

    useEffect(() => {
        const initialize = async () => {
            await populateFilterOptions();
            populateBudget();
        };

        initialize();
    }, []);

    return (
        <Container
            header={
                <Header
                    variant={"h3"}
                    description="Track the current status of budgets. Budget assignment is necessary for project tracking and display."
                    actions={
                        <SpaceBetween size={"s"} direction="horizontal" alignItems="center">
                            <Button
                                iconName="refresh"
                                variant="normal"
                                onClick={() => populateBudget()}
                            ></Button>
                            <Button
                                variant="normal"
                                onClick={() => navigate("/cluster/projects")}
                            >
                                Review projects
                            </Button>
                            <Button
                                variant="normal"
                                onClick={() => navigate("/cluster/projects/configure")}
                            >
                                Create project
                            </Button>
                        </SpaceBetween>
                    }
                >
                    Projects with budget assigned
                </Header>
            }
            footer={
                <ExpandableSection
                    headerText="Display settings"
                    variant="footer"
                >
                    <ColumnLayout columns={2}>
                        <ProjectsFilter
                            selectedProjects={selectedProjects}
                            selectedProjectsRef={selectedProjectsRef}
                            projectsFilter={projectsFilter}
                            setSelectedProjects={setSelectedProjects}
                            populateCosts={populateBudget}
                        />
                    </ColumnLayout>
                </ExpandableSection>
            }
        >
            {buildBarChart()}
        </Container>
    )
}
export default CurrentBudgetWidget;