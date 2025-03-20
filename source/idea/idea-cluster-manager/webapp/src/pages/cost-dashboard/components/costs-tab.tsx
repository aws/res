import * as _ from "lodash";
import { Box, Button, SpaceBetween, Spinner } from "@cloudscape-design/components";
import CurrentBudgetWidget from "./current-budget-widget";
import ProxyClient from "../../../client/proxy-client";
import { IdeaAppLayoutProps } from "../../../components/app-layout";
import { IdeaSideNavigationProps } from "../../../components/side-navigation";
import CostAnalysisWidget from "./cost-analysis-widget";
import CostAnalysisTagsEnableWidget from "./cost-analysis-tags-enable-widget";
import { ListCostAllocationTagsRequest, UpdateCostAllocationTagsStatusRequest } from "../../../client/data-model";
import { ProjectsClient } from "../../../client";
import { AppContext } from "../../../common";
import { ListProjectsResult } from "../../../client/data-model";
import { useEffect, useState } from "react";
import { COST_DASHBOARD_TAGS } from "../utils/cost-dashboard-constants";


export interface CostsTabProps extends IdeaAppLayoutProps, IdeaSideNavigationProps { }

const CostsTab: React.FC<CostsTabProps> = (props) => {
    const [projects, setProjects] = useState<ListProjectsResult | null>(null);
    const [isTagsActive, setIsTagsActive] = useState<boolean>(false);
    const [isEnableTagsButtonActive, setIsEnableTagsButtonActive] = useState<boolean>(true);
    const [isEnableTagsButtonLoading, setIsEnableTagsButtonLoading] = useState<boolean>(false);
    const [isProjectsLoading, setIsProjectsLoading] = useState<boolean>(true);

    const proxyClient: ProxyClient = AppContext.get().client().proxy();

    const getActiveCostAllocationTags = async () => {
        const options: ListCostAllocationTagsRequest = {
            TagKeys: COST_DASHBOARD_TAGS,
            Type: "UserDefined"
        };
        return proxyClient.listCostAllocationTags(options);
    }

    const updateCostAllocationTags = async (shouldEnable: boolean) => {
        const tagsToUpdate: { Status: "Active" | "Inactive", TagKey: string }[] = [];
        _.forEach(COST_DASHBOARD_TAGS, function (value) {
            tagsToUpdate.push({
                TagKey: value,
                Status: shouldEnable ? "Active" : "Inactive"
            });
        });
        const options: UpdateCostAllocationTagsStatusRequest = {
            CostAllocationTagsStatus: tagsToUpdate
        };
        return proxyClient.updateCostAllocationTagsStatus(options);
    }

    const retrieveCostAllocationTagsStatus = async (): Promise<void> => {
        try {
            setIsProjectsLoading(true);
            const activeTags = await getActiveCostAllocationTags();
            if (activeTags.CostAllocationTags.length < COST_DASHBOARD_TAGS.length) {
                setIsTagsActive(false);
                setIsEnableTagsButtonActive(false);
            } else {
                let isAllTagsActive = true;
                _.forEach(activeTags.CostAllocationTags, function (value) {
                    if (value.Status === "Inactive") {
                        isAllTagsActive = false;
                    }
                });
                setIsTagsActive(isAllTagsActive);
                setIsEnableTagsButtonActive(true);
            }
        } catch (error: any) {
            setIsTagsActive(false);
            setIsEnableTagsButtonActive(false);
        } finally {
            setIsProjectsLoading(false);
        }
    }

    const enableCostAllocationTags = async (): Promise<void> => {
        try {
            setIsEnableTagsButtonActive(false);
            setIsEnableTagsButtonLoading(true);
            const response = await updateCostAllocationTags(true);
            if (response.Errors.length > 0) {
                props.onFlashbarChange({
                    items: [
                        {
                            type: "error",
                            header: "Failed to enable cost allocation tags.",
                            content: "Please refresh the page and try again. If this error persists, please contact support.",
                            dismissible: true
                        }
                    ]
                });
            } else {
                props.onFlashbarChange({
                    items: [
                        {
                            type: "success",
                            content: "Successfully enabled cost allocation tags. Please wait 24 hours for your changes to take effect.",
                            dismissible: true,
                        }
                    ]
                });
            }
        } catch (error: any) {
            props.onFlashbarChange({
                items: [
                    {
                        type: "error",
                        header: "Failed to enable cost allocation tagss.",
                        content: "Please refresh the page and try again. If this error persists, please contact support.",
                        dismissible: true
                    }
                ]
            });
        } finally {
            setIsEnableTagsButtonActive(true);
            setIsEnableTagsButtonLoading(false);
        }
    }

    useEffect(() => {
        retrieveCostAllocationTagsStatus();
    }, []);

    useEffect(() => {
        const fetchProjects = async () => {
            try {
                const projectsClient: ProjectsClient = AppContext.get().client().projects();
                const response: ListProjectsResult = await projectsClient.listProjects({
                    sort_by: {
                        key: "alphabetical",
                        order: "asc"
                    }
                });
                if (response) {
                    setProjects(response);
                }
            } catch (err) {
                props.onFlashbarChange({
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
        };

        fetchProjects();
    }, []);

    if (!projects || !projects.listing || projects.listing.length === 0) {
        return (
            <Box textAlign="center" color="text-status-inactive" padding={{ top: "xxxl", bottom: "s" }}>
                <b>No projects available.</b>
                <Box padding={{ top: "s", bottom: "s" }} variant="p" color="text-status-inactive">
                    Get started creating a project and assigning a budget. Budget assignment is necessary for project tracking and display.
                </Box>
                <Button
                    variant="normal"
                    onClick={() => props.navigate("/cluster/projects/configure")}
                >
                    Create project
                </Button>
            </Box>
        );
    }

    return (
        <SpaceBetween size="m">
            <CurrentBudgetWidget navigate={props.navigate} />
            {isProjectsLoading &&
                <Box color="text-body-secondary" textAlign="center">
                    Loading cost analysis <Spinner />
                </Box>
            }
            {
                !isTagsActive &&
                !isProjectsLoading &&
                <CostAnalysisTagsEnableWidget
                    navigate={props.navigate}
                    onToolsChange={props.onToolsChange}
                    isEnableTagsButtonActive={isEnableTagsButtonActive}
                    isEnableTagsButtonLoading={isEnableTagsButtonLoading}
                    enableCostAllocationTags={enableCostAllocationTags}
                />
            }
            {
                isTagsActive &&
                !isProjectsLoading &&
                <CostAnalysisWidget onFlashbarChange={props.onFlashbarChange} response={projects} />
            }
        </SpaceBetween>
    );
};

export default CostsTab;