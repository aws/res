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
import { IdeaAppLayoutProps } from "../../components/app-layout";
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import { HpcLicenseResource } from "../../client/data-model";
import { SchedulerAdminClient } from "../../client";
import { AppContext } from "../../common";
import Utils from "../../common/utils";
import IdeaAppLayout from "../../components/app-layout/app-layout";
import { Alert, Box, Button, ColumnLayout, Container, ExpandableSection, Header, Link, SpaceBetween, Wizard } from "@cloudscape-design/components";
import IdeaForm from "../../components/form";
import { Constants } from "../../common/constants";
import { ClusterSettingsService } from "../../service";
import { KeyValue } from "../../components/key-value";
import dot from "dot-object";
import { CopyToClipBoard } from "../../components/common";
import { withRouter } from "../../navigation/navigation-utils";

export interface UpdateHpcLicenseProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {}

export interface UpdateHpcLicenseState {
    license: HpcLicenseResource;
    licenseResourceName?: string;
    activeStepIndex: number;
    errorMessage: string;
    showForm: boolean;
    schedulerInstanceId: string;
}

const OPENPBS_RESOURCE_DEF_FILE = "/var/spool/pbs/server_priv/resourcedef";
const OPENPBS_SCHED_CONFIG_FILE = "/var/spool/pbs/sched_priv/sched_config";

class UpdateHpcLicense extends Component<UpdateHpcLicenseProps, UpdateHpcLicenseState> {
    createForm: RefObject<IdeaForm>;

    constructor(props: UpdateHpcLicenseProps) {
        super(props);
        this.createForm = React.createRef();
        this.state = {
            license: {
                availability_check_cmd: this.getDefaultCheckAvailabilityScript(),
            },
            activeStepIndex: 0,
            showForm: false,
            errorMessage: "",
            schedulerInstanceId: "",
        };
    }

    isCreate = (): boolean => {
        return this.props.location.pathname.startsWith("/soca/licenses/create");
    };

    isUpdate = (): boolean => {
        return this.props.location.pathname.startsWith("/soca/licenses/update");
    };

    getPythonScriptPath = (): string => {
        return `${this.clusterSettings().getClusterHomeDir()}/${this.clusterSettings().getModuleId(Constants.MODULE_SCHEDULER)}/scripts/license_check.py`;
    };
    getDefaultCheckAvailabilityScript = (): string => {
        const script = `python ${this.getPythonScriptPath()}`;
        return `${script} --server SERVER --port PORT --feature FEATURE`;
    };

    schedulerAdmin(): SchedulerAdminClient {
        return AppContext.get().client().schedulerAdmin();
    }

    componentDidMount() {
        this.loadSchedulerInstanceId();
        if (this.isUpdate()) {
            const query = new URLSearchParams(this.props.location.search);
            const name = Utils.asString(query.get("name"));
            this.schedulerAdmin()
                .getHpcLicenseResource({
                    name: name,
                })
                .then((result) => {
                    this.setState({
                        license: result.license_resource!,
                        licenseResourceName: name,
                        showForm: true,
                    });
                });
        } else {
            this.setState({
                showForm: true,
            });
        }
    }

    isReady(): boolean {
        if (this.isCreate()) {
            return true;
        } else {
            return Utils.isNotEmpty(this.state.licenseResourceName);
        }
    }

    clusterSettings(): ClusterSettingsService {
        return AppContext.get().getClusterSettingsService();
    }

    loadSchedulerInstanceId() {
        AppContext.get()
            .getClusterSettingsService()
            .getModuleSettings(Constants.MODULE_SCHEDULER)
            .then((settings) => {
                this.setState({
                    schedulerInstanceId: dot.pick("instance_id", settings),
                });
            });
    }

    createOrUpdate(license: HpcLicenseResource, dryRun: boolean = false) {
        let createOrUpdate;
        if (this.isUpdate()) {
            createOrUpdate = (request: any) => this.schedulerAdmin().updateHpcLicenseResource(request);
        } else {
            createOrUpdate = (request: any) => this.schedulerAdmin().createHpcLicenseResource(request);
        }
        createOrUpdate({
            license_resource: license,
            dry_run: dryRun,
        })
            .then(() => {
                if (dryRun) {
                    this.setState({
                        activeStepIndex: 1,
                        license: license,
                        errorMessage: "",
                    });
                } else {
                    this.props.navigate("/soca/licenses");
                }
            })
            .catch((error) => {
                this.setState({
                    errorMessage: error.message,
                });
            });
    }

    render() {
        const getOpenPBSResourceDefText = () => {
            return `${this.state.license.name} type=long`;
        };
        const getOpenPBSServerDynResourceText = () => {
            return `server_dyn_res: "${this.state.license.name} !python ${this.state.license.availability_check_cmd}"`;
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
                sideNavActivePath={"/soca/licenses"}
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
                        text: "Licenses",
                        href: "#/soca/licenses",
                    },
                    {
                        text: this.isCreate() ? "Create License Resource" : "Update License Resource",
                        href: "#",
                    },
                ]}
                contentType={"wizard"}
                content={
                    <Wizard
                        activeStepIndex={this.state.activeStepIndex}
                        onNavigate={(event) => {
                            if (event.detail.requestedStepIndex === 0) {
                                this.setState({
                                    activeStepIndex: 0,
                                });
                            } else if (event.detail.requestedStepIndex === 1) {
                                if (!this.createForm.current!.validate()) {
                                    return;
                                }
                                let values = this.createForm.current!.getValues();
                                this.createOrUpdate(values, true);
                            }
                        }}
                        onSubmit={() => {
                            this.createOrUpdate(this.state.license, false);
                        }}
                        onCancel={() => {
                            this.props.navigate("/soca/licenses");
                        }}
                        steps={[
                            {
                                title: "Define License Resource",
                                errorText: this.state.errorMessage,
                                content: (
                                    <Container>
                                        <SpaceBetween size={"m"}>
                                            {this.state.showForm && (
                                                <IdeaForm
                                                    ref={this.createForm}
                                                    name={"license-resource"}
                                                    showActions={false}
                                                    values={this.state.license}
                                                    params={[
                                                        {
                                                            name: "title",
                                                            title: "Title",
                                                            description: "Enter a user friendly license resource title",
                                                            data_type: "str",
                                                            param_type: "text",
                                                            validate: {
                                                                required: true,
                                                            },
                                                        },
                                                        {
                                                            name: "name",
                                                            title: "Resource Name",
                                                            description: "Enter name for the license resource",
                                                            help_text: "Name cannot contain white spaces or special characters and must be of format: {app}_lic_{feature}",
                                                            data_type: "str",
                                                            param_type: "text",
                                                            readonly: this.isUpdate(),
                                                            validate: {
                                                                required: true,
                                                                regex: "^(^[a-z][a-z0-9]*)_lic_([a-z][a-z0-9]*)$",
                                                                message: "Should be in the format: {app}_lic_{feature} where {app} and {feature} only use numbers and lowercase alphabets"
                                                            },
                                                        },
                                                        {
                                                            name: "reserved_count",
                                                            title: "Reserved Licenses",
                                                            description: "Prevent HPC to consume all license by keeping a reserved pool for local usage",
                                                            data_type: "int",
                                                            param_type: "text",
                                                        },
                                                        {
                                                            name: "availability_check_cmd",
                                                            title: "Availability Check Script",
                                                            description: "The script to be executed to with applicable parameters to get the available license count",
                                                            data_type: "str",
                                                            param_type: "text",
                                                            validate: {
                                                                required: true,
                                                            },
                                                        },
                                                    ]}
                                                />
                                            )}
                                            <Alert onDismiss={() => false} dismissAriaLabel="Close alert" header="Info">
                                                <li>IDEA generates a template license check script when scheduler is deployed.</li>
                                                <li>
                                                    Ensure you have updated <b>{this.getPythonScriptPath()}</b> as per your environment and requirements after first time deployment.
                                                </li>
                                                <ExpandableSection header={"license_check.py Usage"}>
                                                    <code className="idea-code-block">
                                                        python {this.getPythonScriptPath()} --help <br />
                                                        usage: license_check.py [-h] -s [SERVER] -p [PORT] -f [FEATURE] <br />
                                                        <br />
                                                        optional arguments:
                                                        <br />
                                                        &nbsp;&nbsp;-h, --help show this help message and exit
                                                        <br />
                                                        &nbsp;&nbsp;-s [SERVER], --server [SERVER]
                                                        <br />
                                                        &nbsp;&nbsp;FlexLM hostname
                                                        <br />
                                                        &nbsp;&nbsp;-p [PORT], --port [PORT]
                                                        <br />
                                                        &nbsp;&nbsp;FlexLM Port
                                                        <br />
                                                        &nbsp;&nbsp;-f [FEATURE], --feature [FEATURE]
                                                        <br />
                                                        &nbsp;&nbsp;FlexLM Feature
                                                        <br />
                                                    </code>
                                                </ExpandableSection>
                                            </Alert>
                                        </SpaceBetween>
                                    </Container>
                                ),
                            },
                            {
                                title: "Update OpenPBS Configuration",
                                errorText: this.state.errorMessage,
                                content: (
                                    <SpaceBetween size={"l"}>
                                        <Alert>A few manual configuration steps are required to configure the license resource in OpenPBS. Review the License Resource definition and follow the steps outlined below.</Alert>
                                        <Container
                                            header={
                                                <Header
                                                    variant={"h3"}
                                                    actions={
                                                        <SpaceBetween size={"s"}>
                                                            <Button
                                                                variant={"normal"}
                                                                onClick={() => {
                                                                    this.setState({
                                                                        activeStepIndex: 0,
                                                                    });
                                                                }}
                                                            >
                                                                Edit
                                                            </Button>
                                                        </SpaceBetween>
                                                    }
                                                >
                                                    License Resource
                                                </Header>
                                            }
                                        >
                                            <ColumnLayout variant={"text-grid"} columns={2}>
                                                <KeyValue title="Title" value={this.state.license.title} />
                                                <KeyValue title="Resource Name" value={this.state.license.name} clipboard={true} />
                                                <KeyValue title="Availability Check Script" value={this.state.license.availability_check_cmd} clipboard={true} />
                                                <KeyValue title="Reserved Licenses" value={this.state.license.reserved_count} />
                                            </ColumnLayout>
                                        </Container>
                                        <Container header={<Header variant={"h3"}>SSH into Scheduler EC2 Instance</Header>}>
                                            <ColumnLayout columns={2}>
                                                <Box>
                                                    <h3>SSH via SSM</h3>
                                                    <p>
                                                        <Link external={true} href={Utils.getSessionManagerConnectionUrl(AppContext.get().getAwsRegion(), this.state.schedulerInstanceId)}>
                                                            Connect via SSM
                                                        </Link>
                                                    </p>
                                                </Box>
                                                <Box>
                                                    <h3>SSH via Bastion Host</h3>
                                                    <p>
                                                        <Link external={true} href={"#/home/ssh-access"}>
                                                            SSH Connection Details
                                                        </Link>
                                                    </p>
                                                </Box>
                                            </ColumnLayout>
                                        </Container>
                                        <Container header={<Header variant={"h3"}>Update resourcedef</Header>}>
                                            <Box variant={"h4"}>
                                                Edit:{" "}
                                                <b>
                                                    <code>{OPENPBS_RESOURCE_DEF_FILE}</code>
                                                </b>
                                                <CopyToClipBoard text={OPENPBS_RESOURCE_DEF_FILE} feedback={`${OPENPBS_RESOURCE_DEF_FILE} copied`} />
                                            </Box>
                                            <p>
                                                Resources created on this file will be visible by OpenPBS and will be usable at qsub time via the -l parameter. Add your new resource with <b>type=long</b>.
                                            </p>
                                            <p>
                                                <code>{getOpenPBSResourceDefText()}</code>
                                                <CopyToClipBoard text={getOpenPBSResourceDefText()} feedback={`${getOpenPBSResourceDefText()} copied`} />
                                            </p>

                                            <p>Save and Close</p>
                                        </Container>
                                        <Container header={<Header variant={"h3"}>Update sched_config</Header>}>
                                            <SpaceBetween size={"m"}>
                                                <Box variant={"h4"}>
                                                    Edit:{" "}
                                                    <b>
                                                        <code>{OPENPBS_SCHED_CONFIG_FILE}</code>
                                                    </b>
                                                    <CopyToClipBoard text={OPENPBS_SCHED_CONFIG_FILE} feedback={`${OPENPBS_SCHED_CONFIG_FILE} copied`} />
                                                </Box>
                                                <Box>
                                                    <p>
                                                        <b>Edit 1) </b>
                                                        Find the relevant section containing <b>resources</b>. This line tells OpenPBS to honors the requested resources and do not start a job unless all resources requirements have been met.
                                                    </p>
                                                    <p>
                                                        <u>Edit</u> the line as below:
                                                    </p>
                                                    <p>
                                                        <code>resources: "{this.state.license.name}, ncpus, mem, arch, host, vnode, aoe, eoe, compute_node"</code>
                                                        <CopyToClipBoard text={this.state.license.name!} feedback={`${this.state.license.name} copied`} />
                                                    </p>
                                                    <Alert onDismiss={() => false} dismissAriaLabel="Close alert" type={"warning"}>
                                                        If you have multiple license resources defined, ensure that you retain existing values in the resources section.
                                                    </Alert>
                                                </Box>
                                                <Box>
                                                    <p>
                                                        <b>Edit 2) </b>
                                                        Find the relevant section containing <b>server_dyn_res</b>. This line tells OpenPBS what script/command to run when it detects the resources.
                                                    </p>
                                                    <p>
                                                        <u>Add a new line</u> as below:
                                                    </p>
                                                    <p>
                                                        <code>{getOpenPBSServerDynResourceText()}</code>
                                                        <CopyToClipBoard text={getOpenPBSServerDynResourceText()} feedback={`${getOpenPBSServerDynResourceText()} copied`} />
                                                    </p>
                                                    <p>Save and Close</p>
                                                </Box>
                                            </SpaceBetween>
                                        </Container>
                                        <Container header={<Header variant={"h3"}>Restart OpenPBS Server</Header>}>
                                            Run the below command to, restart OpenPBS Server and apply the configuration changes and add new license resource.
                                            <p>
                                                <code>systemctl restart pbs</code>
                                                <CopyToClipBoard text={"systemctl restart pbs"} feedback={`systemctl restart pbs copied`} />
                                            </p>
                                            <Alert>
                                                <b>Pro Tip: </b> If you are adding multiple license resources, create all license resources before restarting pbs server.
                                            </Alert>
                                        </Container>
                                    </SpaceBetween>
                                ),
                            },
                        ]}
                        i18nStrings={{
                            stepNumberLabel: (stepNumber) => `Step ${stepNumber}`,
                            collapsedStepsLabel: (stepNumber, stepsCount) => `Step ${stepNumber} of ${stepsCount}`,
                            skipToButtonLabel: (step, _) => `Skip to ${step.title}`,
                            cancelButton: "Cancel",
                            previousButton: "Previous",
                            nextButton: "Next",
                            submitButton: this.isCreate() ? "Create License Resource" : "Update License Resource",
                            optional: "optional",
                        }}
                    />
                }
            />
        );
    }
}

export default withRouter(UpdateHpcLicense);
