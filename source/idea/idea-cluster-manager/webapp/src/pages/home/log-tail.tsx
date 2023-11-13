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

import { IdeaAppLayoutProps } from "../../components/app-layout";
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import React, { Component, RefObject } from "react";
import { withRouter } from "../../navigation/navigation-utils";
import { AppContext } from "../../common";
import Utils from "../../common/utils";
import { Box, Button, Container, Grid, StatusIndicator, StatusIndicatorProps } from "@cloudscape-design/components";
import { XTerm } from "xterm-for-react";
import { FitAddon } from "xterm-addon-fit";

export interface IdeaLogTailProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {}

export interface IdeaLogTailState {
    cwd: string;
    logFile: string;
    next_token: string;
    autoScroll: boolean;
    statusVisible: boolean;
    statusType: StatusIndicatorProps.Type;
    statusDescription: string;

    pollingStatus: boolean;
    emptyReceives: number;
}

const MAX_LINE_COUNT = 1000;
const MAX_EMPTY_RECEIVES = 10;

class IdeaLogTail extends Component<IdeaLogTailProps, IdeaLogTailState> {
    logEntries: RefObject<HTMLDivElement>;
    interval: any;
    xterm: RefObject<XTerm>;
    xtermFitAddon: FitAddon;

    constructor(props: IdeaLogTailProps) {
        super(props);
        this.logEntries = React.createRef();
        this.xterm = React.createRef();
        this.xtermFitAddon = new FitAddon();
        this.interval = null;
        this.state = {
            cwd: "",
            logFile: "",
            next_token: "",
            autoScroll: true,
            statusType: "loading",
            statusDescription: "",
            statusVisible: true,
            pollingStatus: true,
            emptyReceives: 0,
        };
    }

    startPolling() {
        this.interval = setInterval(() => {
            if (Utils.isEmpty(this.state.next_token)) {
                return;
            }
            this.setState(
                {
                    statusVisible: true,
                    statusType: "loading",
                    statusDescription: "fetching new entries ...",
                    pollingStatus: true,
                },
                () => {
                    AppContext.get()
                        .client()
                        .fileBrowser()
                        .tailFile({
                            next_token: this.state.next_token,
                            line_count: MAX_LINE_COUNT,
                            file: this.state.logFile,
                        })
                        .then((result) => {
                            const lines = result.lines!;
                            lines.forEach((line) => {
                                this.newLogEntry(line);
                            });
                            let emptyReceives = this.state.emptyReceives;
                            if (lines.length === 0) {
                                emptyReceives = emptyReceives + 1;
                            } else {
                                emptyReceives = 0;
                            }
                            this.setState(
                                {
                                    statusVisible: false,
                                    emptyReceives: emptyReceives,
                                    next_token: Utils.asString(result.next_token),
                                },
                                () => {
                                    if (this.state.emptyReceives > MAX_EMPTY_RECEIVES) {
                                        console.log(`reached max empty receives: ${MAX_EMPTY_RECEIVES}. stop polling.`);
                                        this.stopPolling();
                                    }
                                }
                            );
                        })
                        .catch((error) => {
                            this.setState(
                                {
                                    statusVisible: true,
                                    statusType: "error",
                                    statusDescription: error.message,
                                    emptyReceives: this.state.emptyReceives + 1,
                                },
                                () => {
                                    if (this.state.emptyReceives > MAX_EMPTY_RECEIVES) {
                                        this.stopPolling();
                                    }
                                }
                            );
                        });
                }
            );
        }, 6000);
        console.log("polling started");
    }

    stopPolling() {
        if (this.interval != null) {
            clearInterval(this.interval);
            console.log("polling stopped");
            this.setState({
                pollingStatus: false,
                emptyReceives: 0,
            });
        }
    }

    newLogEntry = (line: string) => {
        this.xterm.current!.terminal.writeln(line.trim());
    };

    componentDidMount() {
        Utils.hideLoadingAnimation();

        const file = Utils.asString(this.props.searchParams.get("file"));
        const cwd = Utils.asString(this.props.searchParams.get("cwd"));
        this.setState({
            logFile: file,
            cwd: cwd,
        });

        const terminal = this.xterm.current?.terminal!;
        terminal.options = {
            scrollback: 10000,
        };
        terminal.onKey((event) => {
            if (event.domEvent.code === "Enter") {
                terminal.writeln("");
            }
        });
        this.xtermFitAddon.activate(terminal);
        this.xtermFitAddon.fit();

        let lines: string[];
        AppContext.get()
            .client()
            .fileBrowser()
            .tailFile({
                line_count: MAX_LINE_COUNT,
                file: file,
            })
            .then((result) => {
                lines = result.lines!;
                lines.forEach((line) => {
                    this.newLogEntry(line);
                });
                this.setState(
                    {
                        next_token: Utils.asString(result.next_token),
                        statusVisible: false,
                    },
                    () => {
                        this.startPolling();
                    }
                );
            })
            .catch((error) => {
                this.setState({
                    statusType: "error",
                    statusDescription: error.message,
                });
            });
    }

    destroy(): Promise<boolean> {
        return new Promise((resolve, _) => {
            this.stopPolling();
            resolve(true);
        });
    }

    componentWillUnmount() {
        this.destroy().finally();
    }

    render() {
        return (
            <Container
                disableContentPaddings={true}
                disableHeaderPaddings={true}
                header={
                    <Grid gridDefinition={[{ colspan: { xxs: 9 } }, { colspan: { xxs: 3 } }]} disableGutters={true}>
                        <Box className={"idea-log-tail-header"}>
                            <span className={"title"}>Log Tail</span>
                            <span className={"file-name"}>{this.state.logFile}</span>
                            <span>
                                <input
                                    type={"checkbox"}
                                    checked={this.state.pollingStatus}
                                    onChange={(event) => {
                                        this.setState(
                                            {
                                                pollingStatus: event.target.checked,
                                            },
                                            () => {
                                                if (event.target.checked) {
                                                    this.startPolling();
                                                } else {
                                                    this.stopPolling();
                                                }
                                            }
                                        );
                                    }}
                                />{" "}
                                Auto-refresh
                            </span>
                            {this.state.statusVisible && <StatusIndicator type={this.state.statusType}>{this.state.statusDescription}</StatusIndicator>}
                        </Box>

                        <Box textAlign={"right"} padding={{ top: "xxs", right: "xs" }}>
                            <Button
                                variant={"primary"}
                                onClick={() => {
                                    this.setState(
                                        {
                                            statusVisible: true,
                                            statusType: "loading",
                                            statusDescription: "destroying log tail instance ...",
                                        },
                                        () => {
                                            this.destroy().then(() => {
                                                let url = "/home/file-browser";
                                                if (Utils.isNotEmpty(this.state.cwd)) {
                                                    url = `${url}?cwd=${this.state.cwd}`;
                                                }
                                                this.props.navigate(url);
                                            });
                                        }
                                    );
                                }}
                            >
                                Close
                            </Button>
                        </Box>
                    </Grid>
                }
            >
                <div className={"idea-log-tail"}>
                    <XTerm ref={this.xterm} className={"idea-terminal"} />
                </div>
            </Container>
        );
    }
}

export default withRouter(IdeaLogTail);
