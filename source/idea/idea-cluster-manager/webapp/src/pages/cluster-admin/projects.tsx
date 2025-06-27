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
import { Project, ProjectPermissions, RoleAssignment, SocaFilter } from "../../client/data-model";
import IdeaListView from "../../components/list-view";
import { AccountsClient, ClusterSettingsClient, ProjectsClient, VirtualDesktopAdminClient } from "../../client";
import { AppContext } from "../../common";
import { Box, Button, FormField, Header, Input, Modal, ProgressBar, SpaceBetween, StatusIndicator, TagEditor } from "@cloudscape-design/components";
import Utils from "../../common/utils";
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import IdeaAppLayout, { IdeaAppLayoutProps } from "../../components/app-layout";
import { withRouter } from "../../navigation/navigation-utils";
import IdeaSplitPanel from "../../components/split-panel";
import { SharedStorageFileSystem } from "../../common/shared-storage-utils";
import { FILESYSTEM_TABLE_COLUMN_DEFINITIONS } from "./filesystem";
import FilesystemClient from "../../client/filesystem-client";
import { AuthService } from "../../service";
import { Constants } from "../../common/constants"
import IdeaConfirm from "../../components/modals";

export interface ProjectsProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {
  projectOwnerRoles?: string[]
}

export interface ProjectsState {
    projectSelected: boolean;
    defaultFilteringText?: string;
    tags: any[];
    splitPanelOpen: boolean;
    projectAssignments: {
      [key: string]: RoleAssignment[];
    };
    projectPermissions: Map<string, ProjectPermissions>;
    showDeleteProjectConfirmModal: boolean;
    deleteProjectConfirmText: string;
}

const PROJECT_TABLE_COLUMN_DEFINITIONS: TableProps.ColumnDefinition<Project>[] = [
    {
        id: "title",
        header: "Title",
        cell: (project) => project.title,
        sortingField: "title",
    },
    {
        id: "name",
        header: "Project Code",
        cell: (project) => project.name,
        sortingField: "name",
    },
    {
        id: "enabled",
        header: "Status",
        cell: (project) => (project.enabled ? <StatusIndicator type="success">Enabled</StatusIndicator> : <StatusIndicator type="stopped">Disabled</StatusIndicator>),
        sortingField: "enabled",
    },
    {
        id: "allowed_sessions_per_user",
        header: "Allowed Sessions Per User",
        cell: (project) => project.allowed_sessions_per_user,
        sortingField: "allowed_sessions_per_user",
    },
    {
        id: "budgets",
        header: "Budgets",
        minWidth: 240,
        cell: (project) => {
            if (project.enable_budgets) {
                if (project.budget) {
                    if(project.budget === Constants.BUDGET_NOT_FOUND) {
                        return <span style={{ color: "red" }}> Budget Not Found </span>;
                    }
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
        sortingComparator(a, b) {
            const usageA = a.budget ? Utils.asNumber(a.budget.actual_spend?.amount, 0) / Utils.asNumber(a.budget.budget_limit?.amount, 0) : 0;
            const usageB = b.budget ? Utils.asNumber(b.budget.actual_spend?.amount, 0) / Utils.asNumber(b.budget.budget_limit?.amount, 0) : 0;
            if (usageA !== usageB) {
                return usageA - usageB;
            }
            return 0;
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
        sortingComparator: (a, b) => {
            const ldapGroupsA = a.ldap_groups || [];
            const ldapGroupsB = b.ldap_groups || [];
            if (ldapGroupsA.length !== ldapGroupsB.length) {
                return ldapGroupsA.length - ldapGroupsB.length;
            }
            return ldapGroupsA.join(', ').localeCompare(ldapGroupsB.join(', '));
        }
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
        sortingComparator: (a, b) => {
            const usersA = a.users || [];
            const usersB = b.users || [];
            if (usersA.length !== usersB.length) {
                return usersA.length - usersB.length;
            }
            return usersA.join(',').localeCompare(usersB.join(','));
        }
    },
    {
        id: "updated_on",
        header: "Updated On",
        cell: (project) => new Date(project.updated_on!).toLocaleString(),
        sortingField: "updated_on",
    },
];

class Projects extends Component<ProjectsProps, ProjectsState> {
    listing: RefObject<IdeaListView>;
    filesystemListing: RefObject<IdeaListView>;
    deleteProjectConfirmModal: RefObject<IdeaConfirm>;

    constructor(props: ProjectsProps) {
        super(props);
        this.listing = React.createRef();
        this.filesystemListing = React.createRef();
        this.deleteProjectConfirmModal = React.createRef();
        const { state } = this.props.location
        this.state = {
            projectSelected: false,
            defaultFilteringText: state ? state?.defaultFilteringText : "",
            tags: [],
            splitPanelOpen: false,
            projectAssignments: {},
            projectPermissions: new Map(),
            showDeleteProjectConfirmModal: false,
            deleteProjectConfirmText: '',
        };
    }

    projects(): ProjectsClient {
        return AppContext.get().client().projects();
    }

    getVirtualDesktopAdminClient(): VirtualDesktopAdminClient {
        return AppContext.get().client().virtualDesktopAdmin();
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

    getAuthService(): AuthService {
        return AppContext.get().auth();
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

    async getProjectsWithPermissions(context: AppContext, allProjects: Project[]): Promise<Project[]> {
        const rolePermissions = await context.client().authz().listRoles({
          include_permissions: true,
        });
        const user = await this.getAuthService().getUser();
        const projectRoleAssignments: Promise<void>[] = [];
        const projects: Map<string, Project> = new Map();
        const permissions: Map<string, ProjectPermissions> = new Map();

        // For every project in `allProjects`, we populate the users/groups columns, and the
        // permissions that the current user has with which they can interact with the project
        for (const project of allProjects) {
          const resource_key = `${project.project_id!}:project`;
          projectRoleAssignments.push(Promise.resolve(
            context.client().authz().listRoleAssignments({
              resource_key,
            })
            .then(async (result) => {
              for (const roleAssignment of result.items) {
                let update = {
                  ldap_groups: [] as string[],
                  users: [] as string[],
                };
                // If the project associated with the role assignment is already in the projects Map, it retrieves the existing ldap_groups and users arrays for that project.
                if (projects.has(roleAssignment.resource_id!)) {
                  update = {
                    ldap_groups: projects.get(roleAssignment.resource_id!)?.ldap_groups ?? [],
                    users: projects.get(roleAssignment.resource_id!)?.users ?? [],
                  }
                }

                let partOfProject: boolean = false;

                if (roleAssignment.actor_type === "group") {
                  update.ldap_groups.push(roleAssignment.actor_id);
                  if (user.additional_groups?.includes(roleAssignment.actor_id))
                    partOfProject = true;
                } else if (roleAssignment.actor_type === "user") {
                  update.users.push(roleAssignment.actor_id);
                  if (roleAssignment.actor_id === user.username!)
                    partOfProject = true;
                }

                // if we already have a mapping, use that. Otherwise, use the base project
                projects.set(roleAssignment.resource_id!, {...project, ...update});

                // If the user is part of the project or is in a group that is part of the project
                // we update the permissions they have to interact with that project based on the
                // union of all groups/user permissions.

                if (partOfProject) {
                  let permission = permissions.get(roleAssignment.resource_id!) ?? {
                    update_personnel: false,
                    update_status: false,
                  }

                  const rolePermission = rolePermissions.items.find(perm => perm.role_id === roleAssignment.role_id);

                  if (rolePermission) {
                    permission = {
                      update_personnel: permission.update_personnel || rolePermission.projects.update_personnel,
                      update_status: permission.update_status || rolePermission.projects.update_status,
                    }
                    permissions.set(roleAssignment.resource_id!, permission);
                  }
                }
              }
            })
          ));
        }
        await Promise.all(projectRoleAssignments);
        this.setState({
          projectPermissions: permissions,
        });
        return Array.from(projects.values());
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

    canEditProjectDetails(): boolean {
      if (this.isAdmin())
        return true;
      const selectedProject = this.getSelected();
      if (!selectedProject)
        return true;
      if (!this.state.projectPermissions.has(selectedProject!.project_id!)) {
        return false;
      }
      const perms = this.state.projectPermissions.get(selectedProject!.project_id!)!;
      return perms.update_personnel;
    }

    canUpdateProjectStatus(): boolean {
      if (this.isAdmin())
        return true;
      const selectedProject = this.getSelected();
      if (!selectedProject)
        return true;
      if (!this.state.projectPermissions.has(selectedProject!.project_id!)) {
        return false;
      }
      return this.state.projectPermissions.get(selectedProject!.project_id!)!.update_status;
    }

    canEditProjectTags(): boolean {
      return this.isAdmin();
    }

    convertProjectObjectToSocaFilter(): SocaFilter {
        const project = this.getSelected();
        // For VDI sessions: use 'project' as key with eq operator
        const eq = project != null ? {
            'name': project.name,
            'project_id': project.project_id,
            'title': project.title
        } : {};
        return { key: 'project', eq };
    }

    buildDeleteProjectConfirmModal() {
        const selectedProject = this.getSelected();
        return (
                <IdeaConfirm
                    ref={this.deleteProjectConfirmModal}
                    title={`Delete Project: ${selectedProject?.name}`}
                    confirmButtonDisabled={this.state.deleteProjectConfirmText !== selectedProject?.name}
                    onConfirm={async () => {
                        try {
                            this.setState({
                                deleteProjectConfirmText: '',
                            });
                            await this.projects().deleteProject({
                                project_id: selectedProject?.project_id,
                            });

                            await this.getListing().fetchRecords();
                            this.props.onFlashbarChange({
                                items: [{
                                    type: "success",
                                    content: `Project with ID: ${selectedProject?.project_id} has been deleted successfully`,
                                    dismissible: true,
                                }],
                            });
                        } catch (error: any) {
                            this.props.onFlashbarChange({
                                items: [{
                                    type: "error",
                                    content: error.message,
                                    dismissible: true,
                                }],
                            });
                        }
                    }}
                    onCancel={() => {
                        this.setState({
                            showDeleteProjectConfirmModal: false,
                            deleteProjectConfirmText: '',
                        })
                    }}
                >
                    <div>
                        <p>Are you sure you want to delete this project?</p>
                        <p>All associated sessions will be terminated. This action cannot be undone.</p>
                    </div>
                    <FormField
                        label="To confirm deletion, enter the name of the project in the text input field."
                    >
                        <Input
                            value={this.state.deleteProjectConfirmText}
                            onChange={({ detail }) => 
                                this.setState({ deleteProjectConfirmText: detail.value })
                            }
                            placeholder={selectedProject?.name}
                        />
                    </FormField>
                </IdeaConfirm>
        );
    }

    showDeleteProjectConfirmModal() {
        this.setState(
            {
                showDeleteProjectConfirmModal: true,
            },
            () => {
                this.getDeleteProjectConfirmModal().show();
            }
        );
    }

    getDeleteProjectConfirmModal() {
        return this.deleteProjectConfirmModal.current!;
    }

    buildListing() {
        return (
            <IdeaListView
                ref={this.listing}
                preferencesKey={"projects"}
                showPreferences={false}
                title="Projects"
                description={`Environment Project Management.${this.isAdmin() ? "" : " These are the projects of which you are a part of."}`}
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
                              this.props.navigate("/cluster/projects/configure", { state: {
                                isUpdate: true,
                                project: selectedProject, projectRoles: result.items,
                                projectPermission: this.isAdmin() ? undefined : this.state.projectPermissions.get(selectedProject!.project_id!)
                              }})
                            });
                        },
                        // based on if the user is admin or has update_personnel permission for selected project
                        disabled: !this.canEditProjectDetails(),
                    },
                    {
                        id: "toggle-enable-project",
                        text: this.isSelectedProjectEnabled() ? "Disable Project" : "Enable Project",
                        onClick: async () => {
                            const projectId = this.getSelected()?.project_id;
                            const isProjectEnabled = this.isSelectedProjectEnabled();
                            const operationType = isProjectEnabled ? "disable" : "enable";

                            try {
                                let enableOrDisable;
                                let successMessage;
                                if (isProjectEnabled) {
                                    enableOrDisable = (request: any) => this.projects().disableProject(request);
                                    successMessage = `Successfully ${operationType}d project with ID: ${projectId}, and all associated sessions will be stopped`
                                } else {
                                    enableOrDisable = (request: any) => this.projects().enableProject(request);
                                    successMessage = `Successfully ${operationType}d project with ID: ${projectId}`
                                }

                                await enableOrDisable({ project_id: projectId });
                                await this.getListing().fetchRecords();

                                this.props.onFlashbarChange({
                                    items: [{
                                        type: "success",
                                        content: successMessage,
                                        dismissible: true,
                                    }],
                                });
                            } catch (error: any) {
                                this.props.onFlashbarChange({
                                    items: [{
                                        type: "error",
                                        content: `Failed to ${operationType} project with ID: ${projectId} because ${error.message}`,
                                        dismissible: true,
                                    }],
                                });
                            }
                        },
                        disabled: !this.canUpdateProjectStatus(),
                    },
                    {
                        id: "toggle-delete-project",
                        text: "Delete Project",
                        onClick: () => {
                            this.showDeleteProjectConfirmModal();
                        }
                    }
                ]}
                showPaginator={true}
                showFilters={true}
                filters={[
                    {
                        key: "name",
                        like: this.state.defaultFilteringText,
                    },
                ]}
                defaultFilteringText={this.state.defaultFilteringText}
                onFilter={(filters) => {
                    const projectNameToken = Utils.asString(filters[0].value).trim().toLowerCase();
                    this.setState(
                        {
                            projectSelected: false,
                            splitPanelOpen: false,
                        }
                    );
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
                            defaultFilteringText: "",
                        },
                        () => {
                            this.getListing().resetState();
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
                      exclude_disabled: false
                    }))).projects ?? [];
                  projects = await this.getProjectsWithPermissions(context, projects);
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
                        {this.buildListing()}
                        {this.state.showDeleteProjectConfirmModal && this.buildDeleteProjectConfirmModal()}
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
