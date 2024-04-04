import React, {Component, RefObject} from "react";
import IdeaAppLayout, {IdeaAppLayoutProps} from "../../components/app-layout";
import {IdeaSideNavigationProps} from "../../components/side-navigation";
import { Header} from "@cloudscape-design/components";
import IdeaForm from "../../components/form";
import {withRouter} from "../../navigation/navigation-utils";
import Utils from "../../common/utils";
import {AppContext} from "../../common";
import {Project, ScriptEvents, Scripts, SocaUserInputChoice, SocaUserInputParamMetadata} from "../../client/data-model";
import {AccountsClient, ClusterSettingsClient} from "../../client";
import {Constants} from "../../common/constants";
import dot from "dot-object";

export interface ConfigureProjectState {
    isUpdate: boolean
    project?: Project
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
            project: state ? state.project : null
        };
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

    buildUserParam(): SocaUserInputParamMetadata[] {
        const params: SocaUserInputParamMetadata[] = [];
        params.push({
            name: "users",
            title: "Users",
            description: "Select applicable users for the Project",
            param_type: "select",
            multiple: true,
            data_type: "str",
            dynamic_choices: true,
            validate: {
                required: false,
            },
            container_group_name: "team_configurations"
        });
        return params;
    }

    buildAddFileSystemParam(isUpdate: boolean): SocaUserInputParamMetadata[] {
        const params: SocaUserInputParamMetadata[] = [];
        if (isUpdate) {
            return params;
        }
        params.push({
            name: "add_filesystems",
            title: "Add file systems",
            description: "Select applicable file systems for the Project",
            param_type: "select",
            multiple: true,
            data_type: "str",
            dynamic_choices: true,
            default: ["home"],
            container_group_name: "resource_configurations"
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
            })
            const script: SocaUserInputParamMetadata = {
                title: "Script",
                param_type: "text",
                data_type: "str",
            };
            const args: SocaUserInputParamMetadata = {
                title: "Arguments",
                description: "optional",
                param_type: "text",
                data_type: "str"
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
                showActions={true}
                useContainers={true}
                values={values}
                onSubmit={() => {
                    if(!this.getConfigureProjectForm().validate()) {
                        return;
                    }
                    const values = this.getConfigureProjectForm().getValues();
                    let createOrUpdate;
                    let filesystemNames;
                    let scripts;
                    if (isUpdate) {
                        createOrUpdate = (request: any) => this.projects().updateProject(request);
                            values.project_id = project?.project_id;
                    } else {
                        filesystemNames = dot.del("add_filesystems", values);
                        filesystemNames = filesystemNames.filter((filesystemName: string) => filesystemName !== "home");
                        createOrUpdate = (request: any) => this.projects().createProject(request);
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
                }}
                onCancel={() => this.props.navigate("/cluster/projects")}
                onFetchOptions={(request) => {
                    if (request.param === "ldap_groups") {
                            return this.accounts()
                                .listGroups({
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
                                    } else {
                                        const choices: SocaUserInputChoice[] = [];
                                        listing.forEach((value) => {
                                            choices.push({
                                                title: `${value.name} (${value.gid})`,
                                                value: value.name,
                                            });
                                        });
                                        return {
                                            listing: choices,
                                        };
                                    }
                                });
                        }
                    else if (request.param === "users") {
                            return this.accounts()
                                .listUsers()
                                .then((result) => {
                                    const listing = result.listing!;
                                    if (listing.length === 0) {
                                        return {
                                            listing: [],
                                        };
                                    } else {
                                        const choices: SocaUserInputChoice[] = [];
                                        listing.forEach((value) => {
                                            if (value.username !== "clusteradmin") {
                                                choices.push({
                                                    title: `${value.username} (${value.uid})`,
                                                    value: value.username,
                                                });
                                            }
                                        });
                                        return {
                                            listing: choices,
                                        };
                                    }
                                });
                        }
                     else if (request.param === "add_filesystems") {
                            let promises: Promise<any>[] = [];
                            promises.push(this.clusterSettings().getModuleSettings({ module_id: Constants.MODULE_SHARED_STORAGE }));
                            return Promise.all(promises).then((result) => {
                                const choices: SocaUserInputChoice[] = [];
                                const sharedFileSystem = result[0].settings;
                                Object.keys(sharedFileSystem).forEach((key) => {
                                    const storage = dot.pick(key, sharedFileSystem);
                                    const provider = dot.pick("provider", storage);
                                    if (Utils.isEmpty(provider)) {
                                        return true;
                                    }
                                    const isInternal = key === "internal";
                                    if (!isInternal) {
                                        let choice: SocaUserInputChoice = {
                                            title: `${key} [${provider}]`,
                                            value: `${key}`,
                                        };
                                        if (key === "home") {
                                            choice.disabled = true;
                                        }
                                        choices.push(choice);
                                    }
                                });
                                return { listing: choices };
                            });
                        }
                     else if (request.param === "security_groups") {
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
                    {
                        title: "Team Configurations",
                        name: "team_configurations",
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
                        container_group_name: "project_definition"
                    },
                    {
                        name: "name",
                        title: "Project ID",
                        description: "Enter a project-id",
                        help_text: "Project ID can only use lowercase alphabets, numbers, and hyphens (-). Must be between 3 and 18 characters long.",
                        data_type: "str",
                        param_type: "text",
                        readonly: isUpdate,
                        validate: {
                            required: true,
                            regex: "^([a-z0-9-]+){3,18}$",
                            message: "Only use lowercase alphabets, numbers, and hyphens (-). Must be between 3 and 18 characters long.",
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
                        container_group_name: "project_definition"
                    },
                    {
                        name: "ldap_groups",
                        title: "Groups",
                        description: "Select applicable ldap groups for the Project",
                        param_type: "select",
                        multiple: true,
                        data_type: "str",
                        validate: {
                            required: true,
                        },
                        dynamic_choices: true,
                        container_group_name: "team_configurations"
                    },
                    ...this.buildUserParam(),
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
                        container_group_name: "project_definition"
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
                        container_group_name: "project_definition"
                    },
                    ...this.buildResourceConfigurationAdvancedOptions()
                ]}

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
                        {this.buildCreateProjectForm()}
                    </div>
                }
            />
        );
    }
}

export default withRouter(ConfigureProject);
