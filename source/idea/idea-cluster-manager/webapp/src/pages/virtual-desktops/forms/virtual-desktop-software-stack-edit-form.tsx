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
import { Project, SocaUserInputChoice, VirtualDesktopBaseOS, VirtualDesktopSoftwareStack } from "../../../client/data-model";
import { ProjectsClient } from "../../../client";
import { AppContext } from "../../../common";

export interface VirtualDesktopSoftwareStackEditFormProps {
    softwareStack: VirtualDesktopSoftwareStack;
    onDismiss: () => void;
    onSubmit: (stack_id: string, base_os: VirtualDesktopBaseOS, name: string, description: string, projects: Project[]) => Promise<boolean>;
}

export interface VirtualDesktopSoftwareStackEditFormState {
    showModal: boolean;
    projectChoices: SocaUserInputChoice[];
}

class VirtualDesktopSoftwareStackEditForm extends Component<VirtualDesktopSoftwareStackEditFormProps, VirtualDesktopSoftwareStackEditFormState> {
    form: RefObject<IdeaForm>;

    constructor(props: VirtualDesktopSoftwareStackEditFormProps) {
        super(props);
        this.form = React.createRef();
        this.state = {
            showModal: false,
            projectChoices: [],
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

    componentDidMount() {
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
                        this.getForm()?.getFormField("projects")?.setOptions({
                            listing: this.state.projectChoices,
                        });
                    }
                );
            });
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

                        return this.props
                            .onSubmit(stack_id, base_os, name, description, projects)
                            .then((result) => {
                                this.hideForm();
                                return Promise.resolve(result);
                            })
                            .catch((error) => {
                                this.getForm().setError(error.errorCode, error.message);
                                return Promise.resolve(false);
                            });
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
                            name: "projects",
                            title: "Projects",
                            description: "Select applicable projects for the software stack",
                            data_type: "str",
                            param_type: "select",
                            multiple: true,
                            choices: this.state.projectChoices,
                            default: this.getCurrentProjectsChoices(),
                        },
                    ]}
                />
            )
        );
    }
}

export default VirtualDesktopSoftwareStackEditForm;
