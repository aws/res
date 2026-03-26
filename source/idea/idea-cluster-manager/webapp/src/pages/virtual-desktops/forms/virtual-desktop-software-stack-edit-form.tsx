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
import {Project, SocaMemory, SocaUserInputChoice} from "../../../client/data-model";
import { ProjectsClient } from "../../../client";
import { AppContext } from "../../../common";
import Utils from "../../../common/utils";
import { VirtualDesktopBaseOs, VirtualDesktopGpu, VirtualDesktopPlacement, VirtualDesktopSoftwareStack, VirtualDesktopTenancy } from "../../../client/generated/api";
import { 
    handleInstanceTypeUpdate,
    fetchInstanceTypeChoices,
    createFieldUpdaters,
} from "../utils/software-stack-form-utils";

export interface VirtualDesktopSoftwareStackEditFormProps {
    supportedOsChoices: SocaUserInputChoice[];
    supportedGPUChoices: SocaUserInputChoice[];
    allowedInstanceTypes: string[];
    softwareStack: VirtualDesktopSoftwareStack;
    onDismiss: () => void;
    onSubmit: (stack_id: string, base_os: VirtualDesktopBaseOs, name: string, description: string, ami_id: string, gpu: VirtualDesktopGpu, min_storage: SocaMemory,
        min_ram: SocaMemory, projects: Project[], placement: VirtualDesktopPlacement, allowed_instance_types: string[]) => Promise<boolean>;
}

export interface VirtualDesktopSoftwareStackEditFormState {
    showModal: boolean;
    projectChoices: SocaUserInputChoice[];
    tenancyChoices: SocaUserInputChoice[],
    affinityChoices: SocaUserInputChoice[],
    targetHostChoices: SocaUserInputChoice[],
    instanceTypeChoices: SocaUserInputChoice[];
    softwareStackForEdit: Partial<VirtualDesktopSoftwareStack>;
    debounceTimer: NodeJS.Timeout | null;
}

class VirtualDesktopSoftwareStackEditForm extends Component<VirtualDesktopSoftwareStackEditFormProps, VirtualDesktopSoftwareStackEditFormState> {
    form: RefObject<IdeaForm>;

    constructor(props: VirtualDesktopSoftwareStackEditFormProps) {
        super(props);
        this.form = React.createRef();
        this.state = {
            showModal: false,
            projectChoices: [],
            tenancyChoices: Utils.getTenancyChoices(),
            affinityChoices: Utils.getAffinityChoices(),
            targetHostChoices: Utils.getTargetHostChoices(),
            instanceTypeChoices: [],
            softwareStackForEdit: {
                ...this.props.softwareStack
            },
            debounceTimer: null,
        };
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

    async updateInstanceTypes() {
        try {
            const instanceTypeChoices = await fetchInstanceTypeChoices(this.state.softwareStackForEdit);
            this.setState({ instanceTypeChoices }, () => {
                this.getForm()?.getFormField("allowed_instance_types")?.setOptions({
                    listing: instanceTypeChoices,
                });
            });
        } catch (error: any) {
            this.getForm()?.setError(error.errorCode || 'FETCH_ERROR', error.message || 'Failed to fetch instance types');
        }
    }

    async showModal() {
        await this.updateInstanceTypes();
        this.setState({ showModal: true }, () => {
            this.getForm().showModal();
        });
    }

    getProjectsClient(): ProjectsClient {
        return AppContext.get().client().projects();
    }

    getForm() {
        return this.form.current!;
    }

    setError(errorCode: string, errorMessage: string) {
        this.getForm().setError(errorCode, errorMessage);
    }

    getCurrentProjectsChoices(): string[] {
        let choices: string[] = [];
        this.props.softwareStack.projects?.forEach((project) => {
            choices.push(project.project_id!);
        });
        return choices;
    }

    getCurrentTargetHostChoice(): string | undefined {
        if (this.props.softwareStack.placement && this.props.softwareStack.placement.tenancy === "host" ) {
            if (this.props.softwareStack.placement.host_id) {
                return "host_id"
            } else {
                return "host_resource_group"
            }
        }
        else {
            return undefined
        }
    }

    componentDidMount() {
        const allowedInstanceTypes = this.props.allowedInstanceTypes;
        let instanceTypeChoices: SocaUserInputChoice[] = [];
        allowedInstanceTypes.forEach((type) => {
            instanceTypeChoices.push({
                title: type,
                value: type,
            });
        });

        this.setState({
            instanceTypeChoices: instanceTypeChoices
        }, () => {
            this.getForm()?.getFormField("allowed_instance_types")?.setOptions({
                    listing: instanceTypeChoices
                });
            });

        this.getProjectsClient()
            .listProjects({})
            .then((result) => {
                let projectChoices: SocaUserInputChoice[] = [];
                result.listing?.forEach((project) => {
                    projectChoices.push({
                        title: project.title,
                        value: project.project_id,
                        description: project.description,
                    });
                });
                this.setState(
                    {
                        projectChoices: projectChoices,
                    },
                    () => {
                        this.getForm()?.getFormField("projects")?.setOptions({
                            listing: this.state.projectChoices,
                        });
                    }
                );
            });
    }

    async componentDidUpdate(prevProps: VirtualDesktopSoftwareStackEditFormProps, prevState: VirtualDesktopSoftwareStackEditFormState) {
        if (!this.state.showModal) {
            return;
        }

        if (prevState.softwareStackForEdit === this.state.softwareStackForEdit) {
            return;
        }

        await handleInstanceTypeUpdate({
            prevStack: prevState.softwareStackForEdit,
            currStack: this.state.softwareStackForEdit,
            debounceTimer: this.state.debounceTimer,
            clearTimer: () => this.setState({ debounceTimer: null }),
            setTimer: (timer) => this.setState({ debounceTimer: timer }),
            clearError: () => this.getForm()?.clearError(),
            updateInstanceTypes: () => this.updateInstanceTypes(),
            updateStack: (stack) => this.setState({ softwareStackForEdit: stack }),
        });
    }

    componentWillUnmount() {
        if (this.state.debounceTimer) {
            clearTimeout(this.state.debounceTimer);
        }
    }

    render() {
        return (
            this.state.showModal && (
                <IdeaForm
                    ref={this.form}
                    name={"update-software-stack"}
                    modal={true}
                    title={"Update Software Stack: " + this.props.softwareStack.name}
                    modalSize={"medium"}
                    onCancel={() => {
                        this.hideForm();
                    }}
                    onStateChange={(event) => {
                        const paramName = event.param.name;
                        if (!paramName) return;
                        
                        const values = this.getForm().getValues();
                        const updatedStack = { ...this.state.softwareStackForEdit };
                        const fieldUpdaters = createFieldUpdaters(values, updatedStack);
                        
                        if (fieldUpdaters[paramName]) {
                            fieldUpdaters[paramName]();
                            this.setState({ softwareStackForEdit: updatedStack });
                        }
                    }}
                    onSubmit={() => {
                        this.getForm().clearError();
                        if (!this.getForm().validate()) {
                            return;
                        }

                        if (this.props.softwareStack === undefined) {
                            return;
                        }

                        const values = this.getForm().getValues();
                        let projects: Project[] = [];
                        values.projects?.forEach((project_id: string) => {
                            projects.push({
                                project_id: project_id,
                            });
                        });

                        const stack_id = this.props.softwareStack?.stack_id!;
                        const base_os = this.props.softwareStack?.base_os!;
                        const name = values.name;
                        const description = values.description;
                        const ami_id = values.ami_id.toLowerCase().trim();
                        const gpu = values.gpu;
                        const min_storage: SocaMemory = {
                            value: values.root_storage_size,
                            unit: "gb",
                        };
                        const min_ram: SocaMemory = {
                            value: values.ram_size,
                            unit: "gb",
                        };
                        const placement: VirtualDesktopPlacement = {
                            affinity: values.affinity,
                            tenancy: values.tenancy,
                            host_id: (values.target_host_by === "host_id") ? values.host_id : undefined,
                            host_resource_group_arn: (values.target_host_by === "host_resource_group") ? values.host_resource_group_arn : undefined,
                        };
                        const instance_types = values.allowed_instance_types
                        if (this.props.onSubmit) {
                            return this.props.onSubmit(stack_id, base_os, name, description, ami_id, gpu, min_storage, min_ram, projects, placement, instance_types);
                        } else {
                            return Promise.resolve(true);
                        };
                    }}
                    params={[
                        {
                            name: "name",
                            title: "Stack Name",
                            description: "Enter a name for the Software Stack.",
                            help_text: "Use any characters and form a name of length between 3 and 24 characters, inclusive.",
                            data_type: "str",
                            param_type: "text",
                            default: this.props.softwareStack?.name,
                            validate: {
                                required: true,
                                regex: "^.{3,24}$",
                                message: "Use any characters and form a name of length between 3 and 24 characters, inclusive."
                            },
                        },
                        {
                            name: "description",
                            title: "Description",
                            description: "Enter a user friendly description for the software stack",
                            data_type: "str",
                            param_type: "text",
                            default: this.props.softwareStack?.description,
                            validate: {
                                required: true,
                            },
                        },
                        {
                            name: "ami_id",
                            title: "AMI ID / Systems Manager Parameter ARN",
                            description: "Enter the AMI ID or Systems Manager Parameter ARN",
                            help_text: "AMI ID must start with ami-xxx. Systems Manager Parameter ARN must follow the ARN format",
                            data_type: "str",
                            param_type: "text",
                            default: this.state.softwareStackForEdit.ami_id,
                            validate: {
                                required: true,
                            },
                        },
                        {
                            name: "base_os",
                            title: "Operating System",
                            description: "Select the operating system for the software stack",
                            data_type: "str",
                            param_type: "select",
                            validate: {
                                required: true,
                            },
                            readonly: true,
                            default: this.props.softwareStack?.base_os,
                            choices: this.props.supportedOsChoices,
                        },
                        {
                            name: "gpu",
                            title: "GPU Manufacturer",
                            description: "Select the GPU Manufacturer for the software stack",
                            data_type: "str",
                            param_type: "select",
                            validate: {
                                required: true,
                            },
                            default: this.props.softwareStack?.gpu,
                            choices: this.props.supportedGPUChoices,
                        },
                        {
                            name: "root_storage_size",
                            title: "Min. Storage Size (GB)",
                            description: "Enter the min. storage size for your virtual desktop in GBs",
                            data_type: "int",
                            param_type: "text",
                            default: this.props.softwareStack?.min_storage?.value,
                            validate: {
                                required: true,
                            },
                        },
                        {
                            name: "ram_size",
                            title: "Min. RAM (GB)",
                            description: "Enter the min. ram for your virtual desktop in GBs",
                            data_type: "int",
                            param_type: "text",
                            default: this.props.softwareStack?.min_ram?.value,
                            validate: {
                                required: true,
                            },
                        },
                        {
                            name: "projects",
                            title: "Projects",
                            description: "Select applicable projects for the software stack",
                            data_type: "str",
                            param_type: "select",
                            multiple: true,
                            choices: this.state.projectChoices,
                            default: this.getCurrentProjectsChoices(),
                        },
                        {
                            name: "tenancy",
                            title: "Tenancy",
                            description: "The type of tenancy",
                            data_type: "str",
                            param_type: "select",
                            validate: {
                                required: true,
                            },
                            default: this.props.softwareStack.placement?.tenancy ?? "default",
                            choices: this.state.tenancyChoices,
                        },
                        {
                            name: "affinity",
                            title: "Tenancy Affinity",
                            description: "The relationship between an instance and a dedicated host",
                            data_type: "str",
                            param_type: "select",
                            validate: {
                                required: true,
                            },
                            default: this.props.softwareStack.placement?.affinity,
                            choices: this.state.affinityChoices,
                            when:  {
                                param: "tenancy",
                                eq: "host",
                            },
                        },
                        {
                            name: "target_host_by",
                            title: "Target Host By",
                            description: "The type of target host",
                            data_type: "str",
                            param_type: "select",
                            validate: {
                                required: true,
                            },
                            default: this.getCurrentTargetHostChoice(),
                            choices: this.state.targetHostChoices,
                            when:  {
                                param: "tenancy",
                                eq: "host",
                            },
                        },
                        {
                            name: "host_id",
                            title: "Tenancy Host ID",
                            description: "The ID of the dedicated host",
                            help_text: "",
                            data_type: "str",
                            param_type: "text",
                            validate: {
                                required: true,
                                regex: "^h-.+$",
                            },
                            default: this.props.softwareStack.placement?.host_id,
                            when: {
                                and: [
                                    {
                                        param: "tenancy",
                                        eq: "host",
                                    },
                                    {
                                        param: "target_host_by",
                                        eq: "host_id",
                                    }
                                ]
                            },
                        },
                        {
                            name: "host_resource_group_arn",
                            title: "Tenancy Host Resource Group ARN",
                            description: "The ARN of the dedicated resource group",
                            help_text: "",
                            data_type: "str",
                            param_type: "text",
                            default: this.props.softwareStack.placement?.host_resource_group_arn,
                            validate: {
                                required: true,
                                regex: "^(?:arn:(?:aws(?:-cn|-us-gov)?)):resource-groups:.+:\\d{12}:group/.{1,128}$",
                            },
                            when: {
                                and: [
                                    {
                                        param: "tenancy",
                                        eq: "host",
                                    },
                                    {
                                        param: "target_host_by",
                                        eq: "host_resource_group",
                                    }
                                ]
                            },
                        },
                        {
                            name: "allowed_instance_types",
                            title: "Allowed Instance Families and Types",
                            description: "Select instance families and types allowed for this software stack",
                            data_type: "str",
                            param_type: "select",
                            multiple: true,
                            choices: this.state.instanceTypeChoices,
                            default: this.state.softwareStackForEdit.allowed_instance_types || [],
                        },
                    ]}
                />
            )
        );
    }
}

export default VirtualDesktopSoftwareStackEditForm;
