import React, { Component, createRef, RefObject } from "react";
import { withRouter } from "../../navigation/navigation-utils";
import IdeaAppLayout, { IdeaAppLayoutProps } from "../../components/app-layout";
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import { Alert, Box, Button, Container, ExpandableSection, FlashbarProps, Header, Link, Modal, SpaceBetween } from "@cloudscape-design/components";
import { GetRoleResponse, ProjectPermissions, Role, SocaUserInputParamMetadata, VDIPermissions } from "../../client/data-model";
import AuthzClient from "../../client/authz-client";
import { AppContext } from "../../common";
import IdeaForm from "../../components/form";
import Utils from "../../common/utils";
import { Constants } from "../../common/constants";

export interface ConfigurePermissionProfileProps extends IdeaAppLayoutProps, IdeaSideNavigationProps { }

export interface ConfigurePermissionProfileState {
  isUpdate: boolean;
  profile: Role | undefined;
  isLoadingProfile: boolean;
  confirmationModalVisible: boolean;
  affectedProjects: Map<string, number>;
  fromPage: 'list' | 'view' | undefined
}

class ConfigurePermissionProfile extends Component<ConfigurePermissionProfileProps, ConfigurePermissionProfileState> {
  configureProfileDetailsForm: RefObject<IdeaForm>;
  configureProjectPermissionsForm: RefObject<IdeaForm>;
  configureVDIPermissionsForm: RefObject<IdeaForm>;

  constructor(props: ConfigurePermissionProfileProps) {
    super(props);
    const { state } = this.props.location;
    this.configureProfileDetailsForm = createRef<IdeaForm>();
    this.configureProjectPermissionsForm = createRef<IdeaForm>();
    this.configureVDIPermissionsForm = createRef<IdeaForm>();
    this.state = {
      isUpdate: state?.isUpdate,
      profile: state?.profile,
      isLoadingProfile: true,
      affectedProjects: new Map(),
      confirmationModalVisible: false,
      fromPage: state?.fromPage,
    };

    if (state?.isUpdate) {
      this.authzClient().getRole({
        role_id: state!.profile.role_id,
      }).then((role: GetRoleResponse) => {
        this.setState({
          profile: role.role,
          isLoadingProfile: false,
        });
      });
    }
    Utils.getAffectedProjects(AppContext.get().client().projects(), this.authzClient())
    .then(response => {
      this.setState({
        affectedProjects: response.affectedProjects,
      });
    });
  }

  authzClient(): AuthzClient {
    return AppContext.get().client().authz();
  }

  setFlashbarMessage(type: FlashbarProps.Type, content: string, action?: React.ReactNode) {
    this.props.onFlashbarChange({
      items: [
        {
          type,
          content,
          action,
          dismissible: true,
        }
      ]
    })
  }

  buildProjectPermissionsFormParams(): SocaUserInputParamMetadata[] {
    let projectPerms = this.state.profile?.projects;
    if (!projectPerms) {
      projectPerms = {
        update_personnel: false,
        update_status: false,
      }
    }
    let formParams: SocaUserInputParamMetadata[] = [];

    Object.keys(projectPerms!).forEach((permission) => {
        const enabled = (projectPerms!)[permission as keyof ProjectPermissions];
        formParams.push({
          name: permission,
          title: Utils.getPermissionAsUIString(permission as keyof ProjectPermissions),
          description: Utils.getPermissionDescription(permission as keyof ProjectPermissions),
          data_type: "bool",
          default: enabled,
          param_type: "checkbox",
          validate: {
              required: true,
          },
          container_group_name: "permissions",
      });
    });
    return formParams;
  }

  buildVDIPermissionsFormParams(): SocaUserInputParamMetadata[] {
    let vdiPerms = this.state.profile?.vdis;
    if (!vdiPerms) {
      vdiPerms = {
        create_sessions: false,
        create_terminate_others_sessions: false,
      }
    }
    let formParams: SocaUserInputParamMetadata[] = [];

    Object.keys(vdiPerms!).forEach((permission) => {
      const enabled = (vdiPerms!)[permission as keyof VDIPermissions];
      formParams.push({
        name: permission,
        title: Utils.getPermissionAsUIString(permission as keyof VDIPermissions),
        description: Utils.getPermissionDescription(permission as keyof VDIPermissions),
        data_type: "bool",
        default: enabled,
        param_type: "checkbox",
        validate: {
            required: true,
        },
        container_group_name: "permissions",
      });
    });

    return formParams;
  }

  buildProfileDetailsForm() {
    return <IdeaForm
      name="create-update-permission-profile"
      ref={this.configureProfileDetailsForm}
      modal={false}
      showHeader={false}
      showActions={false}
      useContainers={true}
      containerGroups={[
        {
          title: "Permission profile definition",
          name: "profile_definition",
        },
      ]}
      params={[
        {
          name: "name",
          title: "Profile name",
          description: "Assign a name to the profile",
          help_text: "Must start with a letter. Must contain 1 to 64 alphanumeric characters.",
          data_type: "str",
          param_type: "text",
          validate: {
            required: true,
            regex: Constants.ROLE_NAME_REGEX,
            message: Constants.ROLE_NAME_ERROR_MESSAGE,
          },
          container_group_name: "profile_definition",
          default: this.state.isUpdate ? this.state.profile!.name : undefined,
        },
        {
          name: "description",
          title: "Profile description",
          description: "Optionally add more details to describe the specific profile",
          data_type: "str",
          param_type: "text",
          multiline: true,
          validate: {
            required: false,
            regex: Constants.ROLE_DESC_REGEX,
            message: Constants.ROLE_DESC_ERROR_MESSAGE,
          },
          container_group_name: "profile_definition",
          default: this.state.isUpdate ? this.state.profile!.description : undefined,
        },
      ]}
    />
  }

  buildProjectPermissionsForm() {
    return <IdeaForm
      name="create-project-permissions"
      ref={this.configureProjectPermissionsForm}
      modal={false}
      showHeader={false}
      showActions={false}
      useContainers={false}
      loading={this.state.isLoadingProfile}
      loadingText="Loading..."
      columns={3}
      params={ this.buildProjectPermissionsFormParams() }
    />
  }

  buildVDIPermissionsForm() {
    return <IdeaForm
      name="create-vdi-permissions"
      ref={this.configureVDIPermissionsForm}
      modal={false}
      showHeader={false}
      showActions={false}
      useContainers={false}
      loading={this.state.isLoadingProfile}
      loadingText="Loading..."
      columns={3}
      params={ this.buildVDIPermissionsFormParams() }
    />
  }

  showModal() {
    this.setState({
      confirmationModalVisible: true,
    });
  }

  hideModal() {
    this.setState({
      confirmationModalVisible: false,
    });
  }

  submitForm() {
    if (!this.configureProjectPermissionsForm.current!.validate() || !this.configureProfileDetailsForm!.current!.validate()) {
      return;
    }

    this.hideModal();

    const projectValues = this.configureProjectPermissionsForm.current!.getValues();
    const vdiValues = this.configureVDIPermissionsForm.current!.getValues();
    const details = this.configureProfileDetailsForm.current!.getValues();
    const timestamp = Date.now();

    if (!this.state.isUpdate) {
      this.authzClient().createRole({
        role: {
          name: details.name,
          description: details.description ?? "-",
          role_id: `${(details.name as string).trim().toLowerCase().replaceAll(/[-| ]/g, "_")}`,
          created_on: `${timestamp}`,
          updated_on: `${timestamp}`,
          projects: projectValues,
          vdis: vdiValues,
        }
      })
      .then((_) => {
        setTimeout(() => {
          this.setFlashbarMessage("success", "Successfully created permission profile.");
        }, 500);
        this.props.navigate("/cluster/permission-profiles");
      })
      .catch((e) => {
        this.setFlashbarMessage("error", "Failed to create permission profile.");
      });
    } else {
      this.authzClient().updateRole({
        role: {
          name: details.name,
          description: details.description ?? "-",
          role_id: this.state.profile!.role_id,
          created_on: this.state.profile!.created_on,
          updated_on: `${timestamp}`,
          projects: projectValues,
          vdis: vdiValues,
        },
      })
      .then((_) => {
        if (this.state.fromPage === "view")
          this.props.navigate(`/cluster/permission-profiles/${this.state.profile?.role_id}`);
        else
          this.props.navigate("/cluster/permission-profiles");
        setTimeout(() => {
          this.setFlashbarMessage(
            "success",
            `${this.state.profile?.name ?? "1"} profile updated succesfully. This update impacted ${this.state.profile ? 
                this.state.affectedProjects.get(this.state.profile.role_id) ?? 0 : 0
              } ongoing project(s).`,
              <Button
                variant="normal"
                iconName="external"
                iconAlign="right"
                onClick={() => {
                  this.props.navigate(`/cluster/permission-profiles/${this.state.profile?.role_id}`, { state: {
                    activeTabId: "affected-projects"
                  }});
                }}
              >View affected projects</Button>
          );
        }, 500)
      })
      .catch((e) => {
        this.setFlashbarMessage("error", "Failed to update permission profile");
      });
    }
  }

  render() {
    const breadCrumbItems = [
      {
        text: "RES",
        href: "#/",
      },
      {
        text: "Permission Profiles",
        href: "#/cluster/permission-profiles",
      },
    ];
    if (this.state.isUpdate) {
      breadCrumbItems.push(...[
        {
          text: this.state.profile!.name!,
          href: `#/cluster/permission-profiles/${this.state.profile!.role_id}`
        },
        {
          text: "Edit",
          href: `#/cluster/permission-profiles/${this.state.profile!.role_id}`,
        }
      ])
    } else {
      breadCrumbItems.push({
        text: "Create Profile",
        href: "#/cluster/permission-profiles",
      });
    }
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
        breadcrumbItems={breadCrumbItems}
        header={
          <Header variant="h1">
            {this.state.isUpdate ? `Edit ${this.state.profile!.name}` : "Create permission profile"}
          </Header>
        }
        content={
          <SpaceBetween size="l">
            {this.buildProfileDetailsForm()}
            <Container
              header={
                <Header variant="h2" description="Permissions granted to this permission profile.">Permissions</Header>
              }
            >
              <SpaceBetween size="l">
                <div>
                  <h3 style={{ marginTop: 0, marginBottom: 0 }}>Project management permissions</h3>
                  <SpaceBetween size="l">
                    <hr style={{color: "#b6bec9"}} />
                    {this.buildProjectPermissionsForm()}
                  </SpaceBetween>
                </div>
                <div>
                  <h3 style={{ marginTop: 0, marginBottom: 0 }}>VDI session management permissions</h3>
                  <SpaceBetween size="l">
                    <hr style={{color: "#b6bec9"}} />
                    {this.buildVDIPermissionsForm()}
                  </SpaceBetween>
                </div>
              </SpaceBetween>
              
            </Container>
            <SpaceBetween size="m" direction="vertical" alignItems="end">
              <SpaceBetween size="m" direction="horizontal">
                  <Button variant="normal" onClick={() => {
                    if (this.state.fromPage === "view")
                      this.props.navigate(`/cluster/permission-profiles/${this.state.profile?.role_id}`);
                    else
                      this.props.navigate("/cluster/permission-profiles");
                  }}>Cancel</Button>
                  <Button variant="primary" onClick={() => {
                    this.state.isUpdate ? this.showModal() : this.submitForm()
                  }}>{this.state.isUpdate ? "Save changes" : "Create profile"}</Button>
              </SpaceBetween>
            </SpaceBetween>
            <Modal
              visible={this.state.confirmationModalVisible}
              onDismiss={() => this.hideModal()}
              size="medium"
              header="Save changes"
              footer={
                <Box float="right">
                  <SpaceBetween direction="horizontal" size="xs">
                    <Button variant="link" onClick={() => this.hideModal()}>Cancel</Button>
                    <Button variant="primary" onClick={() => this.submitForm()}>Save</Button>
                  </SpaceBetween>
                </Box>
              }
            >
              <p>Update <b>{this.state.profile?.name}</b> profile?</p>
              <Alert
                statusIconAriaLabel="Info"
              >
                Proceeding with this action will impact users and groups in
                <Link variant="primary" external href="#" onFollow={(event) => {
                  event.preventDefault();
                  this.props.navigate(`/cluster/permission-profiles/${this.state.profile?.role_id}`, {
                    state: { activeTabId: "affected-projects" }
                  });
                }}>
                  {` ${this.state.profile ? 
                    this.state.affectedProjects.get(this.state.profile.role_id) ?? 0 : 0
                  }`} projects
                </Link>
              </Alert>
            </Modal>
          </SpaceBetween>
        }
      />
    );
  }
}

export default withRouter(ConfigurePermissionProfile);