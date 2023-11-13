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

import { ColumnLayout, Container, Header, Link, SpaceBetween, Tabs } from "@cloudscape-design/components";
import IdeaForm from "../../components/form";
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import IdeaAppLayout, { IdeaAppLayoutProps } from "../../components/app-layout";
import { KeyValue } from "../../components/key-value";
import { AppContext } from "../../common";
import dot from "dot-object";
import { EnabledDisabledStatusIndicator } from "../../components/common";
import { Constants } from "../../common/constants";
import Utils from "../../common/utils";
import { withRouter } from "../../navigation/navigation-utils";

export interface HpcSchedulerSettingsProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {}

export interface HpcSchedulerSettingsState {
    moduleInfo: any;
    settings: any;
    activeTabId: string;
}

class HpcSchedulerSettings extends Component<HpcSchedulerSettingsProps, HpcSchedulerSettingsState> {
    generalSettingsForm: RefObject<IdeaForm>;

    constructor(props: HpcSchedulerSettingsProps) {
        super(props);
        this.generalSettingsForm = React.createRef();
        this.state = {
            moduleInfo: {},
            settings: {},
            activeTabId: "general",
        };
    }

    componentDidMount() {
        AppContext.get()
            .getClusterSettingsService()
            .getSchedulerSettings()
            .then((settings) => {
                let moduleInfo = AppContext.get().getClusterSettingsService().getModuleInfo(Constants.MODULE_SCHEDULER);
                this.setState({
                    moduleInfo: moduleInfo,
                    settings: settings,
                });
            });
    }

    render() {
        const getSchedulerOpenAPISpecUrl = () => {
            return `${AppContext.get().getHttpEndpoint()}${Utils.getApiContextPath(Constants.MODULE_SCHEDULER)}/openapi.yml`;
        };

        const getSchedulerSwaggerEditorUrl = () => {
            return `https://editor.swagger.io/?url=${getSchedulerOpenAPISpecUrl()}`;
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
                        text: "Settings",
                        href: "",
                    },
                ]}
                header={
                    <Header variant={"h1"} description={"Manage Scale-Out Computing settings (Read-Only, use res-admin.sh to update SOCA settings.)"}>
                        Scale-Out Computing Settings
                    </Header>
                }
                contentType={"default"}
                content={
                    <SpaceBetween size={"l"}>
                        <Container>
                            <ColumnLayout variant={"text-grid"} columns={3}>
                                <KeyValue title="Module Name" value={dot.pick("name", this.state.moduleInfo)} />
                                <KeyValue title="Module ID" value={dot.pick("module_id", this.state.moduleInfo)} />
                                <KeyValue title="Version" value={dot.pick("version", this.state.moduleInfo)} />
                            </ColumnLayout>
                        </Container>
                        <Tabs
                            activeTabId={this.state.activeTabId}
                            onChange={(event) => {
                                this.setState({
                                    activeTabId: event.detail.activeTabId,
                                });
                            }}
                            tabs={[
                                {
                                    label: "General",
                                    id: "general",
                                    content: (
                                        <Container
                                            header={
                                                <Header
                                                    variant={"h2"}
                                                    info={
                                                        <Link external={true} href={"https://spec.openapis.org/oas/v3.1.0"}>
                                                            Info
                                                        </Link>
                                                    }
                                                >
                                                    OpenAPI Specification
                                                </Header>
                                            }
                                        >
                                            <ColumnLayout variant={"text-grid"} columns={1}>
                                                <KeyValue title="Scale-Out Computing on AWS API Spec" value={getSchedulerOpenAPISpecUrl()} type={"external-link"} clipboard />
                                                <KeyValue title="Swagger Editor" value={getSchedulerSwaggerEditorUrl()} type={"external-link"} clipboard />
                                            </ColumnLayout>
                                        </Container>
                                    ),
                                },
                                {
                                    label: "CloudWatch Logs",
                                    id: "cloudwatch-logs",
                                    content: (
                                        <Container header={<Header variant={"h2"}>CloudWatch Logs</Header>}>
                                            <ColumnLayout variant={"text-grid"} columns={3}>
                                                <KeyValue title="Status">
                                                    <EnabledDisabledStatusIndicator enabled={true} />
                                                </KeyValue>
                                                <KeyValue title="Force Flush Interval" value={5} suffix={"seconds"} />
                                                <KeyValue title="Log Retention" value={90} suffix={"days"} />
                                            </ColumnLayout>
                                        </Container>
                                    ),
                                },
                            ]}
                        />
                    </SpaceBetween>
                }
            />
        );
    }
}

export default withRouter(HpcSchedulerSettings);
