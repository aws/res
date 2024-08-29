import React, { Component, RefObject } from "react";
import { withRouter } from "../../navigation/navigation-utils";
import IdeaAppLayout, { IdeaAppLayoutProps } from "../../components/app-layout";
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import { Button, FlashbarProps, Header, Link, TableProps } from "@cloudscape-design/components";
import { Role } from "../../client/data-model";
import IdeaListView from "../../components/list-view";
import AuthzClient from "../../client/authz-client";
import ProjectsClient from "../../client/projects-client";
import { AppContext } from "../../common";
import Utils from "../../common/utils";

export interface PermissionProfilesProps extends IdeaAppLayoutProps, IdeaSideNavigationProps { }

export interface PermissionProfilesState {
  profileSelected: boolean;
  selectedPermissionProfile: Role[];
  affectedProjects: Map<string, number>;
}

class PermissionProfilesDashboard extends Component<PermissionProfilesProps, PermissionProfilesState> {
  listing: RefObject<IdeaListView>;

  constructor(props: PermissionProfilesProps) {
    super(props);
    this.listing = React.createRef();
    this.state = {
      profileSelected: false,
      selectedPermissionProfile: [],
      affectedProjects: new Map<string, number>(),
    };
  }

  authzClient(): AuthzClient {
    return AppContext.get().client().authz();
  }

  projectsClient(): ProjectsClient {
    return AppContext.get().client().projects();
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

  isSelected(): boolean {
    return this.state.profileSelected;
  }

  getSelectedPermissionProfile(): Role | null {
    return this.state.selectedPermissionProfile.length === 0 ? null : this.state.selectedPermissionProfile[0];
  }

  PERMISSION_PROFILES_TABLE_COLUMN_DEFINITIONS: TableProps.ColumnDefinition<Role>[] = [
    {
      id: "name",
      header: "Profile name",
      cell: (role) => <Link href={`/#/cluster/permission-profiles/${role.role_id}`}>{role.name}</Link>,
    },
    {
      id: "description",
      header: "Description",
      cell: (role) => role.description || "-",
    },
    {
      id: "creationDate",
      header: "Creation date",
      cell: (role) => `${role.created_on ? Utils.convertToRelativeTime(Number(role.created_on)) : "-"}`,
    },
    {
      id: "latestUpdate",
      header: "Latest update",
      cell: (role) => `${role.updated_on ? Utils.convertToRelativeTime(Number(role.updated_on)) : "-"}`,
    },
    {
      id: "affectedProjects",
      header: "Affected projects",
      cell: (role) => `${this.state.affectedProjects.get(role.role_id) ?? "0"}`,
    },
  ];

  getListing(): IdeaListView {
    return this.listing.current!;
  }

  deleteProfile(): void {
    this.authzClient().deleteRole({
      role_id: this.state.selectedPermissionProfile[0].role_id,
    }).then((_) => {
      this.setFlashbarMessage("success", "1 permission profile deleted successfully. This deletion did not impact any ongoing projects.");
      this.setState(
        {
          profileSelected: false,
        },
        () => {
          this.getListing().fetchRecords();
        }
      );
    }).catch((e) => {
      this.setFlashbarMessage("error", "Failed to delete permission profile.");
    });
  }

  buildListing() {
    return (
      <IdeaListView
        ref={this.listing}
        preferencesKey={"permission-profiles"}
        showPreferences={false}
        title="Permission Profiles"
        description="Create and manage permission profiles."
        selectionType="single"
        primaryAction={{
          id: "create-profile",
          text: "Create profile",
          onClick: () => {
            this.props.navigate("/cluster/permission-profiles/configure", { state: { isUpdate: false, profile: undefined }})
          },
        }}
        secondaryActionsDisabled={!this.isSelected()}
        secondaryActions={[
          {
            id: "edit-profile",
            text: "Edit profile",
            onClick: () => {
              // Need to get role to retrieve permissions, since we don't get them on this page
              this.authzClient().getRole({
                role_id: this.getSelectedPermissionProfile()!.role_id
              }).then((response) => {
                this.props.navigate("/cluster/permission-profiles/configure", { 
                  state: {
                    isUpdate: true,
                    profile: response.role,
                    fromPage: 'list',
                  }
                });
              });
            },
          },
          {
            id: "delete-profile",
            text: "Delete profile",
            onClick: () => {
              const numAffectedProjects = this.state.affectedProjects.get(this.state.selectedPermissionProfile[0].role_id) ?? 0;
              if (numAffectedProjects === 0) {
                this.deleteProfile();
                return;
              }
              this.setFlashbarMessage(
                "error",
                "Your request could not be processed because users or groups are still associated with that profile. Check the affected projects, remove the users/groups, or change the profile assignments.",
                `Failed to delete ${this.state.selectedPermissionProfile[0].name} profile`,
                <Button
                  variant="normal"
                  iconName="external"
                  iconAlign="right"
                  onClick={() => {
                    this.props.navigate(`/cluster/permission-profiles/${this.state.selectedPermissionProfile[0].role_id}`, { state: {
                      activeTabId: "affected-projects"
                    }});
                  }}
                >View affected projects</Button>
              );
            },
          },
        ]}
        showPaginator={true}
        showFilters={false}
        onRefresh={() => {
          this.setState(
            {
              profileSelected: false,
            },
            () => {
              this.getListing().fetchRecords();
            }
          );
        }}
        selectedItems={this.state.selectedPermissionProfile}
        onSelectionChange={(event) => {
          this.setState({
            profileSelected: true,
            selectedPermissionProfile: event.detail.selectedItems
          })
        }}
        onFetchRecords={async () => {
          const response = await this.authzClient().listRoles({
            paginator: this.getListing().getPaginator(),
          });
          this.setState({
            affectedProjects: (await Utils.getAffectedProjects(this.projectsClient(), this.authzClient())).affectedProjects
          });
          return {
            listing: response.items,
            paginator: response.paginator,
          }
        }}
        columnDefinitions={this.PERMISSION_PROFILES_TABLE_COLUMN_DEFINITIONS}
      />
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
            text: "Permission Profiles",
            href: "#/cluster/permission-profiles",
          },
        ]}
        content={
          <div>
            {this.buildListing()}
          </div>
        }
      />
    );
  }
}

export default withRouter(PermissionProfilesDashboard);