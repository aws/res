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

import { Component } from "react";

import { Badge, Box, Button, Container, Grid, Header, Link, SpaceBetween } from "@cloudscape-design/components";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faLinux, faApple, faWindows } from "@fortawesome/free-brands-svg-icons";
import { faDownload } from "@fortawesome/free-solid-svg-icons";
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import { AppContext } from "../../common";
import Utils from "../../common/utils";
import { Constants } from "../../common/constants";
import IdeaAppLayout, { IdeaAppLayoutProps } from "../../components/app-layout";
import { withRouter } from "../../navigation/navigation-utils";

export interface SSHAccessProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {}

export interface SSHAccessState {
    downloadPpkLoading: boolean;
    downloadPemLoading: boolean;
    sshHostIp: string;
}

class SSHAccess extends Component<SSHAccessProps, SSHAccessState> {
    constructor(props: SSHAccessProps) {
        super(props);
        this.state = {
            downloadPpkLoading: false,
            downloadPemLoading: false,
            sshHostIp: "",
        };
    }

    componentDidMount() {
        AppContext.get()
            .getClusterSettingsService()
            .getModuleSettings(Constants.MODULE_BASTION_HOST)
            .then((moduleInfo) => {
                this.setState({
                    sshHostIp: Utils.asString(moduleInfo.public_ip),
                });
            });
    }

    onDownloadPrivateKey = (keyFormat: "pem" | "ppk") => {
        const state: any = {};
        if (keyFormat === "pem") {
            state.downloadPemLoading = true;
        } else if (keyFormat === "ppk") {
            state.downloadPpkLoading = true;
        }
        this.setState(state, () => {
            AppContext.get()
                .auth()
                .downloadPrivateKey(keyFormat)
                .finally(() => {
                    const state: any = {};
                    if (keyFormat === "pem") {
                        state.downloadPemLoading = false;
                    } else if (keyFormat === "ppk") {
                        state.downloadPpkLoading = false;
                    }
                    this.setState(state);
                });
        });
    };

    render() {
        const getKeyName = (keyFormat: string): string => {
            const clusterName =  AppContext.get().getClusterName();
            const username = AppContext.get().auth().getUsername();
            return `${username}_${clusterName}_privatekey.${keyFormat}`;
        };

        const getUsername = (): string => {
            return AppContext.get().auth().getUsername();
        };

        const getClusterName = (): string => {
            return AppContext.get().getClusterName();
        };

        const getAwsRegion = (): string => {
            return AppContext.get().getAwsRegion();
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
                        text: "RES",
                        href: "#/",
                    },
                    {
                        text: "Home",
                        href: "#/",
                    },
                    {
                        text: "SSH Access",
                        href: "",
                    },
                ]}
                header={<Header variant={"h1"}>SSH Access</Header>}
                contentType={"default"}
                content={
                    <Grid gridDefinition={[{ colspan: { xxs: 12, xs: 6 } }, { colspan: { xxs: 12, xs: 6 } }]}>
                        <Container variant="default">
                            <SpaceBetween size={"xl"}>
                                <Box textAlign="center">
                                    <FontAwesomeIcon icon={faLinux} size="5x" />
                                    &nbsp; &nbsp;
                                    <FontAwesomeIcon icon={faApple} size="5x" />
                                </Box>
                                <Header variant="h3">Access environment using Linux / MacOS</Header>
                            </SpaceBetween>
                            <p>Follow the below steps to connect to the cluster using Terminal on your Linux or MacOS laptop/workstation:</p>
                            <SpaceBetween size="m" direction="vertical">
                                <Box>
                                    <h3>Step 1: Download my Private Key</h3>
                                    <p>Download the private key file, and save it your ~/.ssh directory. </p>
                                    <p>
                                        <Button variant="primary" loading={this.state.downloadPemLoading} onClick={() => this.onDownloadPrivateKey("pem")}>
                                            <FontAwesomeIcon icon={faDownload} /> Download Private Key
                                        </Button>
                                    </p>
                                </Box>
                                <Box>
                                    <h3>Step 2: Modify key permissions</h3>
                                    Run: &nbsp;
                                    <Box variant={"code"}>chmod 600 ~/.ssh/{getKeyName("pem")}</Box>
                                </Box>
                                <Box>
                                    <h3>Step 3: Connect to the cluster</h3>
                                    Run: &nbsp;
                                    <Box variant={"code"}>
                                        ssh -i ~/.ssh/{getKeyName("pem")} {getUsername()}@{this.state.sshHostIp}
                                    </Box>
                                </Box>
                                <Box>
                                    <h3>
                                        <Badge color="green">Optional</Badge> Step 4: Create SSH config
                                    </h3>
                                    <p>
                                        If you don't want your session to be automatically closed after a couple of minutes of inactivity, edit: <code>~/.ssh/config</code> and add:
                                    </p>

                                    <Box variant={"code"}>
                                        Host {getClusterName()}-{getAwsRegion()}
                                        <br />
                                        &nbsp;&nbsp;User {getUsername()}
                                        <br />
                                        &nbsp;&nbsp;Hostname {this.state.sshHostIp}
                                        <br />
                                        &nbsp;&nbsp;ServerAliveInterval 10
                                        <br />
                                        &nbsp;&nbsp;ServerAliveCountMax 2<br />
                                        &nbsp;&nbsp;IdentityFile ~/.ssh/{getKeyName("pem")}
                                    </Box>

                                    <p>
                                        Once updated, you can simply run below to connect to your cluster: <br />
                                        <Box variant={"code"}>
                                            ssh {getClusterName()}-{getAwsRegion()}
                                        </Box>
                                    </p>
                                </Box>
                            </SpaceBetween>
                        </Container>

                        <Container variant="default">
                            <SpaceBetween size={"xl"}>
                                <Box textAlign="center">
                                    <FontAwesomeIcon icon={faWindows} size="5x" />
                                </Box>
                                <Header variant="h3">Access environment using Windows (PuTTY)</Header>
                            </SpaceBetween>

                            <p>Follow the below steps to connect to the cluster using Terminal on your Windows laptop/workstation:</p>
                            <SpaceBetween size="m" direction="vertical">
                                <Box>
                                    <h3>Step 1: Download my PuTTY private key</h3>
                                    <p>
                                        <Button loading={this.state.downloadPpkLoading} variant="primary" onClick={() => this.onDownloadPrivateKey("ppk")}>
                                            <FontAwesomeIcon icon={faDownload} /> Download Private Key
                                        </Button>
                                    </p>
                                </Box>
                                <Box>
                                    <h3>Step 2: Configure PuTTY</h3>
                                    <ul>
                                        <li>
                                            <Link external={true} href="https://www.chiark.greenend.org.uk/~sgtatham/putty/latest.html">
                                                Download PuTTY
                                            </Link>
                                        </li>
                                        <li>
                                            As hostname, enter <code>{this.state.sshHostIp}</code>
                                        </li>
                                        <li>
                                            Navigate to Connection &gt; SSH &gt; Auth and enter the path of your key <code>{getKeyName("ppk")}</code> under <b>"Private Key used for Authentication"</b>
                                        </li>
                                        <li>Save your session</li>
                                        <li>Click connect/open to access the cluster</li>
                                    </ul>
                                </Box>
                                <Box>
                                    <h3>
                                        <Badge color="green">Optional</Badge> Step 3: Enable KeepAlive
                                    </h3>
                                    <p>
                                        If you don't want your session to be automatically closed after a couple of minutes of inactivity, go to Connection and add "3" as <b>"Seconds between KeepAlives"</b>
                                    </p>
                                </Box>
                            </SpaceBetween>
                        </Container>
                    </Grid>
                }
            />
        );
    }
}

export default withRouter(SSHAccess);
