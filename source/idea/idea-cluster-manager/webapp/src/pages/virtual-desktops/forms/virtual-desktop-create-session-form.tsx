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
import IdeaForm from "../../../components/form";
import { Project, SocaMemory, SocaUserInputChoice, SocaUserInputParamMetadata, User, VDIPermissions, VirtualDesktopArchitecture, VirtualDesktopBaseOS, VirtualDesktopGPU, VirtualDesktopSessionType, VirtualDesktopSoftwareStack } from "../../../client/data-model";
import Utils from "../../../common/utils";
import { AccountsClient, AuthClient, ProjectsClient, VirtualDesktopClient } from "../../../client";
import { AppContext } from "../../../common";
import { Constants } from "../../../common/constants";
import VirtualDesktopUtilsClient from "../../../client/virtual-desktop-utils-client";

export interface VirtualDesktopCreateSessionFormProps {
    userProjects?: Project[];
    defaultName?: string;
    maxRootVolumeMemory: number;
    isAdminView?: boolean;
    onSubmit: (session_name: string, username: string, project_id: string, base_os: VirtualDesktopBaseOS, software_stack_id: string, session_type: VirtualDesktopSessionType, instance_type: string, storage_size: number, hibernation_enabled: boolean, vpc_subnet_id: string, session_tags: Record<string,string>[]) => Promise<boolean>;
    onDismiss: () => void;
}

export interface DCVSessionTypeChoice {
    choices: SocaUserInputChoice[];
    defaultChoice: "CONSOLE" | "VIRTUAL";
    disabled: boolean;
}

export interface VirtualDesktopCreateSessionFormState {
    showModal: boolean;
    softwareStacks: { [k: string]: VirtualDesktopSoftwareStack };
    supportedOsChoices: SocaUserInputChoice[];
    dcvSessionTypeChoice: DCVSessionTypeChoice;
    eVDIUsers: User[];
}

class VirtualDesktopCreateSessionForm extends Component<VirtualDesktopCreateSessionFormProps, VirtualDesktopCreateSessionFormState> {
    form: RefObject<IdeaForm>;
    instanceTypesInfo: any;
    defaultInstanceTypeChoices: SocaUserInputChoice[];

    constructor(props: VirtualDesktopCreateSessionFormProps) {
        super(props);
        this.form = React.createRef();
        this.state = {
            showModal: false,
            softwareStacks: {},
            supportedOsChoices: [],
            eVDIUsers: [],
            dcvSessionTypeChoice: {
                choices: Utils.getDCVSessionTypes(),
                defaultChoice: "VIRTUAL",
                disabled: false,
            },
        };
        this.instanceTypesInfo = {};
        this.defaultInstanceTypeChoices = [];
    }

    authAdmin(): AccountsClient {
        return AppContext.get().client().accounts();
    }

    getAuthClient(): AuthClient {
        return AppContext.get().client().auth();
    }

    getProjectsClient(): ProjectsClient {
        return AppContext.get().client().projects();
    }

    getVirtualDesktopUtilsClient(): VirtualDesktopUtilsClient {
        return AppContext.get().client().virtualDesktopUtils();
    }

    getVirtualDesktopClient(): VirtualDesktopClient {
        return AppContext.get().client().virtualDesktop();
    }

    hideForm() {
        this.setState(
            {
                showModal: false,
            },
            () => {
                this.props.onDismiss();
            }
        );
    }

    setError(errorCode: string, message: string) {
        this.getForm().setError(errorCode, message);
    }

    getForm() {
        return this.form.current!;
    }

    showModal() {
        this.setState(
            {
                showModal: true,
            },
            () => {
                this.getForm().showModal();
            }
        );
    }

    componentDidMount() {
        this.getVirtualDesktopUtilsClient()
            .listAllowedInstanceTypes({})
            .then((result) => {
                this.instanceTypesInfo = this.generateInstanceTypeReverseIndex(result.listing);
                this.defaultInstanceTypeChoices = Utils.generateInstanceTypeListing(result.listing);
            });

        this.getVirtualDesktopUtilsClient()
            .listSupportedOS({})
            .then((result) => {
                this.setState(
                    {
                        supportedOsChoices: Utils.getSupportedOSChoices(result.listing!),
                    },
                    () => {
                        this.getForm()?.getFormField("base_os")?.setOptions({
                            listing: this.state.supportedOsChoices,
                        });
                    }
                );
            });

        this.authAdmin()
            .listUsers({ filters: [{ key: "is_active", eq: true }] })
            .then((group_response) => {
                this.setState(
                    {
                        eVDIUsers: group_response.listing!,
                    },
                    () => {
                        this.getForm()
                            ?.getFormField("user_name")
                            ?.setOptions({
                                listing: Utils.generateUserSelectionChoices(
                                    this.state.eVDIUsers,
                                    this.props.userProjects?.find(project => project.project_id! === this.getForm()?.getValue("project_id")),
                                    this.isAdmin(),
                                ),
                            });
                    }
                );
            });
    }

    isAdmin(): boolean {
        return AppContext.get().auth().isAdmin();
    }

    generateInstanceTypeReverseIndex(instanceTypeList: any[]): { [k: string]: any } {
        let reverseIndex: { [k: string]: any } = {};
        if (instanceTypeList !== undefined) {
            instanceTypeList.forEach((instance_type: any) => {
                reverseIndex[instance_type.InstanceType as string] = instance_type;
            });
        }
        return reverseIndex;
    }

    compare_software_stacks = (a: VirtualDesktopSoftwareStack, b: VirtualDesktopSoftwareStack): number => {
        if (a === undefined && b === undefined) {
            return 0;
        }

        if (a === undefined || a.architecture === undefined) {
            return -1;
        }

        if (b === undefined || b.architecture === undefined) {
            return 1;
        }

        if (a.architecture === b.architecture) {
            // these two are the same architecture. Return GPU
            if (a.gpu === b.gpu) {
                // these two are the same architecture and GPU. Return alphabetical
                if (a.name === undefined) {
                    return 1;
                }
                if (b.name === undefined) {
                    return -1;
                }
                return a.name.toLowerCase().localeCompare(b.name.toLowerCase(), undefined, { numeric: true });
            } else {
                if (a.gpu === "NO_GPU") {
                    return -1;
                }
                if (b.gpu === "NO_GPU") {
                    return 1;
                }
                if (a.gpu === "NVIDIA") {
                    return -1;
                }
                if (b.gpu === "NVIDIA") {
                    return 1;
                }
                if (a.gpu === "AMD") {
                    return -1;
                }
                return 1;
            }
        }

        if (a.architecture === "x86_64") {
            return -1;
        }
        if (b.architecture === "x86_64") {
            return 1;
        }
        if (a.architecture === "arm64") {
            return -1;
        }
        return 1;
    };

    generateSoftwareStackListing(softwareStacks: VirtualDesktopSoftwareStack[] | undefined): SocaUserInputChoice[] {
        let softwareStackChoices: SocaUserInputChoice[] = [];

        softwareStacks?.sort(this.compare_software_stacks);

        softwareStacks?.forEach((stack) => {
            softwareStackChoices.push({
                title: stack.description,
                description: `Name: ${stack.name}, AMI ID: ${stack.ami_id}, OS: ${stack.base_os}, GPU: ${Utils.getFormattedGPUManufacturer(stack.gpu)}`,
                value: stack.stack_id,
            });
        });
        return softwareStackChoices;
    }

    getInstanceArch(instance_type: string): VirtualDesktopArchitecture | undefined {
        if (this.instanceTypesInfo === undefined) {
            return undefined;
        }
        let instanceTypeInfo: any = this.instanceTypesInfo[instance_type];
        if (instanceTypeInfo === undefined) {
            return undefined;
        }
        let isARM = false;
        let isX86 = false;
        instanceTypeInfo?.ProcessorInfo?.SupportedArchitectures?.forEach((arch: any) => {
            if (arch === "arm64") {
                isARM = true;
            }
            if (arch === "x86_64") {
                isX86 = true;
            }
        });
        if (isX86) {
            return "x86_64";
        }
        if (isARM) {
            return "arm64";
        }
        return undefined;
    }

    getInstanceGPU(instance_type: string): VirtualDesktopGPU {
        if (this.instanceTypesInfo === undefined) {
            return "NO_GPU";
        }
        let instanceTypeInfo: any = this.instanceTypesInfo[instance_type];
        if (instanceTypeInfo === undefined) {
            return "NO_GPU";
        }

        let isAMD = false;
        let isNVIDIA = false;
        instanceTypeInfo?.GpuInfo?.Gpus?.forEach((gpuInfo: any) => {
            if (gpuInfo.Manufacturer === "AMD") {
                isAMD = true;
            }

            if (gpuInfo.Manufacturer === "NVIDIA") {
                isNVIDIA = true;
            }
        });

        if (isAMD) return "AMD";
        if (isNVIDIA) return "NVIDIA";
        return "NO_GPU";
    }

    getInstanceRAM(instance_type: string): SocaMemory {
        if (this.instanceTypesInfo === undefined) {
            return {
                value: 0,
                unit: "gb",
            };
        }

        let instanceTypeInfo: any = this.instanceTypesInfo[instance_type];
        if (instanceTypeInfo === undefined) {
            return {
                value: 0,
                unit: "gb",
            };
        }
        return {
            unit: "gb",
            value: instanceTypeInfo.MemoryInfo.SizeInMiB / 1024,
        };
    }

    getMinRootVolumeSizeInGB(softwareStack: VirtualDesktopSoftwareStack, isHibernationEnabled: boolean, instanceTypeName: string): SocaMemory {
        let min_storage_gb: SocaMemory = {
            unit: "gb",
            value: 0,
        };
        if (softwareStack && softwareStack.min_storage) {
            min_storage_gb = {
                unit: softwareStack.min_storage.unit,
                value: softwareStack.min_storage.value,
            };
        }
        if (isHibernationEnabled && instanceTypeName) {
            min_storage_gb.value += this.getInstanceRAM(instanceTypeName).value;
        }
        return min_storage_gb;
    }

    buildProjectChoices(projects: Project[]): SocaUserInputChoice[] {
        let projectChoices: SocaUserInputChoice[] = [];
        projects?.forEach((project) => {
            projectChoices.push({
                title: project.title,
                value: project.project_id,
                description: project.description,
            });
        });
        return projectChoices;
    }

    updateSoftwareStackOptions() {
        let project_id = this.getForm()?.getFormField("project_id")?.getValueAsString();
        let base_os = this.getForm()?.getFormField("base_os")?.getValueAsString();
        if (Utils.isEmpty(project_id) || Utils.isEmpty(base_os)) {
            return;
        }
        this.getVirtualDesktopClient()
            .listSoftwareStacks({
                disabled_also: true,
                project_id: project_id,
                paginator: {
                    page_size: 100,
                },
                filters: [
                    {
                        key: "base_os",
                        value: base_os,
                    },
                ],
            })
            .then((result) => {
                const softwareStack = this.getForm()?.getFormField("software_stack");
                softwareStack?.setOptions({
                    listing: this.generateSoftwareStackListing(result.listing),
                });

                let softwareStacks: { [k: string]: VirtualDesktopSoftwareStack } = {};
                result.listing?.forEach((stack) => {
                    if (stack.stack_id !== undefined) {
                        softwareStacks[stack.stack_id] = stack;
                    }
                });
                this.setState({
                    softwareStacks: softwareStacks,
                });
            });
    }

    updateRootVolumeSizeIfRequired() {
        let softwareStack = this.state.softwareStacks[this.getForm()?.getValue("software_stack")];
        let isHibernationSupported = Utils.asBoolean(this.getForm()?.getValue("hibernate_instance"));
        let instanceTypeName = this.getForm()?.getValue("instance_type");
        let min_storage_gb = this.getMinRootVolumeSizeInGB(softwareStack, isHibernationSupported, instanceTypeName);
        let root_storage_size = this.getForm()?.getFormField("root_storage_size");
        let current_storage_size = Utils.asNumber(root_storage_size?.getValueAsString());
        if (current_storage_size < min_storage_gb.value!) {
            root_storage_size?.setValue(min_storage_gb.value!);
        }
    }

    updateSessionTypeChoicesIfRequired() {
        const dcvSessionType = this.getForm()?.getFormField("dcv_session_type");
        let dcvSessionTypeChoices: SocaUserInputChoice[] = [];
        const base_os = this.getForm()?.getValue("base_os");
        let instanceTypeName = this.getForm()?.getValue("instance_type");
        let gpu = this.getInstanceGPU(instanceTypeName);
        let arch = this.getInstanceArch(instanceTypeName);
        let dcvSessionTypeDefaultChoice: "VIRTUAL" | "CONSOLE" = "VIRTUAL";
        let disableSessionTypeChoice = false;

        const console_choice = {
            title: "Console",
            value: "CONSOLE",
        };
        const virtual_choice = {
            title: "Virtual",
            value: "VIRTUAL",
        };
        if (arch === "arm64") {
            dcvSessionTypeDefaultChoice = "VIRTUAL";
            dcvSessionTypeChoices.push(virtual_choice);
            disableSessionTypeChoice = true;
        } else if (base_os === "windows" || gpu === "AMD") {
            // https://docs.aws.amazon.com/dcv/latest/adminguide/servers.html - AMD GPU, Windows support Console sessions only
            dcvSessionTypeDefaultChoice = "CONSOLE";
            dcvSessionTypeChoices.push(console_choice);
            disableSessionTypeChoice = true;
        } else {
            dcvSessionTypeChoices.push(console_choice);
            dcvSessionTypeChoices.push(virtual_choice);
        }
        this.setState({
            ...this.state,
            dcvSessionTypeChoice: {
                choices: dcvSessionTypeChoices,
                defaultChoice: dcvSessionTypeDefaultChoice,
                disabled: disableSessionTypeChoice,
            },
        });
        dcvSessionType?.setOptions({
            listing: dcvSessionTypeChoices,
        });
        dcvSessionType?.setValue(dcvSessionTypeDefaultChoice);
        dcvSessionType?.disable(disableSessionTypeChoice);
    }

    buildFormParams(): SocaUserInputParamMetadata[] {
        let formParams: SocaUserInputParamMetadata[] = [];

        formParams.push({
            name: "session_name",
            title: "Session Name",
            description: "Enter a name for the virtual desktop",
            data_type: "str",
            param_type: "text",
            help_text: "Session Name is required. Use any characters and form a name of length between 3 and 24 characters, inclusive.",
            default: this.props.defaultName!,
            auto_focus: true,
            validate: {
                required: true,
                regex: "^.{3,24}$",
                message: "Use any characters and form a name of length between 3 and 24 characters, inclusive.",
            },
        });

        formParams.push({
            name: "project_id",
            title: "Project",
            description: "Select the project under which the session will get created",
            data_type: "str",
            param_type: "select",
            validate: {
                required: true,
            },
            choices: this.buildProjectChoices(this.props.userProjects!),
        });

        // Don't render User selection until project is selected,
        // and then only if user is admin or has permission to create sessions for others
        if (this.getForm()?.getValue("project_id")) {
            if (this.props.isAdminView) {
                formParams.push({
                    name: "user_name",
                    title: "User",
                    description: "Select the user to create the session for. Sessions can only be created for active user's.",
                    data_type: "str",
                    param_type: "select_or_text",
                    
                    validate: {
                        required: true,
                    },
                    choices: Utils.generateUserSelectionChoices(
                        this.state.eVDIUsers,
                        this.props.userProjects?.find(project => project.project_id! === this.getForm()?.getValue("project_id")),
                        this.isAdmin(),
                    ),
                });
            }
        }

        
        formParams.push({
            name: "base_os",
            title: "Operating System",
            description: "Select the operating system for the virtual desktop",
            data_type: "str",
            param_type: "select",
            validate: {
                required: true,
            },
            default: "amazonlinux2",
            choices: this.state.supportedOsChoices,
        });
        formParams.push({
            name: "software_stack",
            title: "Software Stack",
            description: "Select the software stack for your virtual desktop",
            data_type: "str",
            param_type: "select",
            validate: {
                required: true,
            },
            choices: [],
        });
        formParams.push({
            name: "hibernate_instance",
            title: "Enable Instance Hibernation",
            description: "Hibernation saves the contents from the instance memory (RAM) to your Amazon Elastic Block Store (Amazon EBS) root volume. You can not change instance type if you enable this option.",
            data_type: "bool",
            param_type: "confirm",
            default: false,
            validate: {
                required: true,
            },
        });
        formParams.push({
            name: "instance_type",
            title: "Virtual Desktop Size",
            description: "Select a virtual desktop instance type",
            data_type: "str",
            param_type: "select_or_text",
            validate: {
                required: true,
            },
            choices: this.defaultInstanceTypeChoices,
        });
        formParams.push({
            name: "root_storage_size",
            title: "Storage Size (GB)",
            description: "Enter the storage size for your virtual desktop in GBs",
            data_type: "int",
            param_type: "text",
            default: 10,
            validate: {
                required: true,
                max: this.props.maxRootVolumeMemory,
            },
        });
        formParams.push({
            name: "advanced_options",
            title: "Show Advanced Options",
            data_type: "bool",
            param_type: "confirm",
            validate: {
                required: true,
            },
            default: false,
        });
        formParams.push({
            name: "dcv_session_type",
            title: "DCV Session Type",
            description: "Select the DCV Session Type",
            data_type: "str",
            param_type: "select",
            readonly: this.state.dcvSessionTypeChoice.disabled,
            default: this.state.dcvSessionTypeChoice.defaultChoice,
            choices: this.state.dcvSessionTypeChoice.choices,
            validate: {
                required: true,
            },
            when: {
                param: "advanced_options",
                eq: true,
            },
        });
        formParams.push({
            name: "vpc_subnet_id",
            title: "VPC Subnet ID",
            description: "Launch your virtual desktop in a specific subnet",
            data_type: "str",
            param_type: "text",
            when: {
                param: "advanced_options",
                eq: true,
            },
        });
        const sessionTagKeys: SocaUserInputParamMetadata = {
            name: "session_tags_keys",
            description: "Key",
            param_type: "text",
            data_type: "str"
        };
        const sessionTagValues: SocaUserInputParamMetadata = {
            name: "session_tags_values",
            description: "Value",
            param_type: "text",
            data_type: "str"
        };
        formParams.push({
            name: "session_tags",
            title: "Session Tags",
            description: "Add tags for your virtual desktop. Provided tags will be added to the EC2 Instance.",
            param_type: "container",
            data_type: "record",
            container_items: [sessionTagKeys, sessionTagValues],
            multiple: true,
            default: [],
            when: {
                param: "advanced_options",
                eq: true,
            },
            validate: {
                required: true
            },
            custom_error_message: "Keys and Values cannot be empty."
        })

        return formParams;
    }

    render() {
        return (
            this.state.showModal && (
                <IdeaForm
                    ref={this.form}
                    name="create-session"
                    modal={true}
                    title="Launch New Virtual Desktop"
                    modalSize="medium"
                    onStateChange={(event) => {
                        if (event.param.name === "base_os") {
                            const hibernation = this.getForm()?.getFormField("hibernate_instance");
                            if (event.value === "windows") {
                                // Hibernation is conditionally supported for Windows
                                hibernation?.disable(false);
                            } else {
                                if (event.value === "amazonlinux2") {
                                    // Hibernation is supported for Amazon Linux 2 .
                                    //hibernation?.disable(false);
                                    hibernation?.setValue(false);
                                    hibernation?.disable(true);
                                } else {
                                    hibernation?.setValue(false);
                                    hibernation?.disable(true);
                                }
                            }
                            this.updateSessionTypeChoicesIfRequired();
                            this.updateSoftwareStackOptions();
                        } else if (event.param.name === "software_stack") {
                            this.getVirtualDesktopUtilsClient()
                                .listAllowedInstanceTypes({
                                    hibernation_support: this.getForm()?.getValue("hibernate_instance"),
                                    software_stack: this.state.softwareStacks[event.value],
                                })
                                .then(async (result) => {
                                    let instance_type = this.getForm()?.getFormField("instance_type");
                                    await instance_type?.reset();
                                    instance_type?.setOptions({
                                        listing: Utils.generateInstanceTypeListing(result.listing),
                                    });
                                    this.updateRootVolumeSizeIfRequired();
                                });
                        } else if (event.param.name === "project_id") {
                            this.updateSoftwareStackOptions();
                        } else if (event.param.name === "instance_type") {
                            this.updateRootVolumeSizeIfRequired();
                            this.updateSessionTypeChoicesIfRequired();
                        } else if (event.param.name === "root_storage_size") {
                            let min_storage_gb = this.getMinRootVolumeSizeInGB(this.state.softwareStacks[this.getForm()?.getValue("software_stack")], this.getForm()?.getValue("hibernate_instance"), this.getForm()?.getValue("instance_type"));
                            if (event.value < min_storage_gb.value) {
                                event.ref.setState({
                                    errorMessage: `Storage size must be greater than or equal to: ${Utils.getFormattedMemory(min_storage_gb)}`,
                                });
                            } else {
                                event.ref.setState({
                                    errorMessage: "",
                                });
                            }
                        } else if (event.param.name === "hibernate_instance") {
                            this.getVirtualDesktopUtilsClient()
                                .listAllowedInstanceTypes({
                                    hibernation_support: event.value,
                                    software_stack: this.state.softwareStacks[this.getForm()?.getValue("software_stack")],
                                })
                                .then((result) => {
                                    let instance_type = this.getForm()?.getFormField("instance_type");
                                    instance_type?.setOptions({
                                        listing: Utils.generateInstanceTypeListing(result.listing),
                                    });
                                    this.updateRootVolumeSizeIfRequired();
                                });
                        }
                    }}
                    onSubmit={() => {
                        this.getForm()?.clearError();
                        if (!this.getForm()?.validate()) {
                            return;
                        }
                        const values = this.getForm()?.getValues();
                        const storage_size = Utils.asNumber(values.root_storage_size, 10);
                        const session_name = values.session_name;
                        const hibernation_enabled = Utils.asBoolean(values.hibernate_instance, false);
                        const software_stack_id = values.software_stack;
                        const base_os = values.base_os;
                        const vpc_subnet_id = values.vpc_subnet_id;
                        const project_id = values.project_id;
                        const session_type = values.dcv_session_type;
                        const instance_type = values.instance_type;
                        const session_tags = values.session_tags
                        let username = values.user_name;
                        if (this.props.onSubmit) {
                            return this.props.onSubmit(session_name, username, project_id, base_os, software_stack_id, session_type, instance_type, storage_size, hibernation_enabled, vpc_subnet_id, session_tags);
                        } else {
                            return Promise.resolve(true);
                        }
                    }}
                    onCancel={() => {
                        this.hideForm();
                    }}
                    params={this.buildFormParams()}
                />
            )
        );
    }
}

export default VirtualDesktopCreateSessionForm;
