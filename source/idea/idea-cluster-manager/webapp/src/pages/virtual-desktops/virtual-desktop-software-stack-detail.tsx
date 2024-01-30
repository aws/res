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
import { Button, ColumnLayout, Container, Grid, Header, SpaceBetween } from "@cloudscape-design/components";
import IdeaAppLayout from "../../components/app-layout/app-layout";
import { KeyValue } from "../../components/key-value";
import { AppContext } from "../../common";
import { Project, VirtualDesktopBaseOS, VirtualDesktopSoftwareStack } from "../../client/data-model";
import Tabs from "../../components/tabs/tabs";
import Utils from "../../common/utils";
import VirtualDesktopSoftwareStackEditForm from "./forms/virtual-desktop-software-stack-edit-form";
import { VirtualDesktopAdminClient } from "../../client";
import { withRouter } from "../../navigation/navigation-utils";

export interface VirtualDesktopSoftwareStackDetailProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {}

interface VirtualDesktopSoftwareStackDetailState {
    softwareStack: VirtualDesktopSoftwareStack;
    showEditSoftwareStackForm: boolean;
}

class VirtualDesktopSoftwareStackDetail extends Component<VirtualDesktopSoftwareStackDetailProps, VirtualDesktopSoftwareStackDetailState> {
    editStackForm: RefObject<VirtualDesktopSoftwareStackEditForm>;

    constructor(props: VirtualDesktopSoftwareStackDetailProps) {
        super(props);
        this.editStackForm = React.createRef();
        this.state = {
            softwareStack: {},
            showEditSoftwareStackForm: false,
        };
    }

    getSoftwareStackId(): string {
        return this.props.params.software_stack_id;
    }

    getSoftwareStackBaseOS(): string {
        return this.props.params.software_stack_base_os;
    }

    getVirtualDesktopAdminClient(): VirtualDesktopAdminClient {
        return AppContext.get().client().virtualDesktopAdmin();
    }

    componentDidMount() {
        AppContext.get()
            .client()
            .virtualDesktopAdmin()
            .getSoftwareStackInfo({
                stack_id: this.getSoftwareStackId(),
                base_os: this.getSoftwareStackBaseOS()
            })
            .then((result) => {
                this.setState({
                    softwareStack: result.software_stack!,
                });
            });
    }

    buildProjectsDetails() {
        return (
            <ul>
                {this.state.softwareStack.projects?.map((project) => {
                    return (
                        <li>
                            {project.title} | {project.name}
                        </li>
                    );
                })}
            </ul>
        );
    }

    buildHeaderActions() {
        return (
            <Button variant={"primary"} onClick={() => this.showEditSoftwareStackForm()}>
                {" "}
                Edit{" "}
            </Button>
        );
    }

    buildDetails() {
        return (
            <SpaceBetween size={"l"}>
                <Container header={<Header variant={"h2"}>General Information</Header>}>
                    <ColumnLayout variant={"text-grid"} columns={3}>
                        <KeyValue title="Name" value={this.state.softwareStack.name} />
                        <KeyValue title="AMI ID" value={this.state.softwareStack.ami_id} clipboard={true} />
                        <KeyValue title="Base OS" value={Utils.getOsTitle(this.state.softwareStack.base_os)} />
                    </ColumnLayout>
                </Container>
                <Tabs
                    tabs={[
                        {
                            label: "Details",
                            id: "details",
                            content: (
                                <Container header={<Header variant={"h2"}>Stack Details</Header>}>
                                    <Grid gridDefinition={[{ colspan: 8 }, { colspan: 4 }]}>
                                        <ColumnLayout columns={2} variant={"text-grid"}>
                                            <KeyValue title="Software Stack ID" value={this.state.softwareStack.stack_id} clipboard={true} />
                                            <KeyValue title="Minimum Storage Size" value={this.state.softwareStack.min_storage} type="memory" />
                                            <KeyValue title="Architecture" value={this.state.softwareStack.architecture} />
                                            <KeyValue title="GPU" value={this.state.softwareStack.gpu?.replaceAll("_", " ")} />
                                        </ColumnLayout>
                                        <KeyValue title={"Projects"} value={this.buildProjectsDetails()} type={"react-node"} />
                                    </Grid>
                                </Container>
                            ),
                        },
                    ]}
                />
            </SpaceBetween>
        );
    }

    hideEditSoftwareStackForm() {
        this.setState({
            showEditSoftwareStackForm: false,
        });
    }

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

    getEditSoftwareStackForm(): VirtualDesktopSoftwareStackEditForm {
        return this.editStackForm.current!;
    }

    buildEditForm() {
        return (
            <VirtualDesktopSoftwareStackEditForm
                ref={this.editStackForm}
                softwareStack={this.state.softwareStack}
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
                        .then((response) => {
                            this.setState({
                                softwareStack: response.software_stack!,
                            });
                            return Promise.resolve(true);
                        })
                        .catch((error) => {
                            this.getEditSoftwareStackForm().setError(error.errorCode, error.message);
                            return Promise.resolve(false);
                        });
                }}
                onDismiss={() => {
                    this.hideEditSoftwareStackForm();
                }}
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
                sideNavActivePath={"/virtual-desktop/software-stacks"}
                onFlashbarChange={this.props.onFlashbarChange}
                flashbarItems={this.props.flashbarItems}
                breadcrumbItems={[
                    {
                        text: "RES",
                        href: "#/",
                    },
                    {
                        text: "Virtual Desktop",
                        href: "#/virtual-desktop/software-stacks",
                    },
                    {
                        text: "Software Stacks",
                        href: "#/virtual-desktop/software-stacks",
                    },
                    {
                        text: this.getSoftwareStackId(),
                        href: "",
                    },
                ]}
                header={
                    <Header variant={"h1"} actions={this.buildHeaderActions()}>
                        Stack: {this.state.softwareStack.name}
                    </Header>
                }
                contentType={"default"}
                content={
                    <div>
                        {this.buildDetails()}
                        {this.state.showEditSoftwareStackForm && this.buildEditForm()}
                    </div>
                }
            />
        );
    }
}

export default withRouter(VirtualDesktopSoftwareStackDetail);
