import * as _ from "lodash";
import { useState } from "react";
import { Box, Header, Multiselect, SelectProps, SpaceBetween } from "@cloudscape-design/components";
import { OptionDefinition } from "@cloudscape-design/components/internal/components/option/interfaces";

export interface DropdownFilterOptions {
    options: SelectProps.Options
    status: "pending" | "loading" | "finished" | "error"
    loaded: boolean
}

export interface ProjectsFilterProps {
    selectedProjects: readonly OptionDefinition[]
    selectedProjectsRef: React.MutableRefObject<string[]>
    projectsFilter: DropdownFilterOptions
    setSelectedProjects: React.Dispatch<React.SetStateAction<readonly OptionDefinition[]>>
    populateCosts: () => Promise<void>;
}

const ProjectsFilter = ({ selectedProjects, selectedProjectsRef, projectsFilter, setSelectedProjects, populateCosts }: ProjectsFilterProps) => {
    const [projectsChanged, setProjectsChanged] = useState<boolean>(false);

    return (
        <SpaceBetween size={"xxxs"} direction="vertical">
            <Header>
                <Box color="text-body-secondary" fontWeight="bold">Filter displayed data</Box>
            </Header>
            <Multiselect
                selectedOptions={selectedProjects}
                options={projectsFilter.options}
                filteringType="auto"
                errorText="Error loading projects. Please refresh the page."
                recoveryText="Reload"
                empty="No projects found"
                statusType={projectsFilter.status}
                onChange={({ detail }: any) => {
                    selectedProjectsRef.current = _.map(detail.selectedOptions, "value")
                    setSelectedProjects(detail.selectedOptions);
                    if (detail.selectedOptions.length < selectedProjects.length) {
                        populateCosts();
                    } else {
                        setProjectsChanged(true);
                    }
                }}
                placeholder="Find project by name"
                i18nStrings={{
                    tokenLimitShowMore: "Show more chosen projects",
                    tokenLimitShowFewer: "Show fewer chosen projects",
                }}
                tokenLimit={5}
                onBlur={() => {
                    if (projectsChanged) {
                        setProjectsChanged(false);
                        populateCosts();
                    }
                }}
            />
        </SpaceBetween>
    )
}

export default ProjectsFilter;
