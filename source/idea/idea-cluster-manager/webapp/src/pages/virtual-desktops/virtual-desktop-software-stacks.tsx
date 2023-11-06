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
import { ProjectsClient, VirtualDesktopAdminClient } from "../../client";
import { AppContext } from "../../common";
import { TableProps } from "@cloudscape-design/components/table/interfaces";
import IdeaForm from "../../components/form";
import { Project, SocaUserInputChoice, VirtualDesktopBaseOS, VirtualDesktopSoftwareStack } from "../../client/data-model";
import Utils from "../../common/utils";
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import IdeaAppLayout, { IdeaAppLayoutProps } from "../../components/app-layout";
import { Link } from "@cloudscape-design/components";
import VirtualDesktopSoftwareStackEditForm from "./forms/virtual-desktop-software-stack-edit-form";
import { withRouter } from "../../navigation/navigation-utils";
import VirtualDesktopUtilsClient from "../../client/virtual-desktop-utils-client";

export interface VirtualDesktopSoftwareStacksProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {}

export interface VirtualDesktopSoftwareStacksState {
    softwareStackSelected: boolean;
    supportedOsChoices: SocaUserInputChoice[];
    supportedGPUChoices: SocaUserInputChoice[];
    projectChoices: SocaUserInputChoice[];
    showRegisterSoftwareStackForm: boolean;
    showEditSoftwareStackForm: boolean;
}

const VIRTUAL_DESKTOP_SOFTWARE_STACKS_TABLE_COLUMN_DEFINITIONS: TableProps.ColumnDefinition<VirtualDesktopSoftwareStack>[] = [
    {
        id: "name",
        header: "Name",
        cell: (e) => <Link href={`/#/virtual-desktop/software-stacks/${e.stack_id}`}>{e.name}</Link>,
    },
    {
        id: "description",
        header: "Description",
        cell: (e) => e.description,
    },
    {
        id: "ami_id",
        header: "AMI ID",
        cell: (e) => e.ami_id,
    },
    {
        id: "os",
        header: "Base OS",
        cell: (e) => Utils.getOsTitle(e.base_os),
    },
    {
        id: "root_volume_size",
        header: "Root Volume Size",
        cell: (e) => Utils.getFormattedMemory(e.min_storage),
    },
    {
        id: "min_ram",
        header: "Min RAM",
        cell: (e) => Utils.getFormattedMemory(e.min_ram),
    },
    {
        id: "gpu_manufacturer",
        header: "GPU Manufacturer",
        cell: (e) => Utils.getFormattedGPUManufacturer(e.gpu),
    },
    {
        id: "created_on",
        header: "Created On",
        cell: (e) => new Date(e.created_on!).toLocaleString(),
    },
];

class VirtualDesktopSoftwareStacks extends Component<VirtualDesktopSoftwareStacksProps, VirtualDesktopSoftwareStacksState> {
    listing: RefObject<IdeaListView>;
    registerSoftwareStackForm: RefObject<IdeaForm>;
    editSoftwareStackForm: RefObject<VirtualDesktopSoftwareStackEditForm>;

    constructor(props: VirtualDesktopSoftwareStacksProps) {
        super(props);
        this.listing = React.createRef();
        this.registerSoftwareStackForm = React.createRef();
        this.editSoftwareStackForm = React.createRef();
        this.state = {
            softwareStackSelected: false,
            supportedOsChoices: [],
            supportedGPUChoices: [],
            projectChoices: [],
            showRegisterSoftwareStackForm: false,
            showEditSoftwareStackForm: false,
        };
    }

    componentDidMount() {
        this.getVirtualDesktopUtilsClient()
            .listSupportedOS({})
            .then((result) => {
                this.setState({
                    supportedOsChoices: Utils.getSupportedOSChoices(result.listing!),
                });
            });

        this.getVirtualDesktopUtilsClient()
            .listSupportedGPUs({})
            .then((result) => {
                this.setState({
                    supportedGPUChoices: Utils.getSupportedGPUChoices(result.listing!),
                });
            });

        this.getProjectsClient()
            .getUserProjects({})
            .then((result) => {
                let projectChoices: SocaUserInputChoice[] = [];
                result.projects?.forEach((project) => {
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

    getVirtualDesktopUtilsClient(): VirtualDesktopUtilsClient {
        return AppContext.get().client().virtualDesktopUtils();
    }

    getRegisterSoftwareStackForm(): IdeaForm {
        return this.registerSoftwareStackForm.current!;
    }

    showRegisterSoftwareStackForm() {
        this.setState(
            {
                showRegisterSoftwareStackForm: true,
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
                    values.projects.forEach((project_id: string) => {
                        projects.push({
                            project_id: project_id,
                        });
                    });

                    this.getVirtualDesktopAdminClient()
                        .createSoftwareStack({
                            software_stack: {
                                name: values.name,
                                description: values.description,
                                ami_id: values.ami_id.toLowerCase().trim(),
                                base_os: values.base_os,
                                gpu: values.gpu,
                                min_storage: {
                                    value: values.root_storage_size,
                                    unit: "gb",
                                },
                                min_ram: {
                                    value: values.ram_size,
                                    unit: "gb",
                                },
                                projects: projects,
                            },
                        })
                        .then(() => {
                            this.hideRegisterSoftwareStackForm();
                            this.setFlashMessage(<p key={values.name}>Software Stack: {values.name}, Create request submitted</p>, "success");
                            this.getListing().fetchRecords();
                        })
                        .catch((error) => {
                            this.getRegisterSoftwareStackForm().setError(error.errorCode, error.message);
                        });
                }}
                onCancel={() => {
                    this.hideRegisterSoftwareStackForm();
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
                        title: "AMI ID",
                        description: "Enter the AMI ID",
                        help_text: "AMI ID must start with ami-xxx",
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
                        default: "amazonlinux2",
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
                        default: "NO_GPU",
                        choices: this.state.supportedGPUChoices,
                    },
                    {
                        name: "root_storage_size",
                        title: "Min. Storage Size (GB)",
                        description: "Enter the min. storage size for your virtual desktop in GBs",
                        data_type: "int",
                        param_type: "text",
                        default: 10,
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
                        default: 10,
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
                        validate: {
                            required: true,
                        },
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

    showEditSoftwareStackForm() {
        this.setState(
            {
                showEditSoftwareStackForm: true,
            },
            () => {
                this.getEditSoftwareStackForm().showModal();
            }
        );
    }

    getEditSoftwareStackForm() {
        return this.editSoftwareStackForm.current!;
    }

    buildEditSoftwareStackForm() {
        return (
            <VirtualDesktopSoftwareStackEditForm
                ref={this.editSoftwareStackForm}
                softwareStack={this.getSelectedSoftwareStack()!}
                onSubmit={(stack_id: string, base_os: VirtualDesktopBaseOS, name: string, description: string, projects: Project[]) => {
                    return this.getVirtualDesktopAdminClient()
                        .updateSoftwareStack({
                            software_stack: {
                                stack_id: stack_id,
                                base_os: base_os,
                                name: name,
                                description: description,
                                projects: projects,
                            },
                        })
                        .then((_) => {
                            this.setFlashMessage(<p key={stack_id}>Software Stack: {name}, Edit request submitted</p>, "success");
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
                            this.setState(
                                {
                                    showEditSoftwareStackForm: true,
                                },
                                () => {
                                    this.showEditSoftwareStackForm();
                                }
                            );
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
                                title: "Windows",
                                value: "windows",
                            },
                            {
                                title: "CentOS 7",
                                value: "centos7",
                            },
                            {
                                title: "RHEL 7",
                                value: "rhel7",
                            },
                            {
                                title: "RHEL 8",
                                value: "rhel8"
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
                onFetchRecords={() => {
                    return this.getVirtualDesktopAdminClient()
                        .listSoftwareStacks({
                            disabled_also: true,
                            filters: this.getListing().getFilters(),
                            paginator: this.getListing().getPaginator(),
                        })
                        .catch((error) => {
                            this.props.onFlashbarChange({
                                items: [
                                    {
                                        content: error.message,
                                        type: "error",
                                        dismissible: true,
                                    },
                                ],
                            });
                            throw error;
                        });
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
                        {this.buildListing()}
                    </div>
                }
            />
        );
    }
}

export default withRouter(VirtualDesktopSoftwareStacks);
