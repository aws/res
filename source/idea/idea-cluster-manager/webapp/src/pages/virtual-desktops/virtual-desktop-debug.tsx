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

import { Button, Container, Header, SpaceBetween } from "@cloudscape-design/components";
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import ReactJson from "react-json-view";
import { AppContext } from "../../common";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faSpinner } from "@fortawesome/free-solid-svg-icons/faSpinner";
import IdeaTabs from "../../components/tabs";
import IdeaAppLayout, { IdeaAppLayoutProps } from "../../components/app-layout";
import { withRouter } from "../../navigation/navigation-utils";
import VirtualDesktopDCVClient from "../../client/virtual-desktop-dcv-client";

export interface VirtualDesktopDebugProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {}

export interface VirtualDesktopDebugState {
    vdHostHealth: any;
    vdSessionHealth: any;
    vdHostHealthLoading: boolean;
    vdSessionHealthLoading: boolean;
}

class VirtualDesktopDebug extends Component<VirtualDesktopDebugProps, VirtualDesktopDebugState> {
    constructor(props: VirtualDesktopDebugProps) {
        super(props);
        this.state = {
            vdHostHealthLoading: true,
            vdSessionHealthLoading: true,
            vdHostHealth: {},
            vdSessionHealth: {},
        };
    }

    getVirtualDesktopDCVClient(): VirtualDesktopDCVClient {
        return AppContext.get().client().virtualDesktopDCV();
    }

    componentWillUnmount() {
        this.setState({
            vdSessionHealth: {},
            vdHostHealth: {},
        });
    }

    loadSessionHealth() {
        this.setState(
            {
                vdSessionHealthLoading: true,
            },
            () => {
                this.getVirtualDesktopDCVClient()
                    .describeSessions({})
                    .then((response) => {
                        let health = response.response;
                        delete health?.request_id;
                        delete health?.next_token;
                        this.setState({
                            vdSessionHealth: health,
                            vdSessionHealthLoading: false,
                        });
                    });
            }
        );
    }

    loadServerHealth() {
        this.setState(
            {
                vdHostHealthLoading: true,
            },
            () => {
                this.getVirtualDesktopDCVClient()
                    .describeServers({})
                    .then((response) => {
                        let health = response.response;
                        delete health?.request_id;
                        delete health?.next_token;
                        this.setState({
                            vdHostHealth: health,
                            vdHostHealthLoading: false,
                        });
                    });
            }
        );
    }

    loadHealth() {
        this.loadServerHealth();
        this.loadSessionHealth();
    }

    componentDidMount() {
        this.loadHealth();
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
                        href: "#/virtual-desktop/debug",
                    },
                    {
                        text: "Debug",
                        href: "",
                    },
                ]}
                header={
                    <Header
                        variant={"h1"}
                        description={"View hosts and sessions registered with Amazon DCV Broker"}
                        actions={
                            <SpaceBetween direction="horizontal" size="xs">
                                <Button
                                    iconName="refresh"
                                    variant="normal"
                                    onClick={() => {
                                        this.loadHealth();
                                    }}
                                />
                            </SpaceBetween>
                        }
                    >
                        Debug Virtual Desktop Sessions
                    </Header>
                }
                contentType="default"
                content={
                    <Container>
                        <IdeaTabs
                            tabs={[
                                {
                                    label: "VD Host",
                                    id: "vdHost",
                                    content: (
                                        <Container>
                                            {this.state.vdHostHealthLoading && <FontAwesomeIcon icon={faSpinner} size={"2x"} spin={true} />}
                                            {!this.state.vdHostHealthLoading && <ReactJson theme={AppContext.get().isDarkMode() ? "monokai" : "grayscale:inverted"} src={this.state.vdHostHealth} displayDataTypes={false} iconStyle={"circle"} onEdit={false} name={false} />}
                                        </Container>
                                    ),
                                },
                                {
                                    label: "VD Sessions",
                                    id: "vdSessions",
                                    content: (
                                        <Container>
                                            {this.state.vdSessionHealthLoading && <FontAwesomeIcon icon={faSpinner} size={"2x"} spin={true} />}
                                            {!this.state.vdSessionHealthLoading && <ReactJson theme={AppContext.get().isDarkMode() ? "monokai" : "grayscale:inverted"} src={this.state.vdSessionHealth} displayDataTypes={false} iconStyle={"circle"} onEdit={false} name={false} />}
                                        </Container>
                                    ),
                                },
                            ]}
                        />
                    </Container>
                }
            />
        );
    }
}

export default withRouter(VirtualDesktopDebug);
