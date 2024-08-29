import React, {Component, RefObject} from "react";
import IdeaAppLayout, {IdeaAppLayoutProps} from "../../components/app-layout";
import {IdeaSideNavigationProps} from "../../components/side-navigation";
import { AttributeEditor, Box, Button, Container, Header, Icon, Popover, Select, SpaceBetween } from "@cloudscape-design/components";
import IdeaForm from "../../components/form";
import {withRouter} from "../../navigation/navigation-utils";
import Utils from "../../common/utils";
import {AppContext} from "../../common";
import {BatchPutRoleAssignmentResponse, DeleteRoleAssignmentRequest, Project, ProjectPermissions, PutRoleAssignmentRequest, Role, RoleAssignment, ScriptEvents, Scripts, SocaUserInputChoice, SocaUserInputParamMetadata} from "../../client/data-model";
import {AccountsClient, ClusterSettingsClient} from "../../client";
import {Constants} from "../../common/constants";
import dot from "dot-object";
import AuthzClient from "../../client/authz-client";
import { OptionDefinition } from "@cloudscape-design/components/internal/components/option/interfaces";

export interface ConfigureProjectState {
    isUpdate: boolean
    project?: Project
    projectRoles?: RoleAssignment[];
    attachedUsers: { key: string, value: OptionDefinition, error?: string }[];
    availableUsers: OptionDefinition[];
    attachedGroups: { key: string, value: OptionDefinition, error?: string }[];
    availableGroups: OptionDefinition[];
    permissionProfiles: Map<string, Role>;
    permissionForProject?: ProjectPermissions;
}

export interface ConfigureProjectProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {
}

class ConfigureProject extends Component<ConfigureProjectProps, ConfigureProjectState> {
    configureProjectForm: RefObject<IdeaForm>;

    constructor(props: ConfigureProjectProps) {
        super(props);
        this.configureProjectForm = React.createRef()
        const { state } = this.props.location
        this.state = {
            isUpdate: state ? state.isUpdate ?? false : false,
            project: state ? state.project : null,
            projectRoles: state ? state.projectRoles : [],
            attachedUsers: [],
            availableUsers: [],
            attachedGroups: [],
            availableGroups: [],
            permissionProfiles: new Map(),
            permissionForProject: state ? state.projectPermission : undefined,
        };
        this.getUsers();
        this.getGroups();
        this.getPermissionProfiles();
    }

    getDefaultUsers(profileMap: Map<string, Role>): { key: string; value: OptionDefinition; error?: string }[] {
      const defaults = [];
      for (const existingMapping of this.state.projectRoles ?? []) {
        if (existingMapping.actor_type === "user")
          defaults.push({
            key: existingMapping.actor_id,
            value: {
              value: existingMapping.role_id!,
              label: (profileMap.get(existingMapping.role_id!)?.name || existingMapping.role_id!),
            },
          });
      }
      return defaults;
    }

    getDefaultGroups(profileMap: Map<string, Role>): { key: string; value: OptionDefinition; error?: string }[] {
      const defaults = [];
      for (const existingMapping of this.state.projectRoles ?? []) {
        if (existingMapping.actor_type === "group")
          defaults.push({
            key: existingMapping.actor_id,
            value: {
              value: existingMapping.role_id!,
              label: (profileMap.get(existingMapping.role_id!)?.name || existingMapping.role_id!),
            },
          });
      }
      return defaults;
    }

    isAdmin(): boolean {
      return AppContext.get().auth().isAdmin();
    }

    authz(): AuthzClient {
      return AppContext.get().client().authz();
    }

    projects() {
        return AppContext.get().client().projects()
    }

    accounts(): AccountsClient {
        return AppContext.get().client().accounts();
    }

    clusterSettings(): ClusterSettingsClient {
        return AppContext.get().client().clusterSettings();
    }
    getConfigureProjectForm(): IdeaForm {
        return this.configureProjectForm.current!;
    }

    async updateRoleAssignments() {
      const authzClient = AppContext.get().client().authz();

      const listResponse = this.state.projectRoles!;

      const toDelete: DeleteRoleAssignmentRequest[] = [];
      const toUpdate: PutRoleAssignmentRequest[] = [];

      const newUsers = this.state.attachedUsers;
      const newGroups = this.state.attachedGroups;
      const projectId = this.state.project?.project_id!;

      for (const existingMapping of listResponse) {
        // loop through groups and see if actor exists; if not, delete it
        let exists = false;
        for (const actor of existingMapping.actor_type === "group" ? newGroups : newUsers) {
          if (actor.key === existingMapping.actor_id) {
            exists = true;
            if (actor.value.value !== existingMapping.role_id) {
              // we have a different role, need to update
              toUpdate.push({
                actor_id: actor.key,
                actor_type: existingMapping.actor_type,
                resource_type: "project",
                resource_id: projectId,
                role_id: actor.value.value!,
                request_id: Utils.getUUID(),    
              });
            }
            break;
          }
        }
        // the existingMapping is not present in new mappings, need to delete
        if (!exists) {
          toDelete.push({
            actor_id: existingMapping.actor_id,
            actor_type: existingMapping.actor_type,
            request_id: Utils.getUUID(),
            resource_id: projectId!,
            resource_type: "project",
          });
        }
      }

      for (const user of newUsers) {
        // if the new user is not present in the existing mappings
        // we have a new user being added to the project. Add an update for these
        if (listResponse.findIndex(x => x.actor_id === user.key) === -1) {
          toUpdate.push({
            actor_id: user.key,
            actor_type: "user",
            resource_type: "project",
            resource_id: projectId,
            role_id: user.value.value!,
            request_id: Utils.getUUID(),    
          });
        }
      }

      for (const group of newGroups) {
        // if the new group is not present in the existing mappings
        // we have a new group being added to the project. Add an update for these
        if (listResponse.findIndex(x => x.actor_id === group.key) === -1) {
          toUpdate.push({
            actor_id: group.key,
            actor_type: "group",
            resource_type: "project",
            resource_id: projectId,
            role_id: group.value.value!,
            request_id: Utils.getUUID(),    
          });
        }
      }

      if (toDelete.length > 0) {
        await Promise.resolve(authzClient.batchDeleteRoleAssignment({
          items: toDelete,
        }));
      }

      if (toUpdate.length > 0) {
        await Promise.resolve(authzClient.batchPutRoleAssignment({
          items: toUpdate,
        }));
      }
    }

    createRoleAssignments(projectId: string): Promise<BatchPutRoleAssignmentResponse> {
      const authzClient = AppContext.get().client().authz();

      const groupRoleAssignments = this.state.attachedGroups;
      const userRoleAssignments = this.state.attachedUsers;

      const items: PutRoleAssignmentRequest[] = [];
      for (const groupRoleMapping of groupRoleAssignments) {
        items.push({
          actor_id: groupRoleMapping.key,
          actor_type: "group",
          resource_type: "project",
          resource_id: projectId,
          role_id: groupRoleMapping.value.value!,
          request_id: Utils.getUUID(),    
        });
      }
      for (const userRoleMapping of userRoleAssignments ?? []) {
        items.push({
          actor_id: userRoleMapping.key,
          actor_type: "user",
          resource_type: "project",
          resource_id: projectId,
          role_id: userRoleMapping.value.value!,
          request_id: Utils.getUUID(),    
        });
      }


      return authzClient.batchPutRoleAssignment({
        items
      });
    }

    getUsers() {
      this.accounts().listUsers().then((result) => {
          const listing = result.listing!;
          if (listing.length === 0) {
              return;
          }
          const choices: OptionDefinition[] = [];
          listing.forEach((value) => {
              if (value.username !== "clusteradmin") {
                  choices.push({
                      label: `${value.username} (${value.uid})`,
                      value: value.username!,
                  });
              }
          });
          this.setState({ availableUsers: choices });
      });
    }

    getGroups() {
      this.accounts().listGroups({
          filters: [
              {
                  key: "group_type",
                  eq: "project",
              },
          ],
      })
      .then((result) => {
          const listing = result.listing!;
          if (listing.length === 0) {
              return {
                  listing: [],
              };
          }
          const choices: OptionDefinition[] = [];
          listing.forEach((value) => {
              choices.push({
                  label: `${value.name} (${value.gid})`,
                  value: value.name,
              });
          });
          this.setState({ availableGroups: choices });
      });
    }

    getPermissionProfiles() {
      this.authz().listRoles({
        include_permissions: true,
      })
      .then((response) => {
        const profileMap = new Map();
        response.items.forEach(profile => {
          profileMap.set(profile.role_id, profile);
        })
        this.setState({
          permissionProfiles: profileMap,
          attachedGroups: this.getDefaultGroups(profileMap),
          attachedUsers: this.getDefaultUsers(profileMap),
        });
      });
    }

    getPermissionProfileOptions(): OptionDefinition[] {
      const permissionProfiles = Array.from(this.state.permissionProfiles.values());
      return permissionProfiles.map(profile => {
        return {
          value: profile.role_id,
          label: profile.name,
        }
      });
    }

    buildUserParam(): React.ReactElement {
        return <SpaceBetween size="m">
          <AttributeEditor
            key="UserAttributeEditor"
            onAddButtonClick={() => {
              this.setState({
                attachedUsers: [...this.state.attachedUsers, {
                  key: "",
                  value: { label: "Project Member", value: "project_member" },
                  error: "Please choose a user."
                }]
              });
            }}
            onRemoveButtonClick={(changeEvent) => {
              const tmpItems = [...this.state.attachedUsers];
              tmpItems.splice(changeEvent.detail.itemIndex, 1);
              this.setState({attachedUsers: tmpItems});
            }}
            items={this.state.attachedUsers}
            addButtonText={"Add user"}
            disableAddButton={
              (this.state.attachedUsers.length === this.state.availableUsers.length) || 
              (this.state.permissionForProject ? !this.state.permissionForProject.update_personnel : !this.isAdmin())
            }
            removeButtonText="Remove"
            empty="No users attached. Click 'Add user' below to get started."
            isItemRemovable={(_) => {
              return (this.state.permissionForProject ? this.state.permissionForProject.update_personnel : this.isAdmin())
            }}
            definition={[
              {
                label: "Users",
                info: <Popover content="Select applicable users for the Project.">Info</Popover>,
                control: (item: { key: string, value: OptionDefinition, error?: string }, itemIndex: number) => (
                  <Select
                    key={item.key}
                    options={this.state.availableUsers}
                    selectedOption={{value: item.key}}
                    disabled={this.state.permissionForProject ? !this.state.permissionForProject.update_personnel : !this.isAdmin()}
                    onChange={(e) => {
                      if (this.state.attachedUsers.some(x => x.key === e.detail.selectedOption.value!)) {
                        // we have already chosen this user, we can't assign a user
                        // multiple times so we just leave
                        return;
                      }
                      const tmp = [...this.state.attachedUsers];
                      tmp[itemIndex].key = e.detail.selectedOption.value!;
                      tmp[itemIndex].error = undefined;
                      this.setState({ attachedUsers: tmp });
                    }}
                  ></Select>
                ),
                errorText: (item: {key: string, value: OptionDefinition, error?: string}) => { return item.error },
              },
              {
                label: "Permission profile",
                info: <Popover content="Choose a permission profile for the user.">Info</Popover>,
                control: (item: { key: string, value: OptionDefinition }, itemIndex: number) => (
                  <Select
                    key={item.key}
                    selectedOption={item.value}
                    options={this.getPermissionProfileOptions()}
                    disabled={this.state.permissionForProject ? !this.state.permissionForProject.update_personnel : !this.isAdmin()}
                    placeholder="Choose role"
                    errorText=""
                    onChange={(e) => {
                      const tmp = [...this.state.attachedUsers];
                      tmp[itemIndex].value = e.detail.selectedOption;
                      this.setState({ attachedUsers: tmp });
                    }}
                  ></Select>
                ),
                constraintText: (item: { key: string, value: OptionDefinition, error?: string }) => {
                  if (this.state.permissionProfiles.has(item.value.value!)) {
                    if (this.state.permissionProfiles.get(item.value.value!)?.projects.update_personnel) {
                      return <Box color="text-status-error" variant="p">
                        <Icon name="status-warning" /> Users/groups assigned
                        to this permission profile can grant themselves or
                        others higher privileges for this project by
                        re-assigning personnel to a different permission
                        profile
                      </Box>
                    }
                  }
                  return null;
                },
              }
            ]}
          />
        </SpaceBetween>
    }

    buildGroupParam(): React.ReactElement {
      return <SpaceBetween size="m">
              <AttributeEditor
                key="GroupAttributeEditor"
                onAddButtonClick={() => {
                  this.setState({ attachedGroups: [...this.state.attachedGroups, {
                    key: "",
                    value: { label: "Project Member", value: "project_member" },
                    error: "Please choose a group"
                  }]});
                }}
                onRemoveButtonClick={(changeEvent) => {
                  const tmpItems = [...this.state.attachedGroups];
                  tmpItems.splice(changeEvent.detail.itemIndex, 1);
                  this.setState({ attachedGroups: tmpItems });
                }}
                isItemRemovable={(_) => {
                  return (this.state.permissionForProject ? this.state.permissionForProject.update_personnel : this.isAdmin())
                }}
                items={this.state.attachedGroups}
                addButtonText={"Add group"}
                removeButtonText="Remove"
                disableAddButton={
                  (this.state.attachedGroups.length === this.state.availableGroups.length) || 
                  (this.state.permissionForProject ? !this.state.permissionForProject.update_personnel : !this.isAdmin())
                }
                empty="No groups attached. Click 'Add group' below to get started."
                definition={[
                  {
                    label: "Groups",
                    info: <Popover content="Select applicable ldap groups for the Project.">Info</Popover>,
                    control: (item: { key: string, value: OptionDefinition, error?: string }, itemIndex: number) => (
                      <Select
                        key={item.key}
                        options={this.state.availableGroups}
                        selectedOption={{ value: item.key }}
                        disabled={this.state.permissionForProject ? !this.state.permissionForProject.update_personnel : !this.isAdmin()}
                        onChange={(e) => {
                          if (this.state.attachedGroups.some(x => x.key === e.detail.selectedOption.value!)) {
                            // we have already chosen this group, we can't assign a group
                            // multiple times so we just leave
                            return;
                          }
                          const tmp = [...this.state.attachedGroups];
                          tmp[itemIndex].key = e.detail.selectedOption.value!;
                          tmp[itemIndex].error = undefined;
                          this.setState({ attachedGroups: tmp });
                        }}
                      ></Select>
                    ),
                    errorText: (item: {key: string, value: OptionDefinition, error?: string}) => { return item.error }
                  },
                  {
                    label: "Permission profile",
                    info: <Popover content="Choose a permission profile for the group.">Info</Popover>,
                    control: (item: { key: string, value: OptionDefinition }, itemIndex: number) => (
                      <Select
                        key={item.key}
                        selectedOption={item.value}
                        options={this.getPermissionProfileOptions()}
                        placeholder="Choose role"
                        disabled={this.state.permissionForProject ? !this.state.permissionForProject.update_personnel : !this.isAdmin()}
                        onChange={(e) => {
                          const tmp = [...this.state.attachedGroups];
                          tmp[itemIndex].value = e.detail.selectedOption;
                          this.setState({ attachedGroups: tmp });
                        }}
                      ></Select>
                    ),
                    constraintText: (item: { key: string, value: OptionDefinition, error?: string }) => {
                      if (this.state.permissionProfiles.has(item.value.value!)) {
                        if (this.state.permissionProfiles.get(item.value.value!)?.projects.update_personnel) {
                          return <Box color="text-status-error" variant="p">
                            <Icon name="status-warning" /> Users/groups assigned
                            to this permission profile can grant themselves or
                            others higher privileges for this project by
                            re-assigning personnel to a different permission
                            profile
                          </Box>
                        }
                      }
                      return null;
                    },
                  }
                ]}
              />
        </SpaceBetween>
    }

    buildAddFileSystemParam(isUpdate: boolean): SocaUserInputParamMetadata[] {
        const params: SocaUserInputParamMetadata[] = [];
        if (isUpdate) {
            return params;
        }
        params.push({
            name: "add_filesystems",
            title: "Storage resources",
            description: "Add file systems and/or S3 buckets to the project.",
            param_type: "select",
            multiple: true,
            data_type: "str",
            dynamic_choices: true,
            default: ["home"],
            container_group_name: "resource_configurations",
            readonly: !this.isAdmin(),
        });
        return params;
    }

    buildResourceConfigurationAdvancedOptions(): SocaUserInputParamMetadata[] {
        let formParams: SocaUserInputParamMetadata[] = [];
        formParams.push({
            name: "advanced_options",
            title: "Advanced Options",
            data_type: "bool",
            param_type: "expandable",
            validate: {
                required: true,
            },
            default: false,
            readonly: !this.isAdmin(),
        })

        formParams.push({
            name: "policy_arns",
            title: "Add Policies",
            description: "Select applicable policies for the Project",
            param_type: "select",
            multiple: true,
            data_type: "str",
            dynamic_choices: true,
            when: {
                param: "advanced_options",
                eq: true,
            },
            readonly: !this.isAdmin(),
        });

        formParams.push({
            name: "security_groups",
            title: "Add Security Groups",
            description: "Select applicable security groups for the Project",
            param_type: "select",
            multiple: true,
            data_type: "str",
            dynamic_choices: true,
            when: {
                param: "advanced_options",
                eq: true,
            },
            readonly: !this.isAdmin(),
        });


        formParams = [...formParams, ...this.buildLinuxScriptInput(), ...this.buildWindowsScriptInput()];
        for (const param of formParams) {
            param.container_group_name = "resource_configurations"
        }

        return formParams
    }

    buildWindowsScriptInput() {
        let formParams: SocaUserInputParamMetadata[] = [];

        formParams.push({
            name: `windows`,
            title: "Windows",
            data_type: "bool",
            param_type: "expandable",
            validate: {
                required: true,
            },
            default: false,
            when: {
                param: "advanced_options",
                eq: true,
            },
            readonly: !this.isAdmin(),
        })
        return [...formParams, ...this.buildScriptsInputParams("windows")]
    }

    buildLinuxScriptInput() {
        let formParams: SocaUserInputParamMetadata[] = [];

        formParams.push({
            name: `linux`,
            title: "Linux",
            data_type: "bool",
            param_type: "expandable",
            validate: {
                required: true,
            },
            default: false,
            when: {
                param: "advanced_options",
                eq: true,
            },
            readonly: !this.isAdmin(),
        })
        return [...formParams, ...this.buildScriptsInputParams("linux")]
    }

    buildScriptsInputParams(osType: string): SocaUserInputParamMetadata[] {
        let formParams: SocaUserInputParamMetadata[] = [];
        let script_event_title_map: { [k:string]: string} = {
            "on_vdi_start":"Run Script When VDI Starts",
            "on_vdi_configured": "Run Script when VDI is Configured"
        }
        let script_event_description_map: { [k:string]: string} = {
            "on_vdi_start": "Scripts that execute at the start of a VDI",
            "on_vdi_configured": "Scripts that execute after RES configurations are completed"
        }

        for (let script_event of ["on_vdi_start", "on_vdi_configured"]) {
            formParams.push({
                name: `${osType}_${script_event}_toggle`,
                title: script_event_title_map[script_event],
                description: script_event_description_map[script_event],
                data_type: "bool",
                param_type: "confirm",
                validate: {
                    required: true,
                },
                when: {
                    param: `${osType}`,
                    eq: true,
                },
                default: false,
                readonly: !this.isAdmin(),
          })
            const script: SocaUserInputParamMetadata = {
                title: "Script",
                param_type: "text",
                data_type: "str",
                readonly: !this.isAdmin(),
                markdown: "configure-project",
          };
            const args: SocaUserInputParamMetadata = {
                title: "Arguments",
                description: "optional",
                param_type: "text",
                data_type: "str",
                readonly: !this.isAdmin(),
                markdown: "configure-project",
          };
            formParams.push({
                name: `${osType}_${script_event}_scripts`,
                param_type: "attribute_editor",
                data_type: "attributes",
                attributes_editor_type: "Scripts",
                container_items: [script, args],
                multiple: true,
                when: {
                    param: `${osType}_${script_event}_toggle`,
                    eq: true,
                },
                readonly: !this.isAdmin(),
          })
        }
        return formParams
    }

    buildCreateProjectForm() {
        let {isUpdate, project} = this.state
        let values = undefined
        if (isUpdate) {
            let scripts = project?.scripts ? this.reverseScripts(project.scripts) : {};
            values = {
                ...project,
                ...scripts,
                "budget.budget_name": project?.budget?.budget_name,
                "advanced_options": !!(project?.scripts || project?.policy_arns || project?.security_groups)
            }
        }
        return (
            <IdeaForm
                name="create-update-project"
                ref={this.configureProjectForm}
                modal={false}
                showHeader={false}
                showActions={false}
                useContainers={true}
                values={values}
                onFetchOptions={(request) => {
                    if (request.param === "add_filesystems") {
                            let promises: Promise<any>[] = [];
                            promises.push(this.clusterSettings().getModuleSettings({ module_id: Constants.MODULE_SHARED_STORAGE }));
                            return Promise.all(promises).then((result) => {
                                const choices: SocaUserInputChoice[] = [];
                                const sharedFileSystem = result[0].settings;
                                Object.keys(sharedFileSystem).forEach((name) => {
                                    const storage = dot.pick(name, sharedFileSystem);
                                    const title = dot.pick("title", storage);
                                    const provider = dot.pick("provider", storage);
                                    if (Utils.isEmpty(provider)) {
                                        return true;
                                    }
                                    const isInternal = name === "internal";
                                    if (!isInternal) {
                                        let choice: SocaUserInputChoice = {
                                            title: `${title} [${provider}]`,
                                            description: `${name}`,
                                            value: `${name}`,
                                        };
                                        if (name === "home") {
                                            choice.disabled = true;
                                        }
                                        choices.push(choice);
                                    }
                                });
                                return { listing: choices };
                            });
                        }
                     else if (request.param === "security_groups") {
                        if (!this.isAdmin()) {
                          return Promise.resolve({ listing: [] });
                        }
                        return this.projects().listSecurityGroups().then((result) => {
                            const security_groups = result.security_groups
                            if (!security_groups || security_groups?.length === 0) {
                                return {
                                    listing: [],
                                }
                            } else {
                                const choices: SocaUserInputChoice[] = []
                                security_groups.forEach((security_group) => {
                                    choices.push({
                                        title: security_group.group_name,
                                        value: security_group.group_id
                                    })
                                })
                                return {
                                    listing: choices
                                }
                            }
                        })
                    }
                     else if (request.param === "policy_arns") {
                        if (!this.isAdmin()) {
                          return Promise.resolve({ listing: [] });
                        }
                         return this.projects().listPolicies().then((result) => {
                             const policies = result.policies
                             if(!policies || policies?.length === 0) {
                                 return {
                                     listing: []
                                 }
                             }
                             else{
                                 const choices: SocaUserInputChoice[] = []
                                 policies.forEach((policy) => {
                                     choices.push({
                                         title: policy.policy_name,
                                         value: policy.policy_arn
                                     })
                                 })
                                 return {
                                     listing: choices
                                 }
                             }
                         })
                    }
                     else {
                            return Promise.resolve({
                                listing: [],
                            });
                        }
                }}
                containerGroups={[
                    {
                        title: "Project Definition",
                        name: "project_definition",
                    },
                    {
                        title: "Resource Configurations",
                        name: "resource_configurations",
                    },
                ]}
                params={[
                    {
                        name: "title",
                        title: "Title",
                        description: "Enter a user friendly project title",
                        data_type: "str",
                        param_type: "text",
                        validate: {
                            required: true,
                        },
                        container_group_name: "project_definition",
                        readonly: !this.isAdmin(),
                    },
                    {
                        name: "name",
                        title: "Project ID",
                        description: "Enter a project-id",
                        help_text: "Project ID can only use lowercase alphabets, numbers, hyphens (-), underscores (_), or periods (.). Must be between 3 and 40 characters long.",
                        data_type: "str",
                        param_type: "text",
                        readonly: isUpdate,
                        validate: {
                            required: true,
                            regex: "^[a-z0-9-_.]{3,40}$",
                            message: "Only use lowercase alphabets, numbers, hyphens (-), underscores (_), or periods (.). Must be between 3 and 40 characters long.",
                        },
                        container_group_name: "project_definition"
                    },
                    {
                        name: "description",
                        title: "Description",
                        description: "Enter the project description",
                        data_type: "str",
                        param_type: "text",
                        multiline: true,
                        container_group_name: "project_definition",
                        readonly: !this.isAdmin(),
                    },
                    ...this.buildAddFileSystemParam(isUpdate),
                    {
                        name: "enable_budgets",
                        title: "Do you want to enable budgets for this project?",
                        data_type: "bool",
                        param_type: "confirm",
                        default: false,
                        validate: {
                            required: true,
                        },
                        container_group_name: "project_definition",
                        readonly: !this.isAdmin(),
                    },
                    {
                        name: "budget.budget_name",
                        title: "Enter the AWS Budgets name for the project",
                        description: "Select budget name that you have created in AWS budget",
                        data_type: "str",
                        param_type: "text",
                        validate: {
                            required: true,
                        },
                        when: {
                            param: "enable_budgets",
                            eq: true,
                        },
                        container_group_name: "project_definition",
                        readonly: !this.isAdmin(),
                    },
                    ...this.buildResourceConfigurationAdvancedOptions()
                ]}
                toolsOpen={this.props.toolsOpen} 
                tools={this.props.tools}
                onToolsChange={this.props.onToolsChange}
            />
        )
    }

    retrieveScripts(values: any): { [os: string]: { [event: string]: { script_location: string, arguments: string[] }[] } } {
        const scripts: { [os: string]: { [event: string]: { script_location: string, arguments: string[] }[] } } = {};
        const supportedOs = ["windows", "linux"];
        const scriptEvents = ["on_vdi_start", "on_vdi_configured"];

        for (const osType of supportedOs) {
            if (values[osType]) {
                scripts[osType] = {};
                for (const scriptEvent of scriptEvents) {
                    if (values[`${osType}_${scriptEvent}_toggle`]) {
                        const scriptsArray = values[`${osType}_${scriptEvent}_scripts`] || [];
                        scripts[osType][scriptEvent] = scriptsArray.map((script: { key: string, value: string }) => ({
                            script_location: script.key,
                            arguments: script.value.split(',')
                        }));
                    }
                }
            }
        }

        return scripts;
    }

    reverseScripts(scripts: Scripts): any {
        const values: any = {};
        if (scripts.windows) {
            values['windows'] = true;
            for (const eventType of Object.keys(scripts.windows) as Array<keyof ScriptEvents>) {
                const toggleKey = `windows_${eventType}_toggle`;
                values[toggleKey] = !!scripts.windows[eventType]?.length;

                values[`windows_${eventType}_scripts`] =  scripts.windows[eventType]?.map(script => ({
                    key: script.script_location,
                    value: script.arguments?.join(',') || ''
                })) || [];
            }
        }

        if (scripts.linux) {
            values['linux'] = true;
            for (const eventType of Object.keys(scripts.linux) as Array<keyof ScriptEvents>) {
                const toggleKey = `linux_${eventType}_toggle`;
                values[toggleKey] = !!scripts.linux[eventType]?.length;

                values[`linux_${eventType}_scripts`] =  scripts.linux[eventType]?.map(script => ({
                    key: script.script_location,
                    value: script.arguments?.join(',') || ''
                })) || [];;
            }
        }

        return values;

    }

    canSubmit(): boolean {
      if(!this.configureProjectForm.current!.validate()) {
        return false;
      }
      if (this.state.attachedGroups.length === 0) {
          this.getConfigureProjectForm().setError("400", "No groups attached");
          return false;
      }
      // If we have a new form
      for (const group of this.state.attachedGroups) {
        if (group.key.length === 0) {
          this.getConfigureProjectForm().setError("400", "Invalid Group");
          return false;
        }
      }
      for (const user of this.state.attachedUsers) {
        if (user.key.length === 0) {
          this.getConfigureProjectForm().setError("400", "Invalid User");
          return false;
        }
      }
      return true;
    }

    submitForm() {
        if (!this.canSubmit()) {
          return;
        }
        const values = this.configureProjectForm.current!.getValues();
        let createOrUpdate;
        let filesystemNames;
        let scripts;
        if (this.state.isUpdate) {
            createOrUpdate = async (request: any) => {
              // Only admin can update project
              // users with other permissions can only update role assignments
              const updates = [];
              if (this.isAdmin()) {
                updates.push(this.projects().updateProject(request));
              }
              updates.push(Promise.resolve(this.updateRoleAssignments()));
              return Promise.all(updates);
            }
            values.project_id = this.state.project?.project_id;
        } else {
            filesystemNames = dot.del("add_filesystems", values);
            filesystemNames = filesystemNames.filter((filesystemName: string) => filesystemName !== "home");
            createOrUpdate = async (request: any) => {
                  this.projects().createProject(request)
                  .then((result) => {
                    return this.createRoleAssignments(result.project?.project_id!);
                  });
            }
        }
        const advanced_options_enabled = dot.del("advanced_options", values);
        if(advanced_options_enabled) {
            scripts = this.retrieveScripts(values)
            dot.set("scripts", scripts, values)
        }
        createOrUpdate({
            project: values,
            filesystem_names: filesystemNames,
        })
            .then(() => {
                this.props.navigate("/cluster/projects")
            })
            .catch((error) => {
                this.getConfigureProjectForm().setError(error.errorCode, error.message);
            });
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
                        text: "Virtual Desktop",
                        href: "#/cluster/status",
                    },
                    {
                        text: "Projects",
                        href: "#/cluster/projects",
                    },
                    {
                        text: this.state.isUpdate ? "Edit Project" : "Create new Project",
                        href: "",
                    },
                ]}
                header={
                    <Header
                        variant={"h1"}
                    >
                        {this.state.isUpdate ? "Edit Project" : "Create new Project"}
                    </Header>
                }
                contentType={"default"}
                content={
                    <div>
                        <SpaceBetween size="m">
                          {this.buildCreateProjectForm()}
                          <Container header={<Header variant="h3">Team Configurations</Header>}>
                            <SpaceBetween size="m">
                              {this.buildGroupParam()}
                              {this.buildUserParam()}
                            </SpaceBetween>
                          </Container>
                          <SpaceBetween size="m" direction="vertical" alignItems="end">
                            <SpaceBetween size="m" direction="horizontal">
                                <Button variant="normal" onClick={() => this.props.navigate("/cluster/projects")}>Cancel</Button>
                                <Button variant="primary" onClick={() => this.submitForm()}>Submit</Button>
                            </SpaceBetween>
                          </SpaceBetween>
                        </SpaceBetween>
                    </div>
                }
            />
        );
    }
}

export default withRouter(ConfigureProject);
