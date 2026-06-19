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

import IdeaListView from "../../components/list-view";
import { ProjectsClient, VirtualDesktopAdminClient, VirtualDesktopClient } from "../../client";
import { AppContext } from "../../common";
import { TableProps } from "@cloudscape-design/components/table/interfaces";
import IdeaForm from "../../components/form";
import IdeaConfirm from "../../components/modals";
import {Project, SocaFilter, SocaUserInputChoice} from "../../client/data-model";
import Utils from "../../common/utils";
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import IdeaAppLayout, { IdeaAppLayoutProps } from "../../components/app-layout";
import { Link } from "@cloudscape-design/components";
import VirtualDesktopSoftwareStackEditForm from "./forms/virtual-desktop-software-stack-edit-form";
import { withRouter } from "../../navigation/navigation-utils";
import VirtualDesktopUtilsClient from "../../client/virtual-desktop-utils-client";
import {
    ResMemory,
    VirtualDesktopBaseOs,
    VirtualDesktopGpu,
    VirtualDesktopPlacement,
    VirtualDesktopSoftwareStack,
    VirtualDesktopSession,
} from "../../client/generated/api";
import {
    DEFAULT_SOFTWARE_STACK_BASE_OS,
    DEFAULT_SOFTWARE_STACK_GPU,
    DEFAULT_SOFTWARE_STACK_TENANCY,
    DEFAULT_SOFTWARE_STACK_MIN_RAM,
    DEFAULT_SOFTWARE_STACK_MIN_STORAGE,
    handleInstanceTypeUpdate,
    fetchInstanceTypeChoices,
    createFieldUpdaters,
} from "./utils/software-stack-form-utils";

export interface VirtualDesktopSoftwareStacksProps extends IdeaAppLayoutProps, IdeaSideNavigationProps { }

export interface VirtualDesktopSoftwareStacksState {
    affinityChoices: SocaUserInputChoice[];
    softwareStackSelected: boolean;
    supportedOsChoices: SocaUserInputChoice[];
    supportedGPUChoices: SocaUserInputChoice[];
    projectChoices: SocaUserInputChoice[];
    showRegisterSoftwareStackForm: boolean;
    showEditSoftwareStackForm: boolean;
    showDeleteStackConfirmModal: boolean;
    selectedSoftwareStackSessionsList: VirtualDesktopSession[];
    tenancyChoices: SocaUserInputChoice[];
    targetHostChoices: SocaUserInputChoice[];
    allowedInstanceTypes: string[];
    softwareStackForRegister: Partial<VirtualDesktopSoftwareStack>;
    instanceTypeChoicesForRegister: SocaUserInputChoice[];
    debounceTimerForRegister: NodeJS.Timeout | null;
}

const VIRTUAL_DESKTOP_SOFTWARE_STACKS_TABLE_COLUMN_DEFINITIONS: TableProps.ColumnDefinition<VirtualDesktopSoftwareStack>[] = [
    {
        id: "name",
        header: "Name",
        cell: (e) => <Link href={`/#/virtual-desktop/software-stacks/${e.stack_id}/${e.base_os}`}>{e.name}</Link>,
        sortingField: "name",
    },
    {
        id: "description",
        header: "Description",
        cell: (e) => e.description,
        sortingField: "description",
    },
    {
        id: "ami_id",
        header: "AMI ID / Systems Manager Parameter ARN",
        cell: (e) => e.ami_id,
        sortingField: "ami_id",
    },
    {
        id: "os",
        header: "Base OS",
        cell: (e) => Utils.getOsTitle(e.base_os),
        sortingComparator: (a, b) => (a.base_os || '').localeCompare(b.base_os || '')
    },
    {
        id: "root_volume_size",
        header: "Root Volume Size",
        cell: (e) => Utils.getFormattedMemory(e.min_storage),
        sortingComparator: (a, b) => {
            const valueA = a.min_storage?.value || 0;
            const valueB = b.min_storage?.value || 0;
            return valueA - valueB;
        }
    },
    {
        id: "min_ram",
        header: "Min RAM",
        cell: (e) => Utils.getFormattedMemory(e.min_ram),
        sortingComparator: (a, b) => {
            const valueA = a.min_ram?.value || 0;
            const valueB = b.min_ram?.value || 0;
            return valueA - valueB;
        }
    },
    {
        id: "gpu_manufacturer",
        header: "GPU Manufacturer",
        cell: (e) => Utils.getFormattedGPUManufacturer(e.gpu),
        sortingComparator: (a, b) => (a.gpu || '').localeCompare(b.gpu || '')
    },
    {
        id: "tenancy",
        header: "Tenancy",
        cell: (e) => Utils.getFormattedTenancy(e.placement),
    },
    {
        id: "availabile",
        header: "Availabile",
        cell: (e) => {
            if (!e.enabled) {
                return "No";
            } else {
                return "Yes";
            }
        },
    },
    {
        id: "created_on",
        header: "Created On",
        cell: (e) => new Date(e.created_on!).toLocaleString(),
        sortingField: "created_on",
    },
];

class VirtualDesktopSoftwareStacks extends Component<VirtualDesktopSoftwareStacksProps, VirtualDesktopSoftwareStacksState> {
    listing: RefObject<IdeaListView>;
    registerSoftwareStackForm: RefObject<IdeaForm>;
    editSoftwareStackForm: RefObject<VirtualDesktopSoftwareStackEditForm>;
    deleteStackConfirmModal: RefObject<IdeaConfirm>;

    constructor(props: VirtualDesktopSoftwareStacksProps) {
        super(props);
        this.listing = React.createRef();
        this.registerSoftwareStackForm = React.createRef();
        this.editSoftwareStackForm = React.createRef();
        this.deleteStackConfirmModal = React.createRef();
        this.state = {
            softwareStackSelected: false,
            supportedOsChoices: [],
            supportedGPUChoices: [],
            projectChoices: [],
            showRegisterSoftwareStackForm: false,
            showEditSoftwareStackForm: false,
            showDeleteStackConfirmModal: false,
            selectedSoftwareStackSessionsList: [],
            tenancyChoices: Utils.getTenancyChoices(),
            affinityChoices: Utils.getAffinityChoices(),
            targetHostChoices: Utils.getTargetHostChoices(),
            allowedInstanceTypes: [],
            softwareStackForRegister: {},
            instanceTypeChoicesForRegister: [],
            debounceTimerForRegister: null,
        };
    }

    componentDidMount() {
        this.setState({
            supportedOsChoices: Utils.getSupportedOSChoices(Object.values(VirtualDesktopBaseOs)),
        });

        this.setState({
            supportedGPUChoices: Utils.getSupportedGPUChoices(Object.values(VirtualDesktopGpu))
        })

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
                        this.getRegisterSoftwareStackForm()?.getFormField("projects")?.setOptions({
                            listing: this.state.projectChoices,
                        });
                    }
                );
            });
    }

    getListing(): IdeaListView {
        return this.listing.current!;
    }

    isSelected(): boolean {
        return this.state.softwareStackSelected;
    }

    getProjectsClient(): ProjectsClient {
        return AppContext.get().client().projects();
    }

    getVirtualDesktopAdminClient(): VirtualDesktopAdminClient {
        return AppContext.get().client().virtualDesktopAdmin();
    }

    getVirtualDesktopClient(): VirtualDesktopClient {
        return AppContext.get().client().virtualDesktop();
    }

    getVirtualDesktopUtilsClient(): VirtualDesktopUtilsClient {
        return AppContext.get().client().virtualDesktopUtils();
    }

    getRegisterSoftwareStackForm(): IdeaForm {
        return this.registerSoftwareStackForm.current!;
    }

    getDefaultSoftwareStackForRegister(): Partial<VirtualDesktopSoftwareStack> {
        return {
            name: "placeholder",
            base_os: DEFAULT_SOFTWARE_STACK_BASE_OS,
            gpu: DEFAULT_SOFTWARE_STACK_GPU,
            ami_id: "",
            placement: {
                tenancy: DEFAULT_SOFTWARE_STACK_TENANCY as any,
            },
            min_ram: {
                value: DEFAULT_SOFTWARE_STACK_MIN_RAM,
                unit: "gb",
            },
            min_storage: {
                value: DEFAULT_SOFTWARE_STACK_MIN_STORAGE,
                unit: "gb",
            },
            allowed_instance_types: []
        };
    }

    showRegisterSoftwareStackForm() {
        this.setState(
            {
                showRegisterSoftwareStackForm: true,
                softwareStackForRegister: this.getDefaultSoftwareStackForRegister(),
                instanceTypeChoicesForRegister: [],
            },
            () => {
                this.getRegisterSoftwareStackForm().showModal();
            }
        );
    }

    hideRegisterSoftwareStackForm() {
        this.setState({
            showRegisterSoftwareStackForm: false,
        });
    }

    async updateInstanceTypesForRegister() {
        try {
            const instanceTypeChoices = await fetchInstanceTypeChoices(this.state.softwareStackForRegister);
            this.setState({ instanceTypeChoicesForRegister: instanceTypeChoices }, () => {
                this.getRegisterSoftwareStackForm()?.getFormField("allowed_instance_types")?.setOptions({
                    listing: instanceTypeChoices,
                });
            });
        } catch (error: any) {
            this.getRegisterSoftwareStackForm()?.setError(error.errorCode || 'FETCH_ERROR', error.message || 'Failed to fetch instance types');
        }
    }

    async componentDidUpdate(prevProps: VirtualDesktopSoftwareStacksProps, prevState: VirtualDesktopSoftwareStacksState) {
        if (!this.state.showRegisterSoftwareStackForm) {
            return;
        }

        if (prevState.softwareStackForRegister === this.state.softwareStackForRegister) {
            return;
        }

        await handleInstanceTypeUpdate({
            prevStack: prevState.softwareStackForRegister,
            currStack: this.state.softwareStackForRegister,
            debounceTimer: this.state.debounceTimerForRegister,
            clearTimer: () => this.setState({ debounceTimerForRegister: null }),
            setTimer: (timer) => this.setState({ debounceTimerForRegister: timer }),
            clearError: () => this.getRegisterSoftwareStackForm()?.clearError(),
            updateInstanceTypes: () => this.updateInstanceTypesForRegister(),
            updateStack: (stack) => this.setState({ softwareStackForRegister: stack }),
        });
    }

    componentWillUnmount() {
        if (this.state.debounceTimerForRegister) {
            clearTimeout(this.state.debounceTimerForRegister);
        }
    }

    buildRegisterSoftwareStackForm() {
        return (
            <IdeaForm
                ref={this.registerSoftwareStackForm}
                name="register-software-stack"
                modal={true}
                title="Register new Software Stack"
                modalSize="medium"
                onSubmit={() => {
                    this.getRegisterSoftwareStackForm().clearError();
                    if (!this.getRegisterSoftwareStackForm().validate()) {
                        return;
                    }
                    const values = this.getRegisterSoftwareStackForm().getValues();
                    let projects: Project[] = [];
                    values.projects?.forEach((project_id: string) => {
                        projects.push({
                            project_id: project_id,
                        });
                    });

                    const softwareStack: VirtualDesktopSoftwareStack = {
                        ...this.state.softwareStackForRegister,
                        name: values.name,
                        description: values.description,
                        projects: projects,
                        placement: {
                            ...this.state.softwareStackForRegister.placement,
                            affinity: values.affinity,
                            host_id: (values.target_host_by === "host_id") ? values.host_id : undefined,
                            host_resource_group_arn: (values.target_host_by === "host_resource_group") ? values.host_resource_group_arn : undefined,
                        },
                        enabled: true,
                    } as VirtualDesktopSoftwareStack;

                    this.getVirtualDesktopAdminClient()
                        .createSoftwareStack({ software_stack: softwareStack })
                        .then((response) => {
                            this.hideRegisterSoftwareStackForm();
                            this.setFlashMessage(<p key={values.name}>Software Stack: {values.name}, Create request submitted</p>, "success");
                            this.getListing().fetchRecords();
                        })
                        .catch((error) => {
                        const errorMessage = error?.response?.data?.message || error?.message || 'Failed to create software stack';
                            this.getRegisterSoftwareStackForm().setError('CREATE_ERROR', errorMessage);
                        });
                }}
                onCancel={() => {
                    this.hideRegisterSoftwareStackForm();
                }}
                onStateChange={(event) => {
                    const paramName = event.param.name;
                    if (!paramName) return;

                    const values = this.getRegisterSoftwareStackForm().getValues();
                    const updatedStack = { ...this.state.softwareStackForRegister };
                    const fieldUpdaters = createFieldUpdaters(values, updatedStack);

                    if (fieldUpdaters[paramName]) {
                        fieldUpdaters[paramName]();
                        this.setState({ softwareStackForRegister: updatedStack });
                    }
                }}
                params={[
                    {
                        name: "name",
                        title: "Name",
                        description: "Enter a name for the software stack",
                        help_text: "Use any characters and form a name of length between 3 and 24 characters, inclusive.",
                        data_type: "str",
                        param_type: "text",
                        validate: {
                            required: true,
                            regex: "^.{3,24}$",
                            message: "Use any characters and form a name of length between 3 and 24 characters, inclusive.",
                        },
                    },
                    {
                        name: "description",
                        title: "Description",
                        description: "Enter a user friendly description for the software stack",
                        data_type: "str",
                        param_type: "text",
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
                        default: DEFAULT_SOFTWARE_STACK_BASE_OS,
                        choices: this.state.supportedOsChoices,
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
                        default: DEFAULT_SOFTWARE_STACK_GPU,
                        choices: this.state.supportedGPUChoices,
                    },
                    {
                        name: "root_storage_size",
                        title: "Min. Storage Size (GB)",
                        description: "Enter the min. storage size for your virtual desktop in GBs",
                        data_type: "int",
                        param_type: "text",
                        default: DEFAULT_SOFTWARE_STACK_MIN_STORAGE,
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
                        default: DEFAULT_SOFTWARE_STACK_MIN_RAM,
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
                        default: DEFAULT_SOFTWARE_STACK_TENANCY,
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
                        title: "Host Resource Group ARN",
                        description: "The ARN of the dedicated resource group",
                        help_text: "",
                        data_type: "str",
                        param_type: "text",
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
                        choices: this.state.instanceTypeChoicesForRegister,
                        default: this.state.softwareStackForRegister.allowed_instance_types || [],
                    },
                ]}
            />
        );
    }

    hideEditSoftwareStackForm() {
        this.setState({
            showEditSoftwareStackForm: false,
        });
    }

    setFlashMessage = (content: React.ReactNode, type: "success" | "info" | "error") => {
        this.props.onFlashbarChange({
            items: [
                {
                    content: content,
                    dismissible: true,
                    type: type,
                },
            ],
        });
    };

    async showEditSoftwareStackForm() {
        try {
            const instanceTypes = await Utils.getAllowedInstanceTypesOptionsForSelectedSoftwareStack(this.getSelectedSoftwareStack());
            this.setState(
                {
                    allowedInstanceTypes: instanceTypes,
                    showEditSoftwareStackForm: true,
                },
                () => {
                    this.getEditSoftwareStackForm().showModal();
                }
            );
        } catch (error) {
            console.error('Error showing edit form:', error);
        }
    }

    getEditSoftwareStackForm() {
        return this.editSoftwareStackForm.current!;
    }

    showDeleteSoftwareStackConfirmModal() {
        this.setState(
            {
                showDeleteStackConfirmModal: true,
            },
            () => {
                this.getDeleteSoftwareStackConfirmModal().show();
            }
        );
    }

    getDeleteSoftwareStackConfirmModal() {
        return this.deleteStackConfirmModal.current!;
    }

    buildEditSoftwareStackForm() {
        return (
            <VirtualDesktopSoftwareStackEditForm
                ref={this.editSoftwareStackForm}
                softwareStack={this.getSelectedSoftwareStack()!}
                allowedInstanceTypes={this.state.allowedInstanceTypes}
                supportedOsChoices={this.state.supportedOsChoices}
                supportedGPUChoices={this.state.supportedGPUChoices}
                onSubmit={(stack_id: string, base_os: VirtualDesktopBaseOs, name: string, description: string, ami_id: string, gpu: VirtualDesktopGpu, min_storage: ResMemory,
                    min_ram: ResMemory, projects: Project[], placement: VirtualDesktopPlacement, allowed_instance_types: string[]) => {
                        return this.getVirtualDesktopAdminClient()
                        .updateSoftwareStack(
                            stack_id,
                            {
                            software_stack: {

                                base_os: base_os,
                                name: name,
                                description: description,
                                ami_id: ami_id,
                                gpu: gpu,
                                min_storage: min_storage,
                                min_ram: min_ram,
                                projects: projects as any,
                                placement: placement,
                                allowed_instance_types: allowed_instance_types
                            },
                        })
                        .then((_) => {
                            this.setFlashMessage(<p key={stack_id}>Software Stack: {name}, Edit request submitted</p>, "success");
                            this.getEditSoftwareStackForm().hideForm();
                            return Promise.resolve(true);
                        })
                        .catch((error) => {
                            this.getEditSoftwareStackForm().setError(error.errorCode, error.message);
                            return Promise.resolve(false);
                        });
                }}
                onDismiss={() => {
                    this.hideEditSoftwareStackForm();
                    this.getListing().fetchRecords();
                }}
            />
        );
    }

    buildDeleteStackConfirmModal() {
        const selectedSoftwareStack = this.getSelectedSoftwareStack();
        const infoMsg =  "This stack is currently used by above live sessions. " +
            "Deleting this stack does not terminate any live sessions currently using the stack, " +
            "but you will not be able to launch new sessions with this stack.";
        return (
            <IdeaConfirm
                ref={this.deleteStackConfirmModal}
                title={"Delete Software Stack: " + selectedSoftwareStack?.name}
                onConfirm={() => {
                    if (!selectedSoftwareStack) return;

                    this.getVirtualDesktopAdminClient()
                        .deleteSoftwareStack(
                            selectedSoftwareStack.stack_id!,
                            {
                                base_os: selectedSoftwareStack.base_os!
                            }
                        )
                        .then((_) => {
                            this.setState(
                                {
                                    softwareStackSelected: false,
                                    selectedSoftwareStackSessionsList: []
                                },
                                () => {
                                    this.setFlashMessage(<p key={selectedSoftwareStack?.stack_id}>Software Stack: {selectedSoftwareStack?.name}, Delete Successfully</p>, "success");
                                    this.getListing().fetchRecords();
                                }
                            );
                        })
                        .catch((error) => {
                            this.setFlashMessage(error.message, "error");
                        });
                }}
                onCancel={() => {
                    this.setState({
                        showDeleteStackConfirmModal: false,
                        selectedSoftwareStackSessionsList: []
                    });
                }}
            >
            {
                this.state.selectedSoftwareStackSessionsList.length > 0 &&
                    <div>
                        <b>Current Live Sessions Using this Software Stack:</b>
                        {this.state.selectedSoftwareStackSessionsList.map((session, index) => (
                            <li key={index}>
                                {session.name} (Owner: {session.owner})
                            </li>
                        ))}
                    <p>{infoMsg}</p>
                    </div>
            }
            <p>Are you sure you want to delete this stack? This action cannot be undone.</p>
            </IdeaConfirm>
        );
    }

    getSelectedSoftwareStack(): VirtualDesktopSoftwareStack | undefined {
        if (this.getListing() == null) {
            return undefined;
        }
        return this.getListing().getSelectedItems()[0];
    }

    buildListing() {
        return (
            <IdeaListView
                ref={this.listing}
                title="Software Stacks"
                preferencesKey={"software-stack"}
                showPreferences={true}
                description="Manage your Virtual Desktop Software Stacks"
                selectionType="single"
                primaryAction={{
                    id: "register-software-stack",
                    text: "Register Software Stack",
                    onClick: () => {
                        this.showRegisterSoftwareStackForm();
                    },
                }}
                secondaryActionsDisabled={!this.isSelected()}
                secondaryActions={[
                    {
                        id: "edit-software-stack",
                        text: "Edit Stack",
                        disabled: !this.isSelected(),
                        onClick: () => {
                            this.showEditSoftwareStackForm();
                        }
                    },
                    {
                        id: "delete-software-stack",
                        text: "Delete Stack",
                        disabled: !this.isSelected(),
                        onClick: () => {
                            const softwareStack = this.getSelectedSoftwareStack();
                            this.getVirtualDesktopClient()
                            .listSessions({
                                stackId: softwareStack?.stack_id
                            })
                            .then((result) => {
                                this.setState(
                                    {
                                        selectedSoftwareStackSessionsList: result.listing!
                                    },
                                    () => {
                                        this.showDeleteSoftwareStackConfirmModal();
                                    }
                                )
                            })
                            .catch((error) => {
                                this.setFlashMessage(error.message, "error");
                            });
                        },
                    },
                ]}
                showPaginator={true}
                showFilters={true}
                filterType="select"
                selectFilters={[
                    {
                        name: "$all",
                    },
                    {
                        name: "base_os",
                        choices: [
                            {
                                title: "All Operating Systems",
                                value: "",
                            },
                            {
                                title: "Amazon Linux 2",
                                value: "amazonlinux2",
                            },
                            {
                                title: "Amazon Linux 2023",
                                value: "amzn2023",
                            },
                            {
                                title: "Windows",
                                value: "windows",
                            },
                            {
                                title: "RHEL 8",
                                value: "rhel8"
                            },
                            {
                                title: "RHEL 9",
                                value: "rhel9"
                            },
                            {
                                title: "Ubuntu 2204",
                                value: "ubuntu2204"
                            },
                            {
                                title: "Ubuntu 2404",
                                value: "ubuntu2404"
                            },
                            {
                                title: "Rocky 9",
                                value: "rocky9"
                            }
                        ],
                    },
                ]}
                onFilter={(filters) => {
                    return filters;
                }}
                onRefresh={() => {
                    this.setState(
                        {
                            softwareStackSelected: false,
                        },
                        () => {
                            this.getListing().fetchRecords();
                        }
                    );
                }}
                onSelectionChange={() => {
                    this.setState({
                        softwareStackSelected: true,
                    });
                }}
                onFetchRecords={async () => {
                    // Extract base_os filter from the filters array
                    const filters = this.getListing().getFilters();
                    const baseOsFilter = filters?.find(f => f.key === 'base_os');
                    const baseOs = baseOsFilter?.value || undefined;
                    const searchFilter = filters?.find(f => f.key === '$all');
                    const softwareStackName = searchFilter?.value || undefined;
                    try {
                        let allItems: VirtualDesktopSoftwareStack[] = [];
                        let nextToken: string | undefined;

                        do {
                            const data = await this.getVirtualDesktopClient().listSoftwareStacks({
                                baseOs: baseOs as any,
                                softwareStackName: softwareStackName as any,
                                nextToken: nextToken,
                            });
                            allItems.push(...(data.listing || []));
                            nextToken = data.nextToken;
                        } while (nextToken);

                        return { listing: allItems };
                    } catch (error) {
                        this.props.onFlashbarChange({
                            items: [
                                {
                                    content: error instanceof Error ? error.message : String(error),
                                    type: "error",
                                    dismissible: true,
                                },
                            ],
                        });
                        throw error;
                    }
                }}
                columnDefinitions={VIRTUAL_DESKTOP_SOFTWARE_STACKS_TABLE_COLUMN_DEFINITIONS}
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
                        text: "Virtual Desktops",
                        href: "#/virtual-desktop/sessions",
                    },
                    {
                        text: "Software Stacks (AMIs)",
                        href: "",
                    },
                ]}
                content={
                    <div>
                        {this.state.showRegisterSoftwareStackForm && this.buildRegisterSoftwareStackForm()}
                        {this.state.showEditSoftwareStackForm && this.buildEditSoftwareStackForm()}
                        {this.state.showDeleteStackConfirmModal && this.buildDeleteStackConfirmModal()}
                        {this.buildListing()}
                    </div>
                }
            />
        );
    }
}

export default withRouter(VirtualDesktopSoftwareStacks);
