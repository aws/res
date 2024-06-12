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

import React, { Component, RefObject } from "react";

import { TableProps } from "@cloudscape-design/components/table/interfaces";
import { ListGroupsResult, Project, RoleAssignment } from "../../client/data-model";
import IdeaListView from "../../components/list-view";
import { AccountsClient, ClusterSettingsClient, ProjectsClient } from "../../client";
import { AppContext } from "../../common";
import { Box, Button, Header, Modal, ProgressBar, SpaceBetween, StatusIndicator, TagEditor } from "@cloudscape-design/components";
import Utils from "../../common/utils";
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import IdeaAppLayout, { IdeaAppLayoutProps } from "../../components/app-layout";
import { withRouter } from "../../navigation/navigation-utils";
import IdeaSplitPanel from "../../components/split-panel";
import { SharedStorageFileSystem } from "../../common/shared-storage-utils";
import { FILESYSTEM_TABLE_COLUMN_DEFINITIONS } from "./filesystem";
import FilesystemClient from "../../client/filesystem-client";

export interface ProjectsProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {
  projectOwnerRoles?: string[]
}

export interface ProjectsState {
    projectSelected: boolean;
    showTagEditor: boolean;
    tags: any[];
    splitPanelOpen: boolean;
    projectAssignments: {
      [key: string]: RoleAssignment[];
    },
}

const PROJECT_TABLE_COLUMN_DEFINITIONS: TableProps.ColumnDefinition<Project>[] = [
    {
        id: "title",
        header: "Title",
        cell: (project) => project.title,
    },
    {
        id: "name",
        header: "Project Code",
        cell: (project) => project.name,
    },
    {
        id: "enabled",
        header: "Status",
        cell: (project) => (project.enabled ? <StatusIndicator type="success">Enabled</StatusIndicator> : <StatusIndicator type="stopped">Disabled</StatusIndicator>),
    },
    {
        id: "budgets",
        header: "Budgets",
        minWidth: 240,
        cell: (project) => {
            if (project.enable_budgets) {
                if (project.budget) {
                    const actualSpend = Utils.asNumber(project.budget.actual_spend?.amount, 0);
                    const limit = Utils.asNumber(project.budget.budget_limit?.amount, 0);
                    const usage = (actualSpend / limit) * 100;
                    return (
                        <ProgressBar
                            status={actualSpend > limit ? "error" : "in-progress"}
                            value={usage}
                            resultButtonText="Budget Exceeded"
                            additionalInfo={`Limit: ${Utils.getFormattedAmount(project.budget.budget_limit)}, Forecasted: ${Utils.getFormattedAmount(project.budget.forecasted_spend)}`}
                            description={`Actual Spend for budget: ${project.budget.budget_name}`}
                        />
                    );
                }
            } else {
                return <span style={{ color: "grey" }}> -- </span>;
            }
        },
    },
    {
        id: "ldap-group",
        header: "Groups",
        cell: (project) => {
            if (project.ldap_groups && project.ldap_groups.length !== 0) {
                return (
                    <div>
                        {project.ldap_groups.map((ldap_group, index) => {
                            return <li key={index}>{ldap_group}</li>;
                        })}
                    </div>
                );
            } else {
                return "-";
            }
        },
    },
    {
        id: "user",
        header: "Users",
        cell: (project) => {
            if (project.users && project.users.length !== 0) {
                return (
                    <div>
                        {project.users.map((user, index) => {
                            return <li key={index}>{user}</li>;
                        })}
                    </div>
                );
            } else {
                return "-";
            }
        },
    },
    {
        id: "updated_on",
        header: "Updated On",
        cell: (project) => new Date(project.updated_on!).toLocaleString(),
    },
];

class Projects extends Component<ProjectsProps, ProjectsState> {
    listing: RefObject<IdeaListView>;
    filesystemListing: RefObject<IdeaListView>;

    constructor(props: ProjectsProps) {
        super(props);
        this.listing = React.createRef();
        this.filesystemListing = React.createRef();
        this.state = {
            projectSelected: false,
            showTagEditor: false,
            tags: [],
            splitPanelOpen: false,
            projectAssignments: {},
        };
    }

    projects(): ProjectsClient {
        return AppContext.get().client().projects();
    }

    listSharedStorageFileSystem(project_name: string) {
        return this.projects()
            .listFileSystemsForProject({ project_name: project_name })
            .then((data) => {
                const _result: SharedStorageFileSystem[] = [];
                data.listing?.forEach((item) => {
                    _result.push(new SharedStorageFileSystem(item.name!, item.storage));
                });
                return { ...data, listing: _result };
            });
    }

    accounts(): AccountsClient {
        return AppContext.get().client().accounts();
    }

    filesystem(): FilesystemClient {
        return AppContext.get().client().filesystem();
    }

    getListing(): IdeaListView {
        return this.listing.current!;
    }

    getFileSystemListing(): IdeaListView {
        return this.filesystemListing.current!;
    }


    isSelected(): boolean {
        return this.state.projectSelected;
    }

    isAdmin(): boolean {
      return AppContext.get().auth().isAdmin();
    }

    isSelectedProjectEnabled(): boolean {
        if (!this.isSelected()) {
            return false;
        }
        const selectedProject = this.getSelected();
        if (selectedProject == null) {
            return false;
        }
        if (selectedProject.enabled != null) {
            return selectedProject.enabled;
        }
        return false;
    }

    getSelected(): Project | null {
        if (this.getListing() == null) {
            return null;
        }
        return this.getListing().getSelectedItem();
    }
    clusterSettings(): ClusterSettingsClient {
        return AppContext.get().client().clusterSettings();
    }

    async getOwnerProjectsWithGroups(context: AppContext, allProjects: Project[]): Promise<Project[]> {
      const username: string = context.auth().getUsername();
      const groups: string[] = await new Promise(resolve => {
          context.client().accounts().listGroups({
              username,
          })
          .then((result: ListGroupsResult) => {
            resolve(result.listing?.map(x => `${x.name!}:group`) || []);
          });
      });
      const userGroupRoleAssignments: Promise<void>[] = [];
      const projects: Map<string, Project> = new Map();
      const ownerProjectIds: string[] = [];
      for (const actor_key of [...groups, `${username}:user`]) {
        // resolves to true if one of the returned roles is project_owner
        userGroupRoleAssignments.push(Promise.resolve(
          context.client().authz().listRoleAssignments({
            actor_key,
          })
          .then((result) => {
            for (const roleAssignment of result.items) {
              let update = {
                ldap_groups: [] as string[],
                users: [] as string[],
              };
              if (projects.has(roleAssignment.resource_id!)) {
                update = {
                  ldap_groups: projects.get(roleAssignment.resource_id!)?.ldap_groups ?? [],
                  users: projects.get(roleAssignment.resource_id!)?.users ?? [],
                }
              } else {
                let project = allProjects.find(x => x.project_id! === roleAssignment.resource_id);
                if (!project) continue;
                projects.set(roleAssignment.resource_id, project);
              }
              if (roleAssignment.actor_type === "group") {
                update.ldap_groups.push(roleAssignment.actor_id);
              } else if (roleAssignment.actor_type === "user") {
                update.users.push(roleAssignment.actor_id);
              }
              // if we already have a mapping, use that. Otherwise, use the base project
              projects.set(roleAssignment.resource_id!, {...projects.get(roleAssignment.resource_id!), ...update});
              if (roleAssignment.role_id === "project_owner") {
                ownerProjectIds.push(roleAssignment.resource_id);
              }
              console.log(projects);
            }
          })
        ));
      }
      await Promise.all(userGroupRoleAssignments);
      return Array.from(projects.values()).filter(project => {
        return ownerProjectIds.includes(project.project_id!);
      });
    };

    async getProjectsWithRoles(projects: Project[]): Promise<Project[]> {
      const authzClient = AppContext.get().client().authz();
      const requests = [];
      for (const project of projects) {
        requests.push(
          authzClient.listRoleAssignments({
            resource_key: `${project.project_id!}:project`,
          })
          .then((result) => {
            const groups: string[] = [];
            const users: string[]  = [];
            for (const roleAssignment of result.items) {
              if (roleAssignment.actor_type === "group") {
                groups.push(roleAssignment.actor_id);
              } else if (roleAssignment.actor_type === "user") {
                users.push(roleAssignment.actor_id);
              }
            }
            project.ldap_groups = groups;
            project.users = users;
          })
        );
      }
      await Promise.all(requests);
      return projects;
    }

    buildTagEditor() {
        const onCancel = () => {
            this.hideTagEditor();
        };

        const onSubmit = () => {
            this.projects()
                .updateProject({
                    project: {
                        ...this.getSelected(),
                        tags: this.state.tags,
                    },
                })
                .then(() => {
                    this.props.onFlashbarChange({
                        items: [
                            {
                                type: "success",
                                content: `Tags updated for project: ${this.getSelected()?.name}`,
                                dismissible: true,
                            },
                        ],
                    });
                    this.getListing().fetchRecords();
                    this.hideTagEditor();
                });
        };

        return (
            <Modal
                size="large"
                visible={this.state.showTagEditor}
                onDismiss={onCancel}
                header={<Header variant="h3">Tags: {this.getSelected()?.title}</Header>}
                footer={
                    <Box float="right">
                        <SpaceBetween direction="horizontal" size="xs">
                            <Button variant="link" onClick={onCancel}>
                                Cancel
                            </Button>
                            <Button variant="primary" onClick={onSubmit}>
                                Submit
                            </Button>
                        </SpaceBetween>
                    </Box>
                }
            >
                <TagEditor
                    tags={this.state.tags}
                    tagLimit={20}
                    onChange={(event) => {
                        const tags: any[] = [];
                        event.detail.tags.forEach((tag) => {
                            tags.push({
                                key: tag.key,
                                value: tag.value,
                            });
                        });
                        this.setState({
                            tags: tags,
                        });
                    }}
                    i18nStrings={{
                        keyPlaceholder: "Enter key",
                        valuePlaceholder: "Enter value",
                        addButton: "Add new tag",
                        removeButton: "Remove",
                        undoButton: "Undo",
                        undoPrompt: "This tag will be removed upon saving changes",
                        loading: "Loading tags that are associated with this resource",
                        keyHeader: "Key",
                        valueHeader: "Value",
                        optional: "optional",
                        keySuggestion: "Custom tag key",
                        valueSuggestion: "Custom tag value",
                        emptyTags: "No tags associated with the resource.",
                        tooManyKeysSuggestion: "You have more keys than can be displayed",
                        tooManyValuesSuggestion: "You have more values than can be displayed",
                        keysSuggestionLoading: "Loading tag keys",
                        keysSuggestionError: "Tag keys could not be retrieved",
                        valuesSuggestionLoading: "Loading tag values",
                        valuesSuggestionError: "Tag values could not be retrieved",
                        emptyKeyError: "You must specify a tag key",
                        maxKeyCharLengthError: "The maximum number of characters you can use in a tag key is 128.",
                        maxValueCharLengthError: "The maximum number of characters you can use in a tag value is 256.",
                        duplicateKeyError: "You must specify a unique tag key.",
                        invalidKeyError: "Invalid key. Keys can only contain alphanumeric characters, spaces and any of the following: _.:/=+@-",
                        invalidValueError: "Invalid value. Values can only contain alphanumeric characters, spaces and any of the following: _.:/=+@-",
                        awsPrefixError: "Cannot start with aws:",
                        tagLimit: (availableTags) => (availableTags === 1 ? "You can add up to 1 more tag." : "You can add up to " + availableTags + " more tags."),
                        tagLimitReached: (tagLimit) => (tagLimit === 1 ? "You have reached the limit of 1 tag." : "You have reached the limit of " + tagLimit + " tags."),
                        tagLimitExceeded: (tagLimit) => (tagLimit === 1 ? "You have exceeded the limit of 1 tag." : "You have exceeded the limit of " + tagLimit + " tags."),
                        enteredKeyLabel: (key) => 'Use "' + key + '"',
                        enteredValueLabel: (value) => 'Use "' + value + '"',
                    }}
                />
            </Modal>
        );
    }

    showTagEditor() {
        const tags: any[] = [];
        const selected = this.getSelected();
        if (selected != null) {
            selected.tags?.forEach((tag) => {
                tags.push({
                    key: tag.key,
                    value: tag.value,
                });
            });
        }
        this.setState({
            showTagEditor: true,
            tags: tags,
        });
    }

    hideTagEditor() {
        this.setState({
            showTagEditor: false,
            tags: [],
        });
    }

    buildListing() {
        return (
            <IdeaListView
                ref={this.listing}
                preferencesKey={"projects"}
                showPreferences={false}
                title="Projects"
                description={`Environment Project Management.${this.isAdmin() ? "" : " These are the projects of which you are an owner."}`}
                selectionType="single"
                primaryAction={{
                    id: "create-project",
                    text: "Create Project",
                    onClick: () => {
                        this.props.navigate("/cluster/projects/configure")
                    },
                }}
                primaryActionDisabled={!this.isAdmin()}
                secondaryActionsDisabled={!this.isSelected()}
                secondaryActions={[
                    {
                        id: "edit-project",
                        text: "Edit Project",
                        onClick: () => {
                            const selectedProject = this.getSelected();
                            AppContext.get().client().authz().listRoleAssignments({
                              resource_key: `${selectedProject!.project_id!}:project`,
                            })
                            .then((result) => {
                              this.props.navigate("/cluster/projects/configure", { state: { isUpdate: true, project: selectedProject, projectRoles: result.items }})
                            });
                        },
                    },
                    {
                        id: "toggle-enable-project",
                        text: this.isSelectedProjectEnabled() ? "Disable Project" : "Enable Project",
                        onClick: () => {
                            let enableOrDisable;
                            if (this.isSelectedProjectEnabled()) {
                                enableOrDisable = (request: any) => this.projects().disableProject(request);
                            } else {
                                enableOrDisable = (request: any) => this.projects().enableProject(request);
                            }
                            enableOrDisable({
                                project_id: this.getSelected()?.project_id,
                            })
                                .then(() => {
                                    this.getListing().fetchRecords();
                                })
                                .catch((error) => {
                                    this.props.onFlashbarChange({
                                        items: [
                                            {
                                                type: "error",
                                                content: `Operation failed: ${error.message}`,
                                                dismissible: true,
                                            },
                                        ],
                                    });
                                });
                        },
                        disabled: !this.isAdmin(),
                    },
                    {
                        id: "update-tags",
                        text: "Update Tags",
                        onClick: () => {
                            this.showTagEditor();
                        },
                        disabled: !this.isAdmin(),
                    },
                ]}
                showPaginator={true}
                showFilters={true}
                filters={[
                    {
                        key: "name",
                    },
                ]}
                onFilter={(filters) => {
                    const projectNameToken = Utils.asString(filters[0].value).trim().toLowerCase();
                    if (Utils.isEmpty(projectNameToken)) {
                        return [];
                    } else {
                        return [
                            {
                                key: "name",
                                like: projectNameToken,
                            },
                        ];
                    }
                }}
                onRefresh={() => {
                    this.setState(
                        {
                            projectSelected: false,
                        },
                        () => {
                            this.getListing().fetchRecords();
                        }
                    );
                }}
                onSelectionChange={() => {
                    this.setState(
                        {
                            projectSelected: true,
                        },
                        () => {
                            if (!this.isAdmin())
                              return;
                            this.getFileSystemListing().fetchRecords();
                        }
                    );
                }}
                onFetchRecords={async () => {
                  const context = AppContext.get();
                  if (this.isAdmin()) {
                    let projects = (await Promise.resolve(this.projects().listProjects({
                        filters: this.getListing().getFilters(),
                        paginator: this.getListing().getPaginator(),
                        date_range: this.getListing().getDateRange(),
                    }))).listing ?? [];

                    projects = await this.getProjectsWithRoles(projects);
                    return { listing: projects };
                  }
                  let projects = (await Promise.resolve(this.projects().getUserProjects({
                      username: context.auth().getUsername(),
                    }))).projects ?? [];
                  projects = await this.getOwnerProjectsWithGroups(context, projects);
                  return { listing: projects};  
                }}
                columnDefinitions={PROJECT_TABLE_COLUMN_DEFINITIONS}
            />
        );
    }

    buildSplitPanelContent() {
        if (!this.isAdmin()) {
          return;
        }
        return (
            this.isSelected() && (
                <IdeaSplitPanel title={`File Systems in ${this.getSelected()?.name}`}>
                    <IdeaListView
                        ref={this.filesystemListing}
                        variant={"embedded"}
                        stickyHeader={false}
                        onFetchRecords={() => {
                            if (this.getSelected() == null) {
                                return Promise.resolve({});
                            }
                            return this.listSharedStorageFileSystem(this.getSelected()!.name!);
                        }}
                        columnDefinitions={FILESYSTEM_TABLE_COLUMN_DEFINITIONS}
                    />
                </IdeaSplitPanel>
            )
        );
    }
    render() {
        return (
            <IdeaAppLayout
                ideaPageId={this.props.ideaPageId}
                toolsOpen={this.props.toolsOpen}
                tools={this.props.tools}
                onToolsChange={this.props.onToolsChange}
                onPageChange={this.props.onPageChange}
                sideNavHeader={this.props.sideNavHeader}
                sideNavItems={this.props.sideNavItems}
                onSideNavChange={this.props.onSideNavChange}
                onFlashbarChange={this.props.onFlashbarChange}
                flashbarItems={this.props.flashbarItems}
                breadcrumbItems={[
                    {
                        text: "RES",
                        href: "#/",
                    },
                    {
                        text: "Environment Management",
                        href: "#/cluster/status",
                    },
                    {
                        text: "Projects",
                        href: "",
                    },
                ]}
                content={
                    <div>
                        {this.buildTagEditor()}
                        {this.buildListing()}
                    </div>
                }
                splitPanelOpen={this.state.splitPanelOpen}
                splitPanel={this.buildSplitPanelContent()}
                onSplitPanelToggle={(event: any) => {
                    this.setState({
                        splitPanelOpen: event.detail.open,
                    });
                }}
            />
        );
    }
}

export default withRouter(Projects);
