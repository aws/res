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

import IdeaForm from "../../components/form";
import { Alert, Box, Button, ButtonDropdown, ColumnLayout, Container, ExpandableSection, Form, FormField, Grid, Header, Link, Modal, PieChart, Select, SelectProps, SpaceBetween, StatusIndicator, Table, Tabs, TextFilter, Tiles } from "@cloudscape-design/components";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faBug, faCheckCircle, faEdit, faPlay, faStar, faRefresh, faCircleMinus } from "@fortawesome/free-solid-svg-icons";
import { HpcApplication, JobValidationResultEntry, SocaInstanceTypeOptions, SocaJobEstimatedBOMCostLineItem, SocaUserInputParamMetadata, SubmitJobResult } from "../../client/data-model";
import { ProjectsClient, SchedulerClient } from "../../client";
import IdeaException from "../../common/exceptions";
import { AppContext } from "../../common";
import Utils from "../../common/utils";
import { TableProps } from "@cloudscape-design/components/table/interfaces";
import { KeyValue } from "../../components/key-value";
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import { JobTemplate } from "../../service/job-templates-service";
import IdeaAppLayout, { IdeaAppLayoutProps } from "../../components/app-layout";
import { withRouter } from "../../navigation/navigation-utils";

const nunjucks = require("nunjucks");

export interface SubmitJobProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {}

export interface SubmitJobState {
    splitPanelOpen: boolean;

    showApplicationSelectModal: boolean;
    applications: HpcApplication[];
    applicationFilterText: string;
    filteredApplications: HpcApplication[];
    selectedApplicationId: string | null;
    selectedProject: SelectProps.Option | null;
    projectOptions: SelectProps.Option[];

    showJobTemplatesModal: boolean;
    jobTemplates: JobTemplate[];
    jobTemplateFilterText: string;
    filteredJobTemplates: JobTemplate[];
    selectedJobTemplateId: string | null;

    showSaveJobTemplatesModal: boolean;

    jobSubmissionParameters: any;
    application?: HpcApplication;
    submitJobResult?: SubmitJobResult;
    jobScript?: string;
    activeTab: string;

    errorMessage: string;
    submitJobLoading: boolean;
    dryRunLoading: boolean;
}

const TAB_SUBMIT_JOB = "submit-job";
const TAB_COST_ESTIMATES = "cost-estimates";
const TAB_SERVICE_QUOTAS = "service-quotas";
const TAB_BUDGET_USAGE = "budget-usage";
const TAB_JOB_SCRIPT = "job-script";
const TAB_JOB_PARAMETERS = "job-parameters";

class SubmitJob extends Component<SubmitJobProps, SubmitJobState> {
    jobSubmissionForm: RefObject<IdeaForm>;
    saveJobTemplateForm: RefObject<IdeaForm>;

    constructor(props: SubmitJobProps) {
        super(props);
        this.jobSubmissionForm = React.createRef();
        this.saveJobTemplateForm = React.createRef();
        this.state = {
            splitPanelOpen: false,

            applications: [],
            applicationFilterText: "",
            filteredApplications: [],
            selectedApplicationId: null,
            selectedProject: null,
            projectOptions: [],

            jobSubmissionParameters: {},

            showJobTemplatesModal: false,
            jobTemplates: [],
            jobTemplateFilterText: "",
            filteredJobTemplates: [],
            selectedJobTemplateId: null,

            showSaveJobTemplatesModal: false,

            showApplicationSelectModal: false,
            activeTab: "submit-job",

            errorMessage: "",
            submitJobLoading: false,
            dryRunLoading: false,
        };
        nunjucks.configure({
            autoescape: false,
        });
    }

    getSchedulerClient(): SchedulerClient {
        return AppContext.get().client().scheduler();
    }

    getProjectsClient(): ProjectsClient {
        return AppContext.get().client().projects();
    }

    getJobSubmissionForm(): IdeaForm {
        return this.jobSubmissionForm.current!;
    }

    getSaveJobTemplateForm(): IdeaForm {
        return this.saveJobTemplateForm.current!;
    }

    componentDidMount() {
        this.initialize();
    }

    loadApplication(application: HpcApplication) {
        let projectOptions: any = [];
        application.projects?.forEach((project) => {
            projectOptions.push({
                label: project.title,
                description: `Project Code: ${project.name}`,
                value: project.name,
            });
        });
        this.setState({
            application: {
                ...application,
            },
            selectedApplicationId: null,
            showApplicationSelectModal: false,
            projectOptions: projectOptions,
            selectedProject: projectOptions[0],
        });
    }

    initialize(stateBase64?: string | null) {
        const queryParams = new URLSearchParams(this.props.location.search);
        if (stateBase64 == null) {
            stateBase64 = queryParams.get("state");
        } else {
            this.updateUrlState(stateBase64);
        }

        let state: any = null;
        if (stateBase64) {
            state = JSON.parse(atob(stateBase64));
        }

        if (state && state.applicationId) {
            this.getSchedulerClient()
                .getUserApplications({
                    application_ids: [state.applicationId],
                })
                .then((result) => {
                    if (result.applications?.length > 0) {
                        this.loadApplication(result.applications[0]);
                    }
                });
        }

        let jobSubmissionParameters: any = null;
        if (state && state.params) {
            jobSubmissionParameters = state.params;
        }

        const inputFile = queryParams.get("input_file");
        if (inputFile) {
            jobSubmissionParameters = {
                ...jobSubmissionParameters,
                input_file: inputFile,
                job_name: inputFile.substring(inputFile.lastIndexOf("/") + 1, inputFile.length).replaceAll(`.`, "_"),
            };
        }

        this.setState({
            jobSubmissionParameters: jobSubmissionParameters,
        });
    }

    buildUrlState = () => {
        const state = {
            project: this.state.selectedProject?.value,
            applicationId: this.state.application?.application_id,
            params: this.state.jobSubmissionParameters,
        };
        return btoa(JSON.stringify(state));
    };

    updateUrlState = (stateBase64?: string) => {
        if (stateBase64) {
            this.props.searchParams.set("state", stateBase64);
        } else {
            this.props.searchParams.set("state", this.buildUrlState());
        }
        this.props.setSearchParams(this.props.searchParams);
    };

    resetForm() {
        this.setState(
            {
                application: undefined,
                submitJobResult: undefined,
            },
            () => {
                this.props.searchParams.set("state", "");
            }
        );
    }

    buildApplicationSelectModal() {
        const onCancel = () => {
            this.setState({
                selectedApplicationId: null,
                showApplicationSelectModal: false,
            });
        };
        return (
            <Modal
                visible={this.state.showApplicationSelectModal}
                size="large"
                onDismiss={onCancel}
                header="Select an Application to Submit your Job"
                footer={
                    <Box float="right">
                        <SpaceBetween size="xs" direction="horizontal">
                            <Button variant="normal" onClick={onCancel}>
                                Cancel
                            </Button>
                            <Button
                                variant="primary"
                                disabled={this.state.selectedApplicationId == null}
                                onClick={() => {
                                    this.state.applications.forEach((application) => {
                                        if (application.application_id === this.state.selectedApplicationId) {
                                            this.loadApplication(application);
                                        }
                                    });
                                }}
                            >
                                Select
                            </Button>
                        </SpaceBetween>
                    </Box>
                }
            >
                <div style={{ height: "60vh", overflow: "auto" }}>
                    <SpaceBetween size="m" direction="vertical">
                        <TextFilter
                            filteringText={this.state.applicationFilterText}
                            filteringPlaceholder="Search available applications"
                            onChange={(event) => {
                                this.setState({
                                    applicationFilterText: event.detail.filteringText,
                                });
                            }}
                            onDelayedChange={(event) => {
                                const filteringText = event.detail.filteringText.trim().toLowerCase();
                                let filteredApplications: HpcApplication[] = [];
                                if (Utils.isEmpty(filteringText)) {
                                    filteredApplications = [...this.state.applications];
                                } else {
                                    this.state.applications.forEach((application) => {
                                        if (application.title) {
                                            if (application.title.trim().toLowerCase().includes(filteringText)) {
                                                filteredApplications.push(application);
                                            }
                                        }
                                    });
                                }
                                this.setState({
                                    filteredApplications: filteredApplications,
                                });
                            }}
                        />
                        <Tiles
                            value={this.state.selectedApplicationId}
                            onChange={(event) =>
                                this.setState({
                                    selectedApplicationId: event.detail.value,
                                })
                            }
                            columns={4}
                            items={this.state.filteredApplications.map((application) => {
                                return {
                                    label: application.title!,
                                    value: application.application_id!,
                                    image: this.getApplicationImage(application),
                                };
                            })}
                        />
                    </SpaceBetween>
                </div>
            </Modal>
        );
    }

    loadAllJobTemplates(): Promise<boolean> {
        return new Promise((resolve, reject) => {
            AppContext.get()
                .jobTemplates()
                .listJobTemplates()
                .then((jobTemplates) => {
                    this.setState(
                        {
                            jobTemplates: [...jobTemplates],
                            filteredJobTemplates: [...jobTemplates],
                        },
                        () => {
                            resolve(true);
                        }
                    );
                })
                .catch((error) => {
                    reject(false);
                });
        });
    }

    showJobTemplatesSelectionModal() {
        this.loadAllJobTemplates().then(() => {
            this.setState({
                showJobTemplatesModal: true,
            });
        });
    }

    showSaveJobTemplateForm() {
        this.loadAllJobTemplates().then(() => {
            this.setState(
                {
                    showSaveJobTemplatesModal: true,
                },
                () => {
                    this.getSaveJobTemplateForm().showModal();
                }
            );
        });
    }

    buildSaveJobTemplateForm() {
        const getJobTemplateChoices = () => {
            return this.state.jobTemplates.map((template) => {
                return {
                    title: template.title,
                    description: template.description,
                    value: template.id!,
                };
            });
        };
        const onCancel = () => {
            this.setState({
                showSaveJobTemplatesModal: false,
            });
        };
        return (
            <IdeaForm
                ref={this.saveJobTemplateForm}
                name="save-job-template"
                modal={true}
                modalSize="medium"
                title="Save Job Template"
                description="You can create a new job template or update an existing one"
                onCancel={onCancel}
                onStateChange={(event) => {
                    if (event.param.name === "job_template_id") {
                        const found = this.state.jobTemplates.find((jobTemplate) => jobTemplate.id === event.value);
                        if (found) {
                            this.getSaveJobTemplateForm().setParamValue("title", found.title);
                            this.getSaveJobTemplateForm().setParamValue("description", found.description);
                        }
                    }
                }}
                onSubmit={() => {
                    if (!this.getSaveJobTemplateForm().validate()) {
                        return;
                    }

                    const values = this.getSaveJobTemplateForm().getValues();
                    if (values.create_new) {
                        AppContext.get()
                            .jobTemplates()
                            .createJobTemplate({
                                title: values.title,
                                description: values.description,
                                template_data: this.buildUrlState(),
                            })
                            .finally(onCancel);
                    } else {
                        AppContext.get()
                            .jobTemplates()
                            .updateJobTemplate({
                                id: values.job_template_id,
                                title: values.title,
                                description: values.description,
                                template_data: this.buildUrlState(),
                            })
                            .finally(onCancel);
                    }
                }}
                params={[
                    {
                        name: "create_new",
                        title: "Create new Job Template?",
                        description: "Check to create a new one, or no to select an existing job template",
                        data_type: "bool",
                        param_type: "confirm",
                        default: true,
                    },
                    {
                        title: "Job Template",
                        name: "job_template_id",
                        description: "Select an existing job template",
                        param_type: "select",
                        data_type: "str",
                        choices: getJobTemplateChoices(),
                        validate: {
                            required: true,
                        },
                        when: {
                            param: "create_new",
                            eq: false,
                        },
                    },
                    {
                        title: "Title",
                        name: "title",
                        description: "Enter a title for your job template",
                        param_type: "text",
                        data_type: "str",
                        validate: {
                            required: true,
                        },
                    },
                    {
                        title: "Description",
                        name: "description",
                        description: "Enter a description for your job template",
                        param_type: "text",
                        data_type: "str",
                        multiline: true,
                        validate: {
                            required: true,
                        },
                    },
                ]}
            />
        );
    }

    buildJobTemplatesSelectionModal() {
        const onCancel = () => {
            this.setState({
                selectedJobTemplateId: null,
                showJobTemplatesModal: false,
            });
        };
        const onDeleteJobTemplate = () => {
            AppContext.get()
                .jobTemplates()
                .deleteJobTemplate(this.state.selectedJobTemplateId!)
                .then(() => {
                    this.loadAllJobTemplates().finally(() => {
                        this.setState({
                            selectedJobTemplateId: null,
                        });
                    });
                })
                .finally();
        };
        const onLoadJobTemplate = () => {
            AppContext.get()
                .jobTemplates()
                .getJobTemplate(this.state.selectedJobTemplateId!)
                .then((jobTemplate) => {
                    this.setState(
                        {
                            selectedJobTemplateId: null,
                            showJobTemplatesModal: false,
                            errorMessage: "",
                        },
                        () => {
                            this.initialize(jobTemplate.template_data);
                        }
                    );
                });
        };
        return (
            <Modal
                visible={this.state.showJobTemplatesModal}
                size="large"
                onDismiss={onCancel}
                header="Select a saved Job Template"
                footer={
                    <div>
                        <Box float="left">
                            <SpaceBetween size="xs" direction="horizontal">
                                <Button variant="normal" disabled={this.state.selectedJobTemplateId == null} onClick={onDeleteJobTemplate}>
                                    Delete
                                </Button>
                            </SpaceBetween>
                        </Box>
                        <Box float="right">
                            <SpaceBetween size="xs" direction="horizontal">
                                <Button variant="normal" onClick={onCancel}>
                                    Cancel
                                </Button>
                                <Button variant="primary" disabled={this.state.selectedJobTemplateId == null} onClick={onLoadJobTemplate}>
                                    Load Job Template
                                </Button>
                            </SpaceBetween>
                        </Box>
                    </div>
                }
            >
                <div style={{ height: "60vh", overflow: "auto" }}>
                    <SpaceBetween size="m" direction="vertical">
                        <TextFilter
                            filteringText={this.state.jobTemplateFilterText}
                            filteringPlaceholder="Search Job Templates"
                            onChange={(event) => {
                                this.setState({
                                    jobTemplateFilterText: event.detail.filteringText,
                                });
                            }}
                            onDelayedChange={(event) => {
                                const filteringText = event.detail.filteringText.trim().toLowerCase();
                                let filteredJobTemplates: JobTemplate[] = [];
                                if (Utils.isEmpty(filteringText)) {
                                    filteredJobTemplates = [...this.state.jobTemplates];
                                } else {
                                    this.state.jobTemplates.forEach((jobTemplate) => {
                                        if (jobTemplate.title) {
                                            if (jobTemplate.title.trim().toLowerCase().includes(filteringText)) {
                                                filteredJobTemplates.push(jobTemplate);
                                            }
                                        }
                                    });
                                }
                                this.setState({
                                    filteredJobTemplates: filteredJobTemplates,
                                });
                            }}
                        />
                        <Tiles
                            value={this.state.selectedJobTemplateId}
                            onChange={(event) =>
                                this.setState({
                                    selectedJobTemplateId: event.detail.value,
                                })
                            }
                            columns={3}
                            items={this.state.filteredJobTemplates.map((jobTemplate) => {
                                return {
                                    label: (
                                        <div>
                                            <strong>{jobTemplate.title!}</strong>
                                            <br />
                                            <span>{jobTemplate.description}</span>
                                        </div>
                                    ),
                                    value: jobTemplate.id!,
                                };
                            })}
                        />
                    </SpaceBetween>
                </div>
            </Modal>
        );
    }

    getJobSubmissionFormTemplateParams(): SocaUserInputParamMetadata[] {
        if (this.state.application && this.state.application.form_template) {
            if (this.state.application.form_template.sections && this.state.application.form_template.sections.length > 0) {
                return this.state.application.form_template.sections[0].params!;
            }
        }
        return [];
    }

    hasFormTemplate = () => {
        if (!this.state.application) {
            return false;
        }
        if (!this.state.application.form_template) {
            return false;
        }
        if (!this.state.application.form_template.sections) {
            return false;
        }
        if (this.state.application.form_template.sections.length === 0) {
            return false;
        }
        if (!this.state.application.form_template.sections[0].params) {
            return false;
        }
        if (this.state.application.form_template.sections[0].params.length === 0) {
            return false;
        }
        return true;
    };

    getApplicationImage(application: HpcApplication) {
        if (application.thumbnail_data) {
            return <img width={60} src={application.thumbnail_data} alt={application.title} />;
        } else if (application.thumbnail_url) {
            return <img width={60} src={application.thumbnail_url} alt={application.title} />;
        } else {
            return <div className="application-placeholder-image">No Image</div>;
        }
    }

    buildApplicationCard(application: HpcApplication) {
        return (
            <div style={{ display: "flex", flexDirection: "row", alignItems: "center" }}>
                {this.getApplicationImage(application)}
                &nbsp;&nbsp;
                <span style={{ display: "inline-block", paddingRight: "10px" }}>{application.title}</span>
            </div>
        );
    }

    buildSubmitJobForm() {
        const getProjectErrorText = () => {
            if (this.state.selectedProject) {
                return "";
            }
            return "Project is required to submit the job";
        };

        return (
            <div>
                <Form header={<h3>Fill the below form to submit your job.</h3>}>
                    <SpaceBetween size="l" direction="vertical">
                        <FormField label="Application" description="Select an application to submit the job">
                            <SpaceBetween size="m" direction="horizontal">
                                {this.state.application && <div className={"hpc-application-card"}>{this.buildApplicationCard(this.state.application)}</div>}
                                <Button
                                    variant="normal"
                                    onClick={() => {
                                        this.getSchedulerClient()
                                            .getUserApplications({})
                                            .then((result) => {
                                                const listing: HpcApplication[] = result.applications ? result.applications : [];
                                                this.setState({
                                                    applications: [...listing],
                                                    filteredApplications: [...listing],
                                                    showApplicationSelectModal: true,
                                                });
                                            });
                                    }}
                                >
                                    <FontAwesomeIcon icon={faEdit} />
                                </Button>
                            </SpaceBetween>
                        </FormField>
                        {this.state.application && (
                            <FormField label="Project" description="Select a project to tag AWS resources for the Job" errorText={getProjectErrorText()}>
                                <Select
                                    selectedOption={this.state.selectedProject}
                                    options={this.state.projectOptions}
                                    onChange={(event) => {
                                        this.setState({
                                            selectedProject: event.detail.selectedOption,
                                        });
                                    }}
                                />
                            </FormField>
                        )}
                        {this.hasFormTemplate() && <IdeaForm ref={this.jobSubmissionForm} name="job-submission-form" columns={1} showHeader={false} showActions={false} values={this.state.jobSubmissionParameters} params={this.getJobSubmissionFormTemplateParams()} />}
                    </SpaceBetween>
                </Form>
            </div>
        );
    }

    onDryRun = () => {
        this.setState({
            errorMessage: "",
            dryRunLoading: true,
        });
        this.submitJob(true).then(
            () => {
                this.setState({
                    activeTab: "submit-job",
                    dryRunLoading: false,
                });
            },
            (error) => {
                this.setState({
                    errorMessage: error.message,
                    activeTab: "submit-job",
                    dryRunLoading: false,
                });
            }
        );
    };

    onSubmitJob = () => {
        this.setState(
            {
                errorMessage: "",
                submitJobLoading: true,
            },
            () => {
                this.submitJob(false).then(
                    () => {
                        this.setState({
                            activeTab: "submit-job",
                            submitJobLoading: false,
                        });
                    },
                    (error) => {
                        this.setState({
                            errorMessage: error.message,
                            activeTab: "submit-job",
                            submitJobLoading: false,
                        });
                    }
                );
            }
        );
    };

    buildEmptyTabMessage = () => {
        return (
            <Alert type="info" header={"Job Submission or Dry Run Results"}>
                <Box variant="div">
                    <li>
                        Click <strong>Dry Run</strong> to validate job parameters, compute cost estimations and applicable service quotas.
                    </li>
                    <li>
                        Click <strong>Submit Job</strong> to submit your simulation job.
                    </li>
                </Box>
            </Alert>
        );
    };

    buildCostEstimates() {
        const getColumnDefinitions = (): TableProps.ColumnDefinition<SocaJobEstimatedBOMCostLineItem>[] => {
            return [
                {
                    id: "title",
                    header: "Item",
                    cell: (item) => item.title,
                },
                {
                    id: "qty",
                    header: "Qty",
                    cell: (item) => (item.quantity ? item.quantity.toFixed(2) : 0.0),
                },
                {
                    id: "unit",
                    header: "Unit",
                    cell: (item) => item.unit,
                },
                {
                    id: "unit-price",
                    header: "Unit Price",
                    cell: (item) => Utils.getFormattedAmount(item.unit_price),
                },
                {
                    id: "total-price",
                    header: "Total Price",
                    cell: (item) => Utils.getFormattedAmount(item.total_price),
                },
            ];
        };

        if (this.state.submitJobResult && this.state.submitJobResult.estimated_bom_cost) {
            const estimated_bom_cost = this.state.submitJobResult.estimated_bom_cost;
            return (
                <ColumnLayout columns={1}>
                    <Table items={estimated_bom_cost.line_items ? estimated_bom_cost.line_items! : []} columnDefinitions={getColumnDefinitions()} />

                    {estimated_bom_cost.savings && estimated_bom_cost.savings.length > 0 && (
                        <div>
                            <h4>Potential Savings: {Utils.getFormattedAmount(estimated_bom_cost.savings_total)}</h4>
                            <Table items={estimated_bom_cost.savings} columnDefinitions={getColumnDefinitions()} />
                        </div>
                    )}

                    <ColumnLayout columns={2}>
                        <Box textAlign="left">
                            <h3>Estimated Total Cost Per Hour</h3>
                        </Box>
                        <Box textAlign="right">
                            <h3>{Utils.getFormattedAmount(estimated_bom_cost?.total)}</h3>
                        </Box>
                    </ColumnLayout>

                    <ExpandableSection header="Disclaimer: Baseline numbers">
                        <p>These numbers are just an estimate.</p>
                        <ul>
                            <li>Does not reflect any additional charges such as network or storage transfer, usage of io1 volume (default to gp3)</li>
                            <li>Compute rate is retrieved for your running region</li>
                            <li>FSx Persistent Baseline: (50 MB/s/TiB baseline, up to 1.3 GB/s/TiB burst)</li>
                            <li>FSx Scratch Baseline: (200 MB/s/TiB baseline, up to 1.3 GB/s/TiB burst)</li>
                            <li>EBS/FSx rates as of May 2020 based on us-east-1</li>
                        </ul>
                    </ExpandableSection>
                </ColumnLayout>
            );
        } else {
            return this.buildEmptyTabMessage();
        }
    }

    buildServiceQuotas() {
        if (this.state.submitJobResult?.service_quotas) {
            return (
                <ColumnLayout columns={1}>
                    <Table
                        items={this.state.submitJobResult.service_quotas}
                        columnDefinitions={[
                            {
                                id: "name",
                                header: "Quota Name",
                                cell: (q) => q.quota_name,
                            },
                            {
                                id: "available",
                                header: "Available",
                                cell: (q) => q.available,
                            },
                            {
                                id: "consumed",
                                header: "Consumed",
                                cell: (q) => q.consumed,
                            },
                            {
                                id: "desired",
                                header: "Desired",
                                cell: (q) => q.desired,
                            },
                        ]}
                    />
                </ColumnLayout>
            );
        } else {
            return this.buildEmptyTabMessage();
        }
    }

    buildBudgetUsage() {
        const hasBudget = () => {
            return typeof this.state.submitJobResult?.budget_usage !== "undefined";
        };

        if (this.isSubmitted()) {
            if (hasBudget()) {
                const budget = this.state.submitJobResult?.budget_usage!;
                return (
                    <ColumnLayout columns={2}>
                        <div>
                            <KeyValue title="Budget Name" value={budget.budget_name} />
                            <KeyValue title="Budget Limit" value={budget.budget_limit} type="amount" />
                            <KeyValue title="Actual Spend" value={budget.actual_spend} type="amount" />
                            <KeyValue title="Forecasted Spend" value={budget.forecasted_spend} type="amount" />
                        </div>
                        <div>
                            <PieChart
                                hideFilter={true}
                                data={[
                                    {
                                        title: "Budget Limit",
                                        value: 60,
                                        lastUpdate: "Dec 7, 2020",
                                    },
                                    {
                                        title: "Failed",
                                        value: 30,
                                        lastUpdate: "Dec 6, 2020",
                                    },
                                    {
                                        title: "In-progress",
                                        value: 10,
                                        lastUpdate: "Dec 6, 2020",
                                    },
                                    {
                                        title: "Pending",
                                        value: 0,
                                        lastUpdate: "Dec 7, 2020",
                                    },
                                ]}
                            />
                        </div>
                    </ColumnLayout>
                );
            } else {
                return (
                    <Box color="text-body-secondary">
                        Budgets are not enabled for project: <strong>{this.state.selectedProject?.label}</strong>
                    </Box>
                );
            }
        }
    }

    isSubmitted = () => {
        return typeof this.state.submitJobResult?.job !== "undefined";
    };

    hasSubmissionErrors = () => {
        return Utils.isNotEmpty(this.state.errorMessage);
    };

    isDryRun = () => {
        return this.isSubmitted() && Utils.asBoolean(this.state.submitJobResult?.dry_run);
    };

    hasValidationErrors = () => {
        return this.state.submitJobResult?.validations && this.state.submitJobResult.validations.results && this.state.submitJobResult.validations.results?.length > 0;
    };

    hasIncidentalErrors = () => {
        return this.state.submitJobResult?.incidentals && this.state.submitJobResult.incidentals.results && this.state.submitJobResult.incidentals.results?.length > 0;
    };

    showTab = (tabId: string) => {
        this.setState({
            activeTab: tabId,
        });
    };

    buildSubmitJobResults() {
        const buildPostSubmissionLinks = () => {
            return (
                <ul>
                    <li>
                        <Link onFollow={() => this.showTab(TAB_COST_ESTIMATES)}>Show Cost Estimates</Link>
                    </li>
                    <li>
                        <Link onFollow={() => this.showTab(TAB_SERVICE_QUOTAS)}>Show Service Quota Usage</Link>
                    </li>
                    {/*<li><Link onFollow={() => this.showTab(TAB_BUDGET_USAGE)}>Show Budget Usage</Link></li>*/}
                    <li>
                        <Link onFollow={() => this.showTab(TAB_JOB_SCRIPT)}>Show Job Script</Link>
                    </li>
                    <li>
                        <Link onFollow={() => this.showTab(TAB_JOB_PARAMETERS)}>Show Job Parameters</Link>
                    </li>
                </ul>
            );
        };

        if (this.isSubmitted()) {
            if (this.hasValidationErrors() || this.hasIncidentalErrors()) {
                const errors: JobValidationResultEntry[] = [];
                if (this.hasValidationErrors()) {
                    this.state.submitJobResult?.validations?.results?.forEach((result) => {
                        errors.push(result);
                    });
                }
                if (this.hasIncidentalErrors()) {
                    this.state.submitJobResult?.incidentals?.results?.forEach((result) => {
                        errors.push(result);
                    });
                }
                return (
                    <ColumnLayout columns={1}>
                        {this.isDryRun() && (
                            <div>
                                <Box variant="h3" color="text-status-error">
                                    Dry Run Failed
                                </Box>
                                <p>
                                    <StatusIndicator type="error">Job cannot be submitted with this configuration due to below errors.</StatusIndicator>
                                </p>
                            </div>
                        )}
                        {!this.isDryRun() && (
                            <div>
                                <Box variant="h3" color="text-status-error">
                                    Job Submission Failed
                                </Box>
                                <p>
                                    <StatusIndicator type="error">Job submission failed with errors</StatusIndicator>
                                </p>
                            </div>
                        )}
                        <Table
                            items={errors}
                            columnDefinitions={[
                                {
                                    id: "error-code",
                                    header: "Error Code",
                                    cell: (e) => e.error_code,
                                },
                                {
                                    id: "error-code",
                                    header: "Description",
                                    cell: (e) => <pre>{e.message}</pre>,
                                },
                            ]}
                        />
                    </ColumnLayout>
                );
            } else {
                if (this.isDryRun()) {
                    return (
                        <ColumnLayout columns={1}>
                            <h3>Dry Run Results</h3>
                            <StatusIndicator type="success">Job can be submitted successfully</StatusIndicator>
                            {buildPostSubmissionLinks()}
                        </ColumnLayout>
                    );
                } else {
                    return (
                        <ColumnLayout columns={1}>
                            <Box variant="h3" color="text-status-success">
                                <FontAwesomeIcon icon={faCheckCircle} /> Job Submitted Successfully
                            </Box>
                            <SpaceBetween size="m" direction="horizontal">
                                <Button
                                    variant="normal"
                                    onClick={() => {
                                        this.resetForm();
                                    }}
                                >
                                    Reset Form and Submit Another Job
                                </Button>
                                <Button
                                    variant="primary"
                                    onClick={() => {
                                        this.props.navigate("/home/active-jobs");
                                    }}
                                >
                                    Show Active Jobs
                                </Button>
                            </SpaceBetween>
                            {buildPostSubmissionLinks()}
                        </ColumnLayout>
                    );
                }
            }
        } else if (this.hasSubmissionErrors()) {
            return (
                <div>
                    <Box variant="h3" color="text-status-error">
                        <FontAwesomeIcon icon={faCircleMinus} /> Job Submission Failed
                    </Box>
                    <p>{this.state.errorMessage}</p>
                </div>
            );
        } else {
            return this.buildEmptyTabMessage();
        }
    }

    buildJobActions() {
        const canSubmitJob = () => {
            if (Utils.isEmpty(this.state.application?.application_id)) {
                return false;
            }
            if (Utils.isEmpty(this.state.selectedProject?.value)) {
                return false;
            }
            return true;
        };
        return (
            <SpaceBetween size="xs" direction="horizontal">
                <Button variant="normal" disabled={!canSubmitJob()} onClick={() => this.resetForm()}>
                    <FontAwesomeIcon icon={faRefresh} /> Reset Form
                </Button>
                <ButtonDropdown
                    onItemClick={(event) => {
                        if (event.detail.id === "load") {
                            this.showJobTemplatesSelectionModal();
                        } else if (event.detail.id === "save") {
                            this.showSaveJobTemplateForm();
                        }
                    }}
                    items={[
                        {
                            id: "save",
                            text: "Save Job Template",
                            disabled: !canSubmitJob(),
                            disabledReason: "Select an application before saving job template",
                        },
                        {
                            id: "load",
                            text: "Load Job Template",
                        },
                    ]}
                >
                    <FontAwesomeIcon icon={faStar} /> Job Templates
                </ButtonDropdown>
                <Button variant="normal" disabled={!canSubmitJob()} loading={this.state.dryRunLoading} onClick={this.onDryRun}>
                    <FontAwesomeIcon icon={faBug} /> Dry Run
                </Button>
                <Button variant="primary" disabled={!canSubmitJob()} loading={this.state.submitJobLoading} onClick={this.onSubmitJob}>
                    <FontAwesomeIcon icon={faPlay} /> Submit Job
                </Button>
            </SpaceBetween>
        );
    }

    getJobSubmissionParameters(): any {
        const form = this.getJobSubmissionForm();
        if (!form) {
            return;
        }
        if (!form.validate()) {
            return;
        }
        if (!this.state.selectedProject) {
            return;
        }
        const values = form.getValues();
        return {
            ...values,
            project_name: this.state.selectedProject.value,
        };
    }

    getInstanceTypeCpuCount(instanceTypeOptions: SocaInstanceTypeOptions[]): number {
        const instanceTypes = this.getSelectedInstanceTypes();
        if (Utils.isEmpty(instanceTypes)) {
            return 0;
        }
        const instanceType = instanceTypes[0];
        let cpuCount = 0;
        instanceTypeOptions.forEach((instanceTypeOption) => {
            if (instanceType === instanceTypeOption.name) {
                cpuCount = Utils.asNumber(instanceTypeOption.threads_per_core, 0) * Utils.asNumber(instanceTypeOption.default_core_count, 0);
            }
        });
        return cpuCount;
    }

    getSelectedProjectName(): string | null {
        if (!this.state.selectedProject) {
            return null;
        }
        if (Utils.isEmpty(this.state.selectedProject.value)) {
            return null;
        }
        return this.state.selectedProject.value!;
    }

    getSelectedQueue(): string | null {
        const values = this.getJobSubmissionParameters();
        if (!values) {
            return null;
        }
        if (Utils.isNotEmpty(values.queue_name)) {
            return values.queue_name;
        }
        if (Utils.isNotEmpty(values.queue)) {
            return values.queue;
        }
        return null;
    }

    getSelectedInstanceTypes(): string[] {
        const values = this.getJobSubmissionParameters();
        if (!values) {
            return [];
        }
        if (!values.instance_type) {
            return [];
        }
        return values.instance_type.split("+");
    }

    isHyperThreadingEnabled(): boolean | undefined {
        const values = this.getJobSubmissionParameters();
        if (!values) {
            return;
        }
        if ("ht_support" in values) {
            return Utils.asBoolean(values["ht_support"], false);
        }
        if ("enable_ht_support" in values) {
            return Utils.asBoolean(values["enable_ht_support"], false);
        }
    }

    generateJobScript(): Promise<string> {
        const queueName = this.getSelectedQueue();
        const projectName = this.getSelectedProjectName();
        if (Utils.areAllEmpty(queueName, projectName)) {
            return Promise.reject(
                new IdeaException({
                    errorCode: "INVALID_PARAMS",
                    message: "queue or project are required to generate the job script.",
                })
            );
        }
        return this.getSchedulerClient()
            .getInstanceTypeOptions({
                enable_ht_support: this.isHyperThreadingEnabled(),
                instance_types: this.getSelectedInstanceTypes(),
                queue_name: queueName ? queueName : undefined,
            })
            .then((result) => {
                if (!this.state.application?.job_script_template) {
                    throw new IdeaException({
                        errorCode: "JOB_SCRIPT_NOT_FOUND",
                        message: "Application configuration is not valid. Job script template not found.",
                    });
                }
                const params = this.getJobSubmissionFormTemplateParams();
                const values = this.getJobSubmissionParameters();
                if (!values) {
                    throw new IdeaException({
                        errorCode: "INVALID_PARAMS",
                        message: "Job parameters validation failed.",
                    });
                }

                this.setState({
                    jobSubmissionParameters: values,
                });

                // begin select statement computation
                let cpusPerInstance = this.getInstanceTypeCpuCount(result.instance_types!);
                let nodeCount = Math.ceil(Utils.asNumber(values.cpus) / cpusPerInstance) | 0;
                if (nodeCount === 0) {
                    throw new IdeaException({
                        errorCode: "INVALID_PARAMS",
                        message: `Node computation failed. Nodes Count = ${nodeCount}`,
                    });
                }

                let jobScript = this.state.application.job_script_template!;
                const lines = jobScript.split("\n");
                const updatedLines = [];
                let shebangIndex = -1;
                let selectUpdated = false;
                const select = `#PBS -l select=${nodeCount}:ncpus=${cpusPerInstance}`;
                for (let i = 0; i < lines.length; i++) {
                    let line = lines[i];

                    if (line.trim().startsWith("#!")) {
                        shebangIndex = i;
                    } else if (line.trim().startsWith("#PBS -l select=")) {
                        line = select;
                        selectUpdated = true;
                    }

                    updatedLines.push(line);
                }

                if (!selectUpdated) {
                    if (shebangIndex >= 0) {
                        updatedLines.splice(shebangIndex + 1, 0, select, "# Added by IDEA Web Portal");
                    } else {
                        updatedLines.splice(0, 0, select, "# Added by IDEA Web Portal");
                    }
                }

                jobScript = updatedLines.join("\n");

                // begin parameter replacement
                if (this.state.application?.job_script_type && this.state.application?.job_script_type === "jinja2") {
                    return nunjucks.renderString(jobScript, values);
                } else {
                    jobScript = jobScript.replaceAll(`%project_name%`, values.project_name);
                    params.forEach((param) => {
                        if (param.name && Utils.isNotEmpty(param.name)) {
                            let value = "";
                            if (param.name in values) {
                                value = values[param.name];
                                if (Utils.isEmpty(value)) {
                                    value = "";
                                }
                            }
                            jobScript = jobScript.replaceAll(`%${param.name}%`, value);
                        }
                    });
                }

                return jobScript;
            });
    }

    submitJob(dryRun: boolean = false) {
        return new Promise((resolve, reject) => {
            this.generateJobScript()
                .then((jobScript) => {
                    if (Utils.isEmpty(jobScript)) {
                        reject(
                            new IdeaException({
                                errorCode: "SUBMIT_JOB_FAILED",
                                message: "Failed to generate job submission script",
                            })
                        );
                    }
                    this.updateUrlState();
                    this.setState(
                        {
                            jobScript: jobScript,
                        },
                        () => {
                            this.getSchedulerClient()
                                .submitJob({
                                    project: this.state.selectedProject?.value,
                                    dry_run: dryRun,
                                    job_script_interpreter: this.state.application?.job_script_interpreter,
                                    job_script: btoa(jobScript),
                                })
                                .then((result) => {
                                    this.setState(
                                        {
                                            submitJobResult: result,
                                        },
                                        () => {
                                            resolve({});
                                        }
                                    );
                                })
                                .catch((error) => {
                                    reject(error);
                                });
                        }
                    );
                })
                .catch((error) => {
                    reject(error);
                });
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
                        text: "IDEA",
                        href: "#/",
                    },
                    {
                        text: "Home",
                        href: "#/",
                    },
                    {
                        text: "Submit Job",
                        href: "",
                    },
                ]}
                header={
                    <Header variant={"h1"} actions={this.buildJobActions()}>
                        Submit Job
                    </Header>
                }
                contentType={"form"}
                content={
                    <div>
                        {this.buildApplicationSelectModal()}
                        {this.buildJobTemplatesSelectionModal()}
                        {this.state.showSaveJobTemplatesModal && this.buildSaveJobTemplateForm()}
                        <Container className={"hpc-submit-job"}>
                            <Tabs
                                activeTabId={this.state.activeTab}
                                onChange={(event) =>
                                    this.setState({
                                        activeTab: event.detail.activeTabId,
                                    })
                                }
                                tabs={[
                                    {
                                        id: TAB_SUBMIT_JOB,
                                        label: "Submit Job Form",
                                        content: (
                                            <SpaceBetween size="m" direction="vertical">
                                                <Grid gridDefinition={[{ colspan: { s: 6, xxs: 12 } }, { colspan: { s: 6, xxs: 12 } }]}>
                                                    {this.buildSubmitJobForm()}
                                                    {this.buildSubmitJobResults()}
                                                </Grid>
                                            </SpaceBetween>
                                        ),
                                    },
                                    {
                                        id: TAB_COST_ESTIMATES,
                                        disabled: !this.isSubmitted(),
                                        label: "Cost Estimates",
                                        content: this.buildCostEstimates(),
                                    },
                                    {
                                        id: TAB_SERVICE_QUOTAS,
                                        disabled: !this.isSubmitted(),
                                        label: "AWS Service Quotas",
                                        content: this.buildServiceQuotas(),
                                    },
                                    // {
                                    //     id: TAB_BUDGET_USAGE,
                                    //     disabled: !this.isSubmitted(),
                                    //     label: 'Budget Usage',
                                    //     content: this.buildBudgetUsage()
                                    // },
                                    {
                                        id: TAB_JOB_SCRIPT,
                                        disabled: !this.isSubmitted(),
                                        label: "Job Script",
                                        content: (
                                            <div className={"job-script"}>
                                                <Box variant="code">
                                                    <pre style={{ padding: "8px" }}>{this.state.jobScript}</pre>
                                                </Box>
                                            </div>
                                        ),
                                    },
                                    {
                                        id: TAB_JOB_PARAMETERS,
                                        disabled: !this.isSubmitted(),
                                        label: "Job Parameters",
                                        content: (
                                            <div className={"job-parameters"}>
                                                <Box variant="code">
                                                    <pre style={{ padding: "8px" }}>{this.state.submitJobResult && JSON.stringify(this.state.submitJobResult.job, null, 4)}</pre>
                                                </Box>
                                            </div>
                                        ),
                                    },
                                ]}
                            />
                        </Container>
                    </div>
                }
            />
        );
    }
}

export default withRouter(SubmitJob);
