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

import { Link } from "@cloudscape-design/components";
import { AppContext } from "../../common";
import { VirtualDesktopClient } from "../../client";
import Utils from "../../common/utils";
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import "moment-timezone";
import IdeaAppLayout, { IdeaAppLayoutProps } from "../../components/app-layout";
import { TableProps } from "@cloudscape-design/components/table/interfaces";
import IdeaListView from "../../components/list-view";
import VirtualDesktopSessionStatusIndicator from "./components/virtual-desktop-session-status-indicator";
import { withRouter } from "../../navigation/navigation-utils";
import { VirtualDesktopSessionPermission } from "../../client/generated/api";

export interface MySharedVirtualDesktopProps extends IdeaAppLayoutProps, IdeaSideNavigationProps { }

export interface MySharedVirtualDesktopsState { }

class MySharedVirtualDesktopSessions extends Component<MySharedVirtualDesktopProps, MySharedVirtualDesktopsState> {
    VIRTUAL_DESKTOP_SHARED_SESSIONS_TABLE_COLUMN_DEFINITIONS: TableProps.ColumnDefinition<VirtualDesktopSessionPermission>[] = [
        {
            id: "name",
            header: "Name",
            cell: (e) => e.idea_session_name,
        },
        {
            id: "owner",
            header: "Session Owner",
            cell: (e) => e.idea_session_owner,
        },
        {
            id: "base_os",
            header: "Base OS",
            cell: (e) => Utils.getOsTitle(e.idea_session_base_os),
        },
        {
            id: "instance_type",
            header: "Instance Type",
            cell: (e) => e.idea_session_instance_type,
        },
        {
            id: "state",
            header: "State",
            cell: (e) => <VirtualDesktopSessionStatusIndicator state={e.idea_session_state!} hibernation_enabled={e.idea_session_hibernation_enabled!} />,
        },
        {
            id: "expiry",
            header: "Permission Expiry",
            cell: (e) => new Date(e.expiry_date!).toLocaleString(),
        },
        {
            id: "download-dcv-file",
            header: "Download DCV File",
            cell: (e) => {
                return (
                    <Link>
                        <span
                            onClick={() => {
                                this.onDownloadDcvSessionFile(`Shared_Desktop_${e.idea_session_name!}`, e.idea_session_id!, e.idea_session_owner!, AppContext.get().auth().getUsername()).finally();
                            }}
                        >
                            Download
                        </span>
                    </Link>
                );
            },
        },
        {
            id: "connect-session",
            header: "Join Session",
            cell: (e) => {
                return (
                    e.idea_session_state === "READY" && (
                        <Link external>
                            <span
                                onClick={() => {
                                    this.onJoinSession(e.idea_session_id!, e.idea_session_owner!, e.idea_session_name!, AppContext.get().auth().getUsername()).finally();
                                }}
                            >
                                Connect
                            </span>
                        </Link>
                    )
                );
            },
        },
    ];
    listing: RefObject<IdeaListView>;
    virtualDesktopSettings: any;

    constructor(props: MySharedVirtualDesktopProps) {
        super(props);
        this.listing = React.createRef();
        this.virtualDesktopSettings = undefined;
    }

    componentDidMount() {
        AppContext.get()
            .getClusterSettingsService()
            .getVirtualDesktopSettings()
            .then((settings) => {
                this.virtualDesktopSettings = settings;
            });
    }

    onDownloadDcvSessionFile = (idea_session_name: string, idea_session_id: string, idea_session_owner: string, _username: string): Promise<boolean> => {
        return AppContext.get()
            .client()
            .virtualDesktop()
            .getSessionConnection({
                connection: {
                    'idea-session-id': idea_session_id,
                    'idea-session-owner': idea_session_owner,
                },
            })
            .then((result) => {
                let certificatevalidationpolicy = this.virtualDesktopSettings.dcv_connection_gateway.certificate.provided === "true" ? "strict" : "ask-user";
                let endpoint = result.connection?.endpoint;
                if (endpoint === undefined) {
                    endpoint = AppContext.get().getAlbEndpoint();
                }
                const url = new URL(endpoint);
                let sessionFileContent = "[version]\n";
                sessionFileContent += "format=1.0\n";
                sessionFileContent += "[connect]\n";
                sessionFileContent += `user=${AppContext.get().auth().getUsername()}\n`;
                sessionFileContent += `sessionid=${result.connection?.['idea-session-id']}\n`;
                sessionFileContent += `host=${url.host}\n`;
                sessionFileContent += `port=443\n`;
                sessionFileContent += `webport=443\n`;
                sessionFileContent += `quicport=443\n`;
                sessionFileContent += `certificatevalidationpolicy=${certificatevalidationpolicy}\n`;
                sessionFileContent += `authtoken=${result.connection?.['access-token']}\n`;

                const element = document.createElement("a");
                element.setAttribute("href", "data:text/plain;charset=utf-8," + encodeURIComponent(sessionFileContent));
                element.setAttribute("download", `${idea_session_name}.dcv`);
                element.style.display = "none";
                document.body.appendChild(element);
                element.click();
                document.body.removeChild(element);
                return true;
            })
            .catch((error) => {
                console.error(error);
                if (error.errorCode === "SESSION_CONNECTION_ERROR") {
                    this.setFlashMessage(`${idea_session_name} - Error retrieving session connection information. Please reboot the Virtual Desktop and try again.`, "error");
                } else {
                    this.setFlashMessage(`Something went wrong. An error occured when attempting to download DCV file for session ${idea_session_name}. See logs for more information.`, "error");
                }
                return false;
            });
    };

    onJoinSession = (idea_session_id: string, idea_session_owner: string, idea_session_name: string, _username: string): Promise<boolean> => {
        return AppContext.get().client().virtualDesktop()
            .getSessionConnection({
                connection: {
                    'idea-session-id': idea_session_id,
                    'idea-session-owner': idea_session_owner,
                },
            })
            .then((result) => {
                return `${result.connection?.endpoint}${result.connection?.['web-url-path']}?authToken=${result.connection?.['access-token']}#${result.connection?.['idea-session-id']}`;
            })
            .then((url) => {
                window.open(url);
                return true;
            })
            .catch((error) => {
                console.error(error);
                if (error.errorCode === "SESSION_CONNECTION_ERROR") {
                    this.setFlashMessage(`${idea_session_name} - Error retrieving session connection information. Please reboot the Virtual Desktop and try again.`, "error");
                } else {
                    this.setFlashMessage(`Something went wrong. An error occured when attempting to connect to session ${idea_session_name}. See logs for more information.`, "error");
                }
                return false;
            });
    };

    setFlashMessage = (content: React.ReactNode, type: "success" | "info" | "error") => {
        this.props.onFlashbarChange({
            items: [
                {
                    content: content,
                    dismissible: true,
                    type: type,
                },
            ],
        });
    };

    getListing(): IdeaListView {
        return this.listing.current!;
    }

    getVirtualDesktopClient(): VirtualDesktopClient {
        return AppContext.get().client().virtualDesktop();
    }

    buildListing() {
        return (
            <IdeaListView
                ref={this.listing}
                title="Shared Desktops"
                showPreferences={true}
                preferencesKey={"shared-desktops"}
                description="List of Virtual Desktops shared with you. Unless user has Admin or Owner profile, session owner must be connected in order for them to connect."
                showPaginator={true}
                onRefresh={() => {
                    this.getListing().fetchRecords();
                }}
                showDateRange={true}
                dateRange={{
                    type: "relative",
                    amount: 1,
                    unit: "month",
                }}
                dateRangeFilterKeyOptions={[{ value: "idea_session_created_on", label: "Session Created" }]}
                showFilters={true}
                filterType="select"
                selectFilters={[
                    {
                        name: "$all",
                    },
                    {
                        name: "idea_session_state",
                        choices: [
                            {
                                title: "All States",
                                value: "",
                            },
                            {
                                title: "Ready",
                                value: "READY",
                            },
                            {
                                title: "Provisioning",
                                value: "PROVISIONING",
                            },
                            {
                                title: "Stopped",
                                value: "STOPPED",
                            },
                            {
                                title: "Stopped Idle",
                                value: "STOPPED_IDLE",
                            },
                            {
                                title: "Stopping",
                                value: "STOPPING",
                            },
                            {
                                title: "Initializing",
                                value: "INITIALIZING",
                            },
                            {
                                title: "Creating",
                                value: "CREATING",
                            },
                            {
                                title: "Resuming",
                                value: "RESUMING",
                            },
                            {
                                title: "Deleting",
                                value: "DELETING",
                            },
                            {
                                title: "Error",
                                value: "ERROR",
                            },
                        ],
                    },
                    {
                        name: "idea_session_base_os",
                        choices: [
                            {
                                title: "All Operating Systems",
                                value: "",
                            },
                            {
                                title: "Amazon Linux 2",
                                value: "amazonlinux2",
                            },
                            {
                                title: "Amazon Linux 2023",
                                value: "amzn2023",
                            },
                            {
                                title: "Windows",
                                value: "windows",
                            },
                            {
                                title: "RHEL 8",
                                value: "rhel8"
                            },
                            {
                                title: "RHEL 9",
                                value: "rhel9"
                            },
                            {
                                title: "Ubuntu 2204",
                                value: "ubuntu2204"
                            },
                            {
                                title: "Ubuntu 2404",
                                value: "ubuntu2404"
                            },
                            {
                                title: "Rocky 9",
                                value: "rocky9"
                            }
                        ],
                    },
                ]}
                onFilter={(filters) => {
                    return filters;
                }}
                onFetchRecords={() => {
                    const getFilterValue = (key: string): string | undefined => 
                        this.getListing().getFilters()?.find(f => f.key === key)?.value as string | undefined;

                    const dateRangeFilters = this.getListing().getFormatedDateRange();
                    const sessionName = getFilterValue("$all")
                    const state = getFilterValue("idea_session_state")
                    const baseOs = getFilterValue("idea_session_base_os")

                    return this.getVirtualDesktopClient()
                        .listSharedPermissions({
                            username: AppContext.get().auth().getUsername(),
                            baseOs: baseOs,
                            sessionName: sessionName,
                            state: state,
                            dateRangeKey: dateRangeFilters?.key,
                            after: dateRangeFilters?.start ? new Date(dateRangeFilters.start).getTime().toString() : undefined,
                            before: dateRangeFilters?.end  ? new Date(dateRangeFilters.end).getTime().toString() : undefined,
                        })
                        .then((data) => {
                            this.setState({
                                profileCount: data.listing!.length ?? 0
                            })
                            return {
                                listing: data.listing!,
                            };
                        })
                        .catch((error) => {
                            this.props.onFlashbarChange({
                                items: [
                                    {
                                        content: error.message,
                                        type: "error",
                                        dismissible: true,
                                    },
                                ],
                            });
                            throw error;
                        });
                }}
                columnDefinitions={this.VIRTUAL_DESKTOP_SHARED_SESSIONS_TABLE_COLUMN_DEFINITIONS}
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
                        text: "Shared Desktops",
                        href: "",
                    },
                ]}
                content={<div>{this.buildListing()}</div>}
            />
        );
    }
}

export default withRouter(MySharedVirtualDesktopSessions);
