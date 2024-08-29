import React, { Component, RefObject } from "react";
import { withRouter } from "../../navigation/navigation-utils";
import IdeaAppLayout, { IdeaAppLayoutProps } from "../../components/app-layout";
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import { Button, ColumnLayout, Container, ExpandableSection, FlashbarProps, FormField, Header, Link, SpaceBetween, StatusIndicator, Table, TabsProps } from "@cloudscape-design/components";
import { GetRoleResponse, Project, ProjectPermissions, Role, RoleAssignment, VDIPermissions } from "../../client/data-model";
import AuthzClient from "../../client/authz-client";
import ProjectsClient from "../../client/projects-client";
import { AppContext } from "../../common";
import { CopyToClipBoard } from "../../components/common";
import IdeaTabs from "../../components/tabs";
import Utils from "../../common/utils";
import IdeaListView from "../../components/list-view/list-view";
import IdeaTable from "../../components/table";

export interface PermissionProfilesViewProps extends IdeaAppLayoutProps, IdeaSideNavigationProps { }

export interface PermissionProfilesViewState {
  projectManagementSectionExpanded: boolean;
  givenRole: Role | undefined;
  affectedProjects: Map<string, number>;
  roleProjectSetMap: Map<string, Set<string>>;
  defaultFilteringText: string;
  projects: Project[];
  projectRoleAssignmentsMap: Map<string, RoleAssignment[]>;
  isLoadingProjects: boolean;
  activeTabId: string;
}

class PermissionProfilesView extends Component<PermissionProfilesViewProps, PermissionProfilesViewState> {
  listing: RefObject<IdeaTable>;

  constructor(props: PermissionProfilesViewProps) {
    super(props);
    this.listing = React.createRef();
    this.state = {
      projectManagementSectionExpanded: true,
      givenRole: undefined,
      affectedProjects: new Map(),
      roleProjectSetMap: new Map(),
      defaultFilteringText: "Find project by name",
      projects: [],
      projectRoleAssignmentsMap: new Map(),
      isLoadingProjects: true,
      activeTabId: this.props.location.state?.activeTabId ?? "permissionsTab",
    };

    this.authzClient().getRole({
      role_id: this.props.params.profile_id,
    }).then((role: GetRoleResponse) => {
      this.setState({
        givenRole: role.role,
      });
    });

    Utils.getAffectedProjects(this.projectsClient(), this.authzClient())
      .then(response => {
        this.setState({
          affectedProjects: response.affectedProjects,
          roleProjectSetMap: response.roleProjectSetMap,
        });
        this.fetchRecords();
      });
  }

  TOTAL_NUM_PROJECT_PERMISSIONS = 2;
  TOTAL_NUM_VDI_PERMISSIONS = 2;

  authzClient(): AuthzClient {
    return AppContext.get().client().authz();
  }

  projectsClient(): ProjectsClient {
    return AppContext.get().client().projects();
  }

  getListing(): IdeaTable {
    return this.listing.current!;
  }

  async fetchRecords() {
    let projects = (await Promise.resolve(this.projectsClient().listProjects({}))).listing ?? [];

    const affectedProjectIds = this.state.roleProjectSetMap.get(this.state.givenRole!.role_id);

    projects = projects.filter(project => affectedProjectIds?.has(project.project_id!));
    const projectRoleAssignmentsMap = new Map<string, RoleAssignment[]>();

    const authzClient = this.authzClient();
    const requests = [];
    for (const project of projects) {
      requests.push(
        authzClient.listRoleAssignments({
          resource_key: `${project.project_id!}:project`,
        })
          .then((result) => {
            const groups: string[] = [];
            const users: string[] = [];
            for (const roleAssignment of result.items) {
              if (roleAssignment.actor_type === "group") {
                groups.push(roleAssignment.actor_id);
              } else if (roleAssignment.actor_type === "user") {
                users.push(roleAssignment.actor_id);
              }
            }
            projectRoleAssignmentsMap.set(project.project_id!, result.items);
            project.ldap_groups = groups;
            project.users = users;
          })
      );
    }
    await Promise.all(requests);
    this.setState({
      projects: projects,
      isLoadingProjects: false,
      projectRoleAssignmentsMap: projectRoleAssignmentsMap,
    })
  }

  setFlashbarMessage(type: FlashbarProps.Type, content: string, header?: React.ReactNode, action?: React.ReactNode) {
    this.props.onFlashbarChange({
      items: [
        {
          type,
          header,
          content,
          action,
          dismissible: true,
        }
      ]
    })
  }

  allSectionsExpanded(): boolean {
    // to be expanded in the future when adding more permission sections
    return this.state.projectManagementSectionExpanded;
  }

  buildGeneralSettings() {
    const roleId = this.state.givenRole?.role_id || "-";
    return <Container
      header={
        <Header>General Settings</Header>
      }
    >
      <ColumnLayout columns={3} borders="vertical">
        <FormField
          label="Profile ID"
        >
          <CopyToClipBoard text={roleId} feedback={"Profile ID copied!"} /> {Utils.asString(roleId)}
        </FormField>
        <FormField
          label="Description"
        >
          {this.state.givenRole?.description || "-"}
        </FormField>
        <SpaceBetween direction="vertical" size="m">
          <FormField
            label="Creation date"
          >
            {this.state.givenRole?.created_on ? Utils.convertToRelativeTime(Number(this.state.givenRole.created_on)) : "-"}
          </FormField>
          <FormField
            label="Latest update"
          >
            {this.state.givenRole?.updated_on ? Utils.convertToRelativeTime(Number(this.state.givenRole.updated_on)) : "-"}
          </FormField>
        </SpaceBetween>
      </ColumnLayout>
    </Container>;
  }

  getNumProjectPermissions(): number {
    // to be expanded later as more permissions sections are added
    if (!this.state.givenRole) {
      return 0;
    }
    return Object.values(this.state.givenRole.projects).filter(Boolean).length;
  }

  getNumVDIPermissions(): number {
    // to be expanded later as more permissions sections are added
    if (!this.state.givenRole || !this.state.givenRole.vdis) {
      return 0;
    }
    return Object.values(this.state.givenRole.vdis!).filter(Boolean).length;
  }

  buildPermissionsTab(): TabsProps.Tab {
    const numProjectPermissions = this.getNumProjectPermissions();
    const numVDIPermissions = this.getNumVDIPermissions();
    return {
      id: "permissionsTab",
      label: "Permissions",
      content: <Container
        header={
          <Header
            // tracks total number of granted permissions
            counter={`(${numProjectPermissions + numVDIPermissions})`}
            description="Permissions granted to this permission profile."
          >Permissions</Header>
        }
      >
        <SpaceBetween size="l">
          <div>
            <h3 style={{ marginTop: 0, marginBottom: 0 }}>
              {`Project management permissions (selected ${numProjectPermissions}/${this.TOTAL_NUM_PROJECT_PERMISSIONS})`}
            </h3>
            <SpaceBetween size="m">
              <hr style={{color: "#b6bec9"}}/>
              <SpaceBetween size="l" direction="horizontal">
                <ColumnLayout columns={3} borders="vertical">
                  {Object.keys(this.state.givenRole?.projects || {}).map((permission) => {
                    const enabled = (this.state.givenRole!.projects as ProjectPermissions)[permission as keyof ProjectPermissions];
                    return <FormField
                      label={Utils.getPermissionAsUIString(permission as keyof ProjectPermissions)}
                      description={Utils.getPermissionDescription(permission as keyof ProjectPermissions)}
                    >
                      <StatusIndicator type={enabled ? "success" : "stopped"}>{enabled ? "Enabled" : "Disabled"}</StatusIndicator>
                    </FormField>;
                  })}
                </ColumnLayout>
              </SpaceBetween>
            </SpaceBetween>
          </div>
          <div>
            <h3 style={{ marginTop: 0, marginBottom: 0 }}>
              {`VDI session management permissions (selected ${numVDIPermissions}/${this.TOTAL_NUM_VDI_PERMISSIONS})`}
            </h3>
            <SpaceBetween size="m">
              <hr style={{color: "#b6bec9"}}/>
              <SpaceBetween size="l" direction="horizontal">
                <ColumnLayout columns={3} borders="vertical">
                  {Object.keys(this.state.givenRole?.vdis || {
                    create_sessions: false,
                    create_terminate_others_sessions: false
                  }).map((permission) => {
                    const enabled = this.state.givenRole?.vdis ? (this.state.givenRole.vdis as VDIPermissions)[permission as keyof VDIPermissions] : false;
                    return <FormField
                      label={Utils.getPermissionAsUIString(permission as keyof VDIPermissions)}
                      description={Utils.getPermissionDescription(permission as keyof VDIPermissions)}
                    >
                      <StatusIndicator type={enabled ? "success" : "stopped"}>{enabled ? "Enabled" : "Disabled"}</StatusIndicator>
                    </FormField>;
                  })}
                </ColumnLayout>
              </SpaceBetween>
            </SpaceBetween>
          </div>
        </SpaceBetween>
        
      </Container>
    }
  }

  buildAffectedProjectsTab(): TabsProps.Tab {
    if (!this.state.givenRole) {
      return {
        id: "affected-projects",
        label: "Affected projects",
        content: undefined,
      }
    }
    const numAffectedProjects = this.state.affectedProjects?.get(this.state.givenRole!.role_id) ?? 0;
    return {
      id: "affected-projects",
      label: "Affected projects",
      content:
        <Table
          header={
            <Header
              description="List of projects using this permission profile."
            >
              {`Affected projects (${numAffectedProjects})`}
            </Header>
          }
          items={this.state.projects}
          loading={this.state.isLoadingProjects}
          loadingText="Retrieving projects..."
          columnDefinitions={[
            {
              id: "name",
              header: "Project name",
              cell: (project) => <Link
                variant="primary"
                external
                onFollow={() => {
                  // Navigate directly to the relevant edit project page.
                  const projectRoles = this.state.projectRoleAssignmentsMap.get(project.project_id!);
                  this.props.navigate("/cluster/projects/configure", {
                    state: {
                      isUpdate: true,
                      project: project,
                      projectRoles: projectRoles,
                      projectPermission: undefined,
                      fromPage: 'view',
                    }
                  });
                }}
              >{project.name}</Link>
            },
            {
              id: "groups",
              header: "Groups",
              cell: (project) => project.ldap_groups?.length || "0"
            },
            {
              id: "users",
              header: "Users",
              cell: (project) => project.users?.length || "0"
            }
          ]}
          empty="No projects found."
        />
    };
  }

  buildProfileTagsTab() {
    return <Container></Container>;
  }

  buildTabs(): TabsProps.Tab[] {
    const permissionsTabContent = this.buildPermissionsTab();
    const affectedProjectsTabContent = this.buildAffectedProjectsTab();
    // const profileTagsTabContent = this.buildProfileTagsTab();
    return [permissionsTabContent, affectedProjectsTabContent];
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
            text: "Permission Profiles",
            href: "#/cluster/permission-profiles",
          },
          {
            text: this.state.givenRole?.name,
            href: "#/cluster/permission-profiles",
          },
        ]}
        header={
          <Header
            variant="h1"
            actions={
              <SpaceBetween size="m" direction="horizontal">
                <Button
                  variant="normal"
                  onClick={() => {
                    this.props.navigate("/cluster/permission-profiles/configure", { state: { isUpdate: true, profile: this.state.givenRole, fromPage: "view" } })
                  }}
                >
                  Edit
                </Button>
                <Button
                  variant="normal"
                  onClick={(e) => {
                    const numAffectedProjects = this.state.affectedProjects.get(this.state.givenRole!.role_id) ?? 0;
                    if (numAffectedProjects === 0) {
                      this.setFlashbarMessage("in-progress", "Deleting 1 profile");
                      this.authzClient().deleteRole({
                        role_id: this.state.givenRole?.role_id,
                      }).then((_) => {
                        this.props.navigate("/cluster/permission-profiles");
                        setTimeout(() => {
                          this.setFlashbarMessage("success", "1 permission profile deleted successfully.")
                        }, 500);
                      }).catch((e) => {
                        this.setFlashbarMessage("error", "Failed to delete permission profile.");
                      });
                      return;
                    }
                    this.setFlashbarMessage(
                      "error",
                      "Your request could not be processed because users or groups are still associated with that profile. Check the affected projects, remove the users/groups, or change the profile assignments.",
                      `Failed to delete ${this.state.givenRole?.name} profile`,
                      <Button
                        variant="normal"
                        iconName="external"
                        iconAlign="right"
                        onClick={() => {
                          this.props.navigate(`/cluster/permission-profiles/${this.state.givenRole?.role_id}`, { state: {
                            activeTabId: "affected-projects"
                          }});
                        }}
                      >View affected projects</Button>
                    );
                  }}
                >
                  Delete
                </Button>
              </SpaceBetween>

            }
          >
            {this.state.givenRole?.name || "View permission profile"}
          </Header>
        }
        content={
          <SpaceBetween size="s">
            {this.buildGeneralSettings()}
            <IdeaTabs tabs={this.buildTabs()} activeTabId={this.state.activeTabId}/>
          </SpaceBetween>
        }
      />
    );
  }
}

export default withRouter(PermissionProfilesView);