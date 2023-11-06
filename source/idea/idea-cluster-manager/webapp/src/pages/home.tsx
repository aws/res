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

import { ColumnLayout, Header, Box, Link, Grid, Container, SpaceBetween, Icon } from "@cloudscape-design/components";

import "../styles/home.scss";
import { IdeaSideNavigationProps } from "../components/side-navigation";
import { OnToolsChangeEvent } from "../App";
import IdeaAppLayout, { IdeaAppLayoutProps } from "../components/app-layout";
import { withRouter } from "../navigation/navigation-utils";

export interface CounterProps {
    content?: string;
}

export const externalLinkProps = {
    external: true,
    externalIconAriaLabel: "Opens in a new tab",
};

export function Counter(props: CounterProps) {
    return (
        <Box variant="div" fontSize="display-l" fontWeight="normal">
            {props.content}
        </Box>
    );
}

export interface HomePageProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {
    toolsOpen: boolean;
    tools: React.ReactNode;
    onToolsChange: (event: OnToolsChangeEvent) => void;
}

export interface HomePageState {
    selectedOption: string;
}

class Home extends Component<HomePageProps, HomePageState> {
    constructor(props: HomePageProps) {
        super(props);
        this.state = {
            selectedOption: "",
        };
    }

    content() {
        return (
            <Grid
                gridDefinition={[
                    { colspan: { xl: 6, l: 5, s: 6, xxs: 10 }, offset: { l: 2, xxs: 1 } },
                    { colspan: { xl: 2, l: 3, s: 4, xxs: 10 }, offset: { s: 0, xxs: 1 } },
                ]}
            >
                <SpaceBetween size="l">
                    <Container>
                        <SpaceBetween size="l">
                            <Box variant="h1" tagOverride="h2">
                                Features and Benefits
                            </Box>
                            <ColumnLayout columns={2} variant="text-grid">
                                <div>
                                    <Box variant="h3" padding={{ top: "n" }}>
                                        Accelerate time to results
                                    </Box>
                                    <Box variant="p">Let your users focus on what they do best by simplifying access to a broad range of AWS infrastructure and services.</Box>
                                </div>
                                <div>
                                    <Box variant="h3" padding={{ top: "n" }}>
                                        Web-based user interface
                                    </Box>
                                    <Box variant="p">Research and Engineering Studio includes a simple web UI designed to simplify user interactions.</Box>
                                </div>
                                <div>
                                    <Box variant="h3" padding={{ top: "n" }}>
                                        Improve collaboration
                                    </Box>
                                    <Box variant="p">Enable your engineers and researchers to collaborate in a common environment with access to shared data.</Box>
                                </div>
                                <div>
                                    <Box variant="h3" padding={{ top: "n" }}>
                                        Simplify user management
                                    </Box>
                                    <Box variant="p">Easily integrate with you existing identity management infrastructure to minimize administrative overhead.</Box>
                                </div>
                                <div>
                                    <Box variant="h3" padding={{ top: "n" }}>
                                        Security and compliance
                                    </Box>
                                    <Box variant="p">Allows IT administrators to standardize engineering and research workspaces and maintain consistent security, compliance and governance.</Box>
                                </div>
                                <div>
                                    <Box variant="h3" padding={{ top: "n" }}>
                                        Management and governance
                                    </Box>
                                    <Box variant="p">Manage access to resources and data at a project level. Monitor and manage costs for each project with a simple interface.</Box>
                                </div>
                            </ColumnLayout>
                        </SpaceBetween>
                    </Container>
                    <Container>
                        <SpaceBetween size="l">
                            <Box variant="h1" tagOverride="h2">
                                Use cases
                            </Box>
                            <ColumnLayout columns={1} variant="text-grid">
                                <div>
                                    <Box variant="h3" padding={{ top: "n" }}>
                                        Remote Desktop Sessions
                                    </Box>
                                    <Box variant="p">
                                        With Research Engineering Studio you get a fully operational Virtual Desktop management solution. Manage a fleet of virtual desktops and provide your research and engineering teams with access to latest Amazon EC2 instances. Integrate with your existing Active Directory for easy access management.
                                    </Box>
                                    <Link href="#" {...externalLinkProps}>
                                        Learn more
                                    </Link>
                                </div>
                            </ColumnLayout>
                        </SpaceBetween>
                    </Container>
                </SpaceBetween>

                <div className="custom-home__sidebar">
                    <SpaceBetween size="xxl">
                        <Container
                            header={
                                <Header variant="h2">
                                    Getting started
                                </Header>
                            }
                        >
                            <ul aria-label="Getting started documentation" className="custom-list-separator">
                                <li>
                                    <Link href="https://docs.aws.amazon.com/res/latest/ug/what-is-res.html" external={true}>
                                        What is Research and Engineering Studio on AWS?
                                    </Link>
                                </li>
                                <li>
                                    <Link href="https://docs.aws.amazon.com/res/latest/ug/plan-your-deployment.html" external={true}>Getting started with Research and Engineering Studio on AWS</Link>
                                </li>
                            </ul>
                        </Container>

                        <Container
                            header={
                                <Header variant="h2">
                                    More resources
                                </Header>
                            }
                        >
                            <ul aria-label="Additional resource links" className="custom-list-separator">
                                <li>
                                    <Link href="https://docs.aws.amazon.com/res/latest/ug/" external={true}>Documentation</Link>
                                </li>
                                <li>
                                    <Link href="https://github.com/aws/res/issues" external={true}>Report an Issue</Link>
                                </li>
                            </ul>
                        </Container>
                    </SpaceBetween>
                </div>
            </Grid>
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
                header={
                    <Header variant={"h1"}>
                        <div className="custom-home__header">
                            <Box padding={{ vertical: "xxl", horizontal: "s" }}>
                                <Grid gridDefinition={[{ colspan: { xxs: 12 } }, { colspan: { xxs: 12 } }]}>
                                    <div className="custom-home__header-title">
                                        <Box variant="h1" fontWeight="bold" padding="n" fontSize="display-l" color="inherit">
                                            Research and Engineering Studio on AWS
                                        </Box>
                                        <Box fontWeight="light" padding={{ bottom: "s" }} fontSize="heading-xl" color="inherit">
                                        Easily manage, deploy and run cloud-based research and engineering environments
                                        </Box>
                                    </div>
                                </Grid>
                            </Box>
                        </div>
                    </Header>
                }
                contentType={"default"}
                content={this.content()}
            />
        );
    }
}

export default withRouter(Home);
