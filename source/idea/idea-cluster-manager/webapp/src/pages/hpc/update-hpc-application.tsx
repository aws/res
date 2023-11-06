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

import React, { Component, ReactNode, RefObject } from "react";

import { HpcApplication, SocaUserInputParamMetadata } from "../../client/data-model";
import { SchedulerAdminClient } from "../../client";
import { AppContext } from "../../common";
import Utils from "../../common/utils";
import IdeaForm from "../../components/form";
import { Box, Button, CodeEditor, ColumnLayout, Container, FormField, Link, SpaceBetween, Wizard } from "@cloudscape-design/components";
import IdeaFormBuilder from "../../components/form-builder";
import { CodeEditorProps } from "@cloudscape-design/components/code-editor/interfaces";
import "ace-builds/css/ace.css";
import "ace-builds/css/theme/dawn.css";
import { IdeaFormField } from "../../components/form-field";
import imageCompression from "browser-image-compression";
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import IdeaAppLayout, { IdeaAppLayoutProps } from "../../components/app-layout";
import { withRouter } from "../../navigation/navigation-utils";

const SampleJobScriptSimple = require("./sample-job-script-simple.txt");
const SampleJobScriptJinja2 = require("./sample-job-script-jinja2.txt");
const SampleJobParams = require("./sample-job-params.json");

export interface UpdateHpcApplicationProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {}

export interface UpdateHpcApplicationState {
    application?: HpcApplication;
    isCreate: boolean;
    applicationId?: string;
    ace: any;
    preferences: any;
    language: CodeEditorProps.Language;
    jobScriptTemplate: string;
    scriptInterpreter: string;
    activeStep: number;
    thumbnailData?: string;
    toolsOpen: boolean;
    tools: React.ReactNode;
    updatedApplication: HpcApplication;
    project_ids: string[];
}

interface AvailableVariableProps {
    name: string;
    required: boolean;
    isReferenced: boolean;
    isDefined: boolean;
    description?: string;
}

function AvailableVariable(props: AvailableVariableProps) {
    const getStyle = () => {
        if (props.name === "cpus") {
            if (props.isDefined) {
                return {
                    color: "green",
                };
            } else {
                return {
                    color: "red",
                };
            }
        }
        if (props.isReferenced) {
            return {
                color: "green",
            };
        } else {
            return {
                color: "red",
            };
        }
    };
    const getText = (): string => {
        let s = "(";
        if (props.required) {
            s += "required";
        } else {
            s += "optional";
        }
        if (props.description) {
            s += ", " + props.description;
        }
        s += ")";
        return s;
    };
    return (
        <div>
            <code style={getStyle()}>{props.name}</code>&nbsp;&nbsp;
            <Box variant="span" color="text-body-secondary">
                {getText()}
            </Box>
        </div>
    );
}

class UpdateHpcApplication extends Component<UpdateHpcApplicationProps, UpdateHpcApplicationState> {
    formBuilder: RefObject<IdeaFormBuilder>;
    titleFormField: RefObject<IdeaFormField>;
    projectsFormField: RefObject<IdeaFormField>;
    jobScriptForm: RefObject<IdeaForm>;

    constructor(props: UpdateHpcApplicationProps) {
        super(props);
        this.formBuilder = React.createRef();
        this.titleFormField = React.createRef();
        this.projectsFormField = React.createRef();
        this.jobScriptForm = React.createRef();
        this.state = {
            application: {},
            isCreate: this.props.location.pathname.startsWith("/soca/applications/create"),
            applicationId: "",
            ace: undefined,
            preferences: undefined,
            jobScriptTemplate: "jinja2",
            language: "batchfile",
            scriptInterpreter: "pbs",
            activeStep: 0,
            toolsOpen: false,
            tools: null,
            updatedApplication: {},
            project_ids: [],
        };
    }

    componentDidMount() {
        if (this.isUpdate()) {
            const query = new URLSearchParams(this.props.location.search);
            const applicationId = Utils.asString(query.get("id"));
            this.schedulerAdmin()
                .getHpcApplication({
                    application_id: applicationId,
                })
                .then((result) => {
                    let project_ids: string[] = [];
                    result.application?.projects?.forEach((project) => {
                        project_ids.push(project.project_id!);
                    });
                    this.setState({
                        application: result.application,
                        applicationId: applicationId,
                        updatedApplication: { ...result.application },
                        jobScriptTemplate: result.application?.job_script_template ? result.application?.job_script_template : "",
                        thumbnailData: result.application?.thumbnail_data ? result.application?.thumbnail_data : "",
                        project_ids: project_ids,
                    });
                });
        } else {
            this.getDefaultJobScriptTemplate().then((script: string) => {
                this.setState({
                    jobScriptTemplate: script,
                });
            });
        }

        import("ace-builds").then((ace) => {
            import("ace-builds/webpack-resolver").then(() => {
                ace.config.set("useStrictCSP", true);
                ace.config.set("loadWorkerFromBlob", false);
                this.setState({
                    ace: ace,
                });
            });
        });
    }

    schedulerAdmin(): SchedulerAdminClient {
        return AppContext.get().client().schedulerAdmin();
    }

    getFormBuilder(): IdeaFormBuilder {
        return this.formBuilder.current!;
    }

    getJobScriptForm(): IdeaForm {
        return this.jobScriptForm.current!;
    }

    getTitleFormField(): IdeaFormField {
        return this.titleFormField.current!;
    }

    getProjectsFormField(): IdeaFormField {
        return this.projectsFormField.current!;
    }

    isCreate(): boolean {
        return this.state.isCreate;
    }

    isUpdate(): boolean {
        return !this.isCreate();
    }

    isReady(): boolean {
        if (this.isCreate()) {
            return true;
        } else {
            return Utils.isNotEmpty(this.state.applicationId);
        }
    }

    fetchSampleJobScript(): Promise<string> {
        if (this.state.updatedApplication.job_script_type === "default") {
            return fetch(SampleJobScriptSimple).then((response) => response.text());
        } else {
            return fetch(SampleJobScriptJinja2).then((response) => response.text());
        }
    }

    getDefaultJobScriptTemplate() {
        if (this.state.updatedApplication?.job_script_template) {
            return Promise.resolve(this.state.updatedApplication.job_script_template!);
        } else {
            return this.fetchSampleJobScript();
        }
    }

    onResetJobScript = () => {
        const application = this.getUpdatedApplication();
        if (application) {
            this.setState(
                {
                    updatedApplication: application,
                },
                () => {
                    this.fetchSampleJobScript().then((jobScript) => {
                        this.setState({
                            jobScriptTemplate: jobScript,
                        });
                    });
                }
            );
        }
    };

    getRecommendedJobParameters(): SocaUserInputParamMetadata[] {
        if (this.state.updatedApplication?.form_template && this.state.updatedApplication.form_template.sections) {
            const params: any[] = [];
            this.state.updatedApplication.form_template.sections.forEach((section) => {
                if (section.params) {
                    params.push(...section.params);
                }
                if (section.groups) {
                    section.groups.forEach((group) => {
                        if (group.params) {
                            params.push(...group.params);
                        }
                    });
                }
            });
            return params;
        } else {
            return JSON.parse(JSON.stringify(SampleJobParams));
        }
    }

    resizeImage(file: File): Promise<File> {
        return new Promise((resolve) => {
            imageCompression(file, {
                maxWidthOrHeight: 150,
            }).then((file) => {
                resolve(file);
            });
        });
    }

    updateTools = (content: ReactNode) => {
        this.setState({
            toolsOpen: true,
            tools: content,
        });
    };

    resetHelp = () => {
        this.setState({
            toolsOpen: false,
            tools: "",
        });
    };

    showHelp = (id: string) => {
        let content;
        if (id === "job-design-form") {
            content = (
                <SpaceBetween size="s" direction="vertical">
                    <Box padding={{ left: "l", right: "l" }}>
                        <h3>Reserved Variables</h3>
                        <p>You can use your own variable names, however some variables are pre-configured for you when you use the following variables:</p>

                        <li>
                            <i>job_name</i>: If present, will be automatically populated with the input file name
                        </li>
                        <li>
                            <i>input_name</i>: If present, will be automatically populated with the input file path
                        </li>
                        <li>
                            <i>instance_type</i>: Used to calculate the number of node to provision
                        </li>
                        <li>
                            <i>cpus</i>: Used to calculate the number of node(s) to provision
                        </li>
                        <li>
                            <i>scratch_size</i>: Used to estimate the cost of your simulation
                        </li>
                        <li>
                            <i>root_size</i>: Used to estimate the cost of your simulation
                        </li>
                        <li>
                            <i>fsx_size</i>: Used to estimate the cost of your simulation
                        </li>
                        <li>
                            <i>wall_time</i>: Used to estimate the cost of your simulation
                        </li>
                    </Box>
                    <Box padding={{ left: "l", right: "l" }}>
                        <h3>Calculate number of nodes to provision automatically</h3>
                        <p>
                            If <i>instance_type</i> and <i>cpus</i> parameters are specified, SOCA will automatically calculate the number of node(s) to provision. If not set, you will need to find a way to specify <i>nodes</i> resource.
                        </p>
                    </Box>
                    <Box padding={{ left: "l", right: "l" }}>
                        <h3>Calculate Job Cost Estimate Automatically</h3>
                        <p>Parameters below will be used to estimate the price of a simulation:</p>

                        <li>
                            <i>instance_type</i>: Used to calculate the number of node to provision
                        </li>
                        <li>
                            <i>cpus</i>: Used to calculate the number of node(s) to provision
                        </li>
                        <li>
                            <i>scratch_size</i>: Used to estimate the cost of your simulation
                        </li>
                        <li>
                            <i>root_size</i>: Used to estimate the cost of your simulation
                        </li>
                        <li>
                            <i>fsx_size</i>: Used to estimate the cost of your simulation
                        </li>
                        <li>
                            <i>wall_time</i>: Used to estimate the cost of your simulation
                        </li>
                    </Box>
                </SpaceBetween>
            );
        }
        if (content) {
            this.updateTools(content);
        }
    };

    getUpdatedApplication(): HpcApplication | null {
        const currentStep = this.state.activeStep;
        let application: HpcApplication | null = null;
        if (currentStep === 0) {
            const params = this.getFormBuilder().getFormParams();
            application = {
                ...this.state.updatedApplication,
                form_template: {
                    sections: [
                        {
                            params: params,
                        },
                    ],
                },
            };
        } else if (currentStep === 1) {
            if (!this.getJobScriptForm().validate()) {
                return null;
            }
            const values = this.getJobScriptForm().getValues();
            const jobScriptTemplate = this.state.jobScriptTemplate;
            application = {
                ...this.state.updatedApplication,
                job_script_template: jobScriptTemplate,
                job_script_interpreter: values.job_script_interpreter,
                job_script_type: values.job_script_type,
            };
        } else if (currentStep === 2) {
            let isValid = true;
            if (!this.getTitleFormField().triggerValidate()) {
                isValid = false;
            }
            if (!this.getProjectsFormField().triggerValidate()) {
                isValid = false;
            }
            if (!isValid) {
                return null;
            }
            const applicationTitle = this.getTitleFormField().getTypedValue();
            const applicationThumbnail = this.state.thumbnailData;
            let project_ids = this.getProjectsFormField().getValueAsStringArray();

            let projects: any = [];
            project_ids.forEach((project_id) => {
                projects.push({
                    project_id: project_id,
                });
            });

            application = {
                ...this.state.updatedApplication,
                title: applicationTitle,
                thumbnail_data: applicationThumbnail,
                projects: projects,
            };
        }
        return application;
    }

    isFormDesigned(): boolean {
        if (this.state.updatedApplication.form_template) {
            return true;
        }
        return false;
    }

    getDesignedFormVariables(): SocaUserInputParamMetadata[] {
        return this.state.updatedApplication.form_template?.sections![0].params!;
    }

    isVariableDefined(name: string): boolean {
        const params = this.getDesignedFormVariables();
        if (!params) {
            return false;
        }
        const found = params.find((param) => param.name === name);
        if (found) {
            return true;
        }
        return false;
    }

    onWizardNavigate = (stepIndex: number) => {
        this.resetHelp();
        const application = this.getUpdatedApplication();
        if (application) {
            this.setState({
                activeStep: stepIndex,
                updatedApplication: application,
            });
        }
    };

    onSubmit = () => {
        const application = this.getUpdatedApplication();
        let createOrUpdate;
        if (this.isCreate()) {
            createOrUpdate = (request: any) => this.schedulerAdmin().createHpcApplication(request);
        } else {
            createOrUpdate = (request: any) => this.schedulerAdmin().updateHpcApplication(request);
        }
        if (application) {
            createOrUpdate({
                application: application,
            })
                .then(() => {
                    this.props.navigate("/soca/applications");
                })
                .catch((error) => {
                    console.error(error);
                });
        }
    };

    render() {
        const isVariableReferencedInScript = (name: string) => {
            if (this.state.updatedApplication.job_script_type === "jinja2") {
                const matches = this.state.jobScriptTemplate.match(`{{.*(\\b${name}\\b).*}}`);
                if (matches == null || matches.length === 0) {
                    return false;
                }
                return matches[1] === name;
            } else {
                return this.state.jobScriptTemplate.search(`%${name}%`) >= 0;
            }
        };

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
                        text: "IDEA",
                        href: "#/",
                    },
                    {
                        text: "Scale-Out Computing",
                        href: "#/soca/active-jobs",
                    },
                    {
                        text: "Applications",
                        href: "#/soca/applications",
                    },
                    {
                        text: this.isCreate() ? "Create Application" : `Update Application${this.state.updatedApplication.title ? ": " + this.state.updatedApplication.title : ""}`,
                        href: "#",
                    },
                ]}
                contentType={"wizard"}
                content={
                    this.isReady() && (
                        <Wizard
                            i18nStrings={{
                                stepNumberLabel: (stepNumber) => `Step ${stepNumber}`,
                                collapsedStepsLabel: (stepNumber, stepsCount) => `Step ${stepNumber} of ${stepsCount}`,
                                skipToButtonLabel: (step, stepNumber) => `Skip to ${step.title}`,
                                cancelButton: "Cancel",
                                previousButton: "Previous",
                                nextButton: "Next",
                                submitButton: "Submit",
                                optional: "optional",
                            }}
                            onNavigate={(event) => {
                                this.onWizardNavigate(event.detail.requestedStepIndex);
                            }}
                            onSubmit={this.onSubmit}
                            onCancel={() => {
                                this.props.navigate("/soca/applications");
                            }}
                            activeStepIndex={this.state.activeStep}
                            steps={[
                                {
                                    title: "Design Job Submission Form",
                                    info: (
                                        <Link variant="info" onFollow={() => this.showHelp("job-design-form")}>
                                            Info
                                        </Link>
                                    ),
                                    content: (
                                        <IdeaFormBuilder
                                            ref={this.formBuilder}
                                            params={this.getRecommendedJobParameters()}
                                            infoSection={
                                                this.isCreate() && (
                                                    <div>
                                                        <p>
                                                            We have generated a test job submission form for you. You can customize it as needed or click <strong>Reset Form</strong> to start from scratch.
                                                        </p>
                                                    </div>
                                                )
                                            }
                                        />
                                    ),
                                },
                                {
                                    title: "Design the Job Script",
                                    content: (
                                        <Container variant="default">
                                            <SpaceBetween direction="vertical" size="xl">
                                                <IdeaForm
                                                    columns={2}
                                                    ref={this.jobScriptForm}
                                                    name="job-script-interpreter"
                                                    showHeader={false}
                                                    showActions={false}
                                                    onStateChange={(event) => {
                                                        if (event.param.name === "job_script_type") {
                                                            this.setState({
                                                                updatedApplication: {
                                                                    ...this.state.updatedApplication,
                                                                    job_script_type: event.value,
                                                                },
                                                            });
                                                        }
                                                    }}
                                                    values={{
                                                        job_script_interpreter: this.state.updatedApplication.job_script_interpreter,
                                                        job_script_type: this.state.updatedApplication.job_script_type,
                                                    }}
                                                    params={[
                                                        {
                                                            name: "job_script_interpreter",
                                                            title: "Script Interpreter",
                                                            description: "Select the interpreter you want to use",
                                                            data_type: "str",
                                                            param_type: "select",
                                                            default: "pbs",
                                                            choices: [
                                                                {
                                                                    title: "PBS Job Script",
                                                                    description: "This is a PBS job script (will use qsub)",
                                                                    value: "pbs",
                                                                },
                                                                {
                                                                    title: "Linux Shell Script",
                                                                    description: "This is a Linux shell script (will use /bin/bash)",
                                                                    value: "bash",
                                                                },
                                                            ],
                                                        },
                                                        {
                                                            name: "job_script_type",
                                                            title: "Script Template Type",
                                                            description: "Select the script template type",
                                                            data_type: "str",
                                                            param_type: "select",
                                                            default: "jinja2",
                                                            choices: [
                                                                {
                                                                    title: "Simple",
                                                                    description: "Simple replacement of %foo%",
                                                                    value: "default",
                                                                },
                                                                {
                                                                    title: "Advanced (Jinja2)",
                                                                    description: "Use Jinja2 template to write your job scripts",
                                                                    value: "jinja2",
                                                                },
                                                            ],
                                                        },
                                                    ]}
                                                />
                                                <FormField label="Available Variables" description="Below variables are available for use in your job script, based on the form designed in the previous step.">
                                                    <ul>
                                                        <li>
                                                            <AvailableVariable name="project_name" isReferenced={isVariableReferencedInScript("project_name")} isDefined={this.isVariableDefined("project_name")} required={true} description={"included automatically"} />
                                                        </li>
                                                        <li>
                                                            <AvailableVariable name="cpus" isReferenced={isVariableReferencedInScript("cpus")} required={true} isDefined={this.isVariableDefined("cpus")} description={"used for node count computation"} />
                                                        </li>
                                                        {this.isFormDesigned() &&
                                                            this.getDesignedFormVariables().map((param) => {
                                                                if (param.param_type!.startsWith("heading")) {
                                                                    return "";
                                                                }
                                                                if (param.name === "cpus") {
                                                                    return "";
                                                                }
                                                                if (param.name === "project_name") {
                                                                    return "";
                                                                }
                                                                if (!param.name) {
                                                                    return "";
                                                                }
                                                                return (
                                                                    <li key={param.name}>
                                                                        <AvailableVariable name={param.name} isReferenced={isVariableReferencedInScript(param.name)} isDefined={this.isVariableDefined(param.name)} required={Utils.isTrue(param.validate?.required)} />
                                                                    </li>
                                                                );
                                                            })}
                                                    </ul>
                                                </FormField>
                                                <FormField label="Job Script" description="Build the job script template based on your simulation requirements" stretch={true}>
                                                    <SpaceBetween size="xs" direction="vertical">
                                                        <CodeEditor
                                                            id="job-script-editor"
                                                            ace={this.state.ace}
                                                            language={this.state.language}
                                                            value={this.state.jobScriptTemplate}
                                                            preferences={this.state.preferences}
                                                            onPreferencesChange={(e) =>
                                                                this.setState({
                                                                    preferences: e.detail,
                                                                })
                                                            }
                                                            onChange={(e) => {
                                                                this.setState({
                                                                    jobScriptTemplate: e.detail.value,
                                                                });
                                                            }}
                                                            loading={false}
                                                            i18nStrings={{
                                                                loadingState: "Loading code editor",
                                                                errorState: "There was an error loading the code editor.",
                                                                errorStateRecovery: "Retry",
                                                                editorGroupAriaLabel: "Code editor",
                                                                statusBarGroupAriaLabel: "Status bar",
                                                                cursorPosition: (row, column) => `Ln ${row}, Col ${column}`,
                                                                errorsTab: "Errors",
                                                                warningsTab: "Warnings",
                                                                preferencesButtonAriaLabel: "Preferences",
                                                                paneCloseButtonAriaLabel: "Close",
                                                                preferencesModalHeader: "Preferences",
                                                                preferencesModalCancel: "Cancel",
                                                                preferencesModalConfirm: "Confirm",
                                                                preferencesModalWrapLines: "Wrap lines",
                                                                preferencesModalTheme: "Theme",
                                                                preferencesModalLightThemes: "Light themes",
                                                                preferencesModalDarkThemes: "Dark themes",
                                                            }}
                                                        />
                                                        <Button variant="normal" onClick={this.onResetJobScript}>
                                                            Reset Job Script
                                                        </Button>
                                                    </SpaceBetween>
                                                </FormField>
                                            </SpaceBetween>
                                        </Container>
                                    ),
                                },
                                {
                                    title: "Create Application Profile",
                                    content: (
                                        <ColumnLayout columns={2}>
                                            <Container variant="default">
                                                <SpaceBetween size="m" direction="vertical">
                                                    <IdeaFormField
                                                        ref={this.titleFormField}
                                                        module="submit-application-profile"
                                                        param={{
                                                            name: "title",
                                                            title: "Title",
                                                            description: "Enter a user friendly title for the application profile",
                                                            data_type: "str",
                                                            param_type: "text",
                                                            validate: {
                                                                required: true,
                                                            },
                                                            default: this.state.updatedApplication.title,
                                                        }}
                                                    />
                                                    <IdeaFormField
                                                        ref={this.projectsFormField}
                                                        module="submit-application-profile"
                                                        value={this.state.project_ids}
                                                        onFetchOptions={(event) => {
                                                            return AppContext.get()
                                                                .client()
                                                                .projects()
                                                                .listProjects({
                                                                    paginator: {
                                                                        page_size: 100,
                                                                    },
                                                                })
                                                                .then((result) => {
                                                                    let choices: any = [];
                                                                    result.listing?.forEach((project) => {
                                                                        choices.push({
                                                                            title: project.title,
                                                                            value: project.project_id,
                                                                            description: `Project Code: ${project.name}`,
                                                                        });
                                                                    });
                                                                    return {
                                                                        listing: choices,
                                                                    };
                                                                });
                                                        }}
                                                        param={{
                                                            name: "project_ids",
                                                            title: "Projects",
                                                            description: "Select applicable projects for the Queue Profile",
                                                            param_type: "select",
                                                            multiple: true,
                                                            data_type: "str",
                                                            validate: {
                                                                required: true,
                                                            },
                                                            dynamic_choices: true,
                                                        }}
                                                    />
                                                    <FormField label="Select Thumbnail" description="Select an image (.jpg or .png) to use as thumbnail">
                                                        <Box>
                                                            <input
                                                                type="file"
                                                                accept="image/png,image/jpeg"
                                                                onChange={(event) => {
                                                                    this.resizeImage(event.target.files![0])
                                                                        .then((file) => {
                                                                            let reader = new FileReader();
                                                                            reader.onload = () => {
                                                                                this.setState({
                                                                                    thumbnailData: `${reader.result}`,
                                                                                });
                                                                            };
                                                                            reader.readAsDataURL(file);
                                                                        })
                                                                        .catch((error) => console.error(error));
                                                                }}
                                                            />
                                                        </Box>
                                                        {this.state.thumbnailData && (
                                                            <Box padding="m">
                                                                <img width={80} src={this.state.thumbnailData} alt="thumbnail" />
                                                            </Box>
                                                        )}
                                                    </FormField>
                                                </SpaceBetween>
                                            </Container>
                                        </ColumnLayout>
                                    ),
                                },
                            ]}
                        />
                    )
                }
            />
        );
    }
}

export default withRouter(UpdateHpcApplication);
