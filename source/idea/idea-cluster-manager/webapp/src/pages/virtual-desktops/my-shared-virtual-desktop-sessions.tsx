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
import { VirtualDesktopSessionConnectionInfo, VirtualDesktopSessionPermission } from "../../client/data-model";
import { VirtualDesktopClient } from "../../client";
import Utils from "../../common/utils";
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import "moment-timezone";
import IdeaAppLayout, { IdeaAppLayoutProps } from "../../components/app-layout";
import { TableProps } from "@cloudscape-design/components/table/interfaces";
import IdeaListView from "../../components/list-view";
import VirtualDesktopSessionStatusIndicator from "./components/virtual-desktop-session-status-indicator";
import { withRouter } from "../../navigation/navigation-utils";

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

    constructor(props: MySharedVirtualDesktopProps) {
        super(props);
        this.listing = React.createRef();
    }

    onDownloadDcvSessionFile = (idea_session_name: string, idea_session_id: string, idea_session_owner: string, username: string): Promise<boolean> => {
        return AppContext.get()
            .client()
            .virtualDesktop()
            .getSessionConnectionInfo({
                connection_info: {
                    idea_session_id: idea_session_id,
                    idea_session_owner: idea_session_owner,
                    username: username,
                },
            })
            .then((result) => {
                let endpoint = result.connection_info?.endpoint;
                if (endpoint === undefined) {
                    endpoint = AppContext.get().getAlbEndpoint();
                }
                const url = new URL(endpoint);
                let sessionFileContent = "[version]\n";
                sessionFileContent += "format=1.0\n";
                sessionFileContent += "[connect]\n";
                sessionFileContent += `user=${AppContext.get().auth().getUsername()}\n`;
                sessionFileContent += `sessionid=${result.connection_info?.dcv_session_id}\n`;
                sessionFileContent += `host=${url.host}\n`;
                sessionFileContent += `port=443\n`;
                sessionFileContent += `webport=443\n`;
                sessionFileContent += `quicport=443\n`;
                sessionFileContent += `certificatevalidationpolicy=accept-untrusted\n`;
                sessionFileContent += `authtoken=${result.connection_info?.access_token}\n`;

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
                // Popup error with message to reboot the VDI
                if (error.errorCode === "SESSION_CONNECTION_ERROR") {
                    this.setFlashMessage(`${idea_session_name} - Error retrieving session connection information. Please reboot the Virtual Desktop and try again.`, "error");
                } else {
                    this.setFlashMessage(`Something went wrong. An error occured when attempting to download DCV file for session ${idea_session_name}. See logs for more information.`, "error");
                }
                return false;
            });
    };

    onJoinSession = (idea_session_id: string, idea_session_owner: string, idea_session_name: string, username: string): Promise<boolean> => {
        let connection_info: VirtualDesktopSessionConnectionInfo = {
            idea_session_id: idea_session_id,
            idea_session_owner: idea_session_owner,
        };

        if (username) {
            connection_info.username = username;
        }

        return AppContext.get().client().virtualDesktop()
            .getSessionConnectionInfo({ connection_info: connection_info })
            .then((result) => {
                return `${result.connection_info?.endpoint}${result.connection_info?.web_url_path}?authToken=${result.connection_info?.access_token}#${result.connection_info?.dcv_session_id}`;
            })
            .then((url) => {
                window.open(url);
                return true;
            })
            .catch((error) => {
                console.error(error);
                // Popup error with message to reboot the VDI
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
                        ],
                    },
                ]}
                onFilter={(filters) => {
                    return filters;
                }}
                onFetchRecords={() => {
                    return this.getVirtualDesktopClient()
                        .listSharedPermissions({
                            filters: this.getListing().getFilters(),
                            paginator: this.getListing().getPaginator(),
                            date_range: this.getListing().getFormatedDateRange(),
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
