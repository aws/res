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

import React, { Component } from "react";
import { Button, Container, Header, Link, SpaceBetween, Tabs } from "@cloudscape-design/components";
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import IdeaAppLayout, { IdeaAppLayoutProps } from "../../components/app-layout";
import { withRouter } from "../../navigation/navigation-utils";
import { ListSessionsResponse, VirtualDesktopSession } from '../../client/data-model'
import { AppContext } from "../../common";
import ResourcesTab from "./components/resources-tab";
import CostsTab from "./components/costs-tab"
import { fetchAllSessions } from "../../common/sessions-fetcher";

export interface CostDashboardProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {}

export interface CostDashboardState {
    activeTabId: string;
    alertVisible: boolean;
    sessions: VirtualDesktopSession[];
    loading: boolean
}

const DEFAULT_ACTIVE_TAB_ID = "costs";

class CostDashboard extends Component<CostDashboardProps, CostDashboardState> {
    constructor(props: CostDashboardProps) {
        super(props);
        this.state = {
            activeTabId: DEFAULT_ACTIVE_TAB_ID,
            alertVisible: true,
            sessions: [],
            loading: false
        };
    }

    buildCostsTab() {
        return (
            <SpaceBetween size="m">
                <Container header={<Header variant={"h3"}>Current budget and project status</Header>}>
                </Container>
                    <Container
                        header={
                            <Header
                                variant={"h3"}
                            >
                                Cost analysis over time
                            </Header>
                        }
                    >
                </Container>
            </SpaceBetween>
        )
    }

    async loadSessionsData() {
        this.setState({loading: true});
        try {
            const client = AppContext.get().client().virtualDesktopAdmin();
           
            const result = await fetchAllSessions(
                client,
                [], 
                undefined, 
                this.props.onFlashbarChange
            );
            
            this.setState({sessions: result.listing ?? [], loading: false});
        } catch (error: any) {
            this.setState({loading: false});
        }
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
                disableContentHeaderOverlap={true}
                breadcrumbItems={[
                    {
                        text: "RES",
                        href: "#/",
                    },
                    {
                        text: "Cost Dashboard",
                        href: "",
                    },
                ]}
                header={
                    <Header
                        variant={"h1"}
                        info={<Link
                                onFollow={() => {
                                    this.props.onToolsChange({open: true, pageId: 'cost-dashboard'});
                                }}
                                variant="primary"
                            >Info</Link>
                        }
                        actions={
                            this.state.activeTabId === "resources" &&
                            <SpaceBetween size={"xs"} direction={"horizontal"}>
                                <Button
                                    variant="normal"
                                    iconName="refresh"
                                    onClick={() => {
                                        this.loadSessionsData();
                                    }}
                                />
                                <Button
                                    variant={"primary"}
                                    onClick={() => {
                                        this.props.navigate("/virtual-desktop/sessions");
                                    }}
                                >
                                    View Sessions
                                </Button>
                            </SpaceBetween>
                        }
                    >
                        Dashboard
                    </Header>
                }
                content={
                    <React.Fragment>
                        <Tabs
                            activeTabId={this.state.activeTabId}
                            onChange={(event) => {
                                this.setState(
                                    {
                                        activeTabId: event.detail.activeTabId,
                                    }
                                );
                                if (event.detail.activeTabId === "resources") {
                                    this.loadSessionsData();
                                }
                            }}
                            tabs={[
                                {
                                    label: "Costs",
                                    id: "costs",
                                    content: (
                                        <CostsTab {...this.props} />
                                    ),
                                },
                                {
                                    label: "Resources",
                                    id: "resources",
                                    content: (
                                        <ResourcesTab sessions={this.state.sessions} loading={this.state.loading}/>
                                    ),
                                },
                            ]}
                        />
                    </React.Fragment>
                }
            />
        );
    }
}

export default withRouter(CostDashboard);
