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

import { Box, Button, Cards, Header, SegmentedControl, SpaceBetween, Toggle } from "@cloudscape-design/components";
import { AppContext } from "../../common";
import { Project, SocaUserInputChoice, VDIPermissions, VirtualDesktopBaseOS, VirtualDesktopSession, VirtualDesktopSessionPermission, VirtualDesktopSessionScreenshot, VirtualDesktopSoftwareStack } from "../../client/data-model";
import { ProjectsClient, VirtualDesktopClient } from "../../client";
import IdeaForm from "../../components/form";
import Utils from "../../common/utils";
import IdeaConfirm from "../../components/modals";
import { withRouter } from "../../navigation/navigation-utils";
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import "moment-timezone";
import VirtualDesktopScheduleModal from "./components/virtual-desktop-schedule-modal";
import VirtualDesktopSessionCard from "./components/virtual-desktop-session-card";
import IdeaAppLayout, { IdeaAppLayoutProps } from "../../components/app-layout";
import { DcvClientHelpModal } from "./components/dcv-client-help-modal";
import moment from "moment";
import UpdateSessionPermissionModal from "./forms/virtual-desktop-update-session-permissions-form";
import dot from "dot-object";
import VirtualDesktopCreateSessionForm from "./forms/virtual-desktop-create-session-form";
import VirtualDesktopUtilsClient from "../../client/virtual-desktop-utils-client";
import AuthzClient from "../../client/authz-client";

const CARD_HEADER_CLASS_NAME = "awsui_card-header_p8a6i_9tpvn_272";
const OS_FILTER_LINUX_ID = "linux";
const OS_FILTER_WINDOWS_ID = "windows";
const OS_FILTER_ALL_ID = "$all";
const AUTO_REFRESH_TIME_IN_MS = 15000;

export interface MyVirtualDesktopSessionsProps extends IdeaAppLayoutProps, IdeaSideNavigationProps { }

export interface MyVirtualDesktopConfirmModalActionProps {
    actionTitle: string;
    onConfirm: () => void;
    actionText: string;
    onCancel: () => void;
}

interface ScreenShotState {
    data: string;
    time: moment.Moment;
}

export interface MyVirtualDesktopSessionsState {
    selectedItems: any[];
    directoryServiceProvider: string;
    sessions: Map<string, VirtualDesktopSession>;
    loading: boolean;
    screenshots: { [k: string]: ScreenShotState };
    selectedSession: VirtualDesktopSession | undefined;
    selectedSessionApplicableInstanceTypes: SocaUserInputChoice[];
    osFilter: string;
    showDcvClientHelpModal: boolean;
    showCreateSessionForm: boolean;
    showUpdateSessionForm: boolean;
    showUpdateSessionPermissionForm: boolean;
    confirmAction: MyVirtualDesktopConfirmModalActionProps;
    activeConnectionConfirmModalOnConfirm: () => void;
    userProjects: Project[];
    softwareStacks: { [k: string]: VirtualDesktopSoftwareStack };
    autoRefreshIntervalId: NodeJS.Timer | undefined;
    lastRefreshTimeInSec: number;
}

class MyVirtualDesktopSessions extends Component<MyVirtualDesktopSessionsProps, MyVirtualDesktopSessionsState> {
    createSessionForm: RefObject<VirtualDesktopCreateSessionForm>;
    updateSessionForm: RefObject<IdeaForm>;
    updateSessionPermissionForm: RefObject<UpdateSessionPermissionModal>;
    sessionActionConfirmModal: RefObject<IdeaConfirm>;
    activeConnectionConfirmModal: RefObject<IdeaConfirm>;
    scheduleModal: RefObject<VirtualDesktopScheduleModal>;
    refreshInterval: any;
    virtualDesktopSettings: any;
    componentMounted: boolean;
    lastRefreshTime: Date;

    constructor(props: MyVirtualDesktopSessionsProps) {
        super(props);
        this.createSessionForm = React.createRef();
        this.updateSessionForm = React.createRef();
        this.updateSessionPermissionForm = React.createRef();
        this.sessionActionConfirmModal = React.createRef();
        this.activeConnectionConfirmModal = React.createRef();
        this.scheduleModal = React.createRef();
        this.componentMounted = true;
        this.virtualDesktopSettings = undefined;
        this.lastRefreshTime = new Date();

        this.state = {
            selectedItems: [],
            directoryServiceProvider: "",
            sessions: new Map<string, VirtualDesktopSession>(),
            loading: true,
            screenshots: {},
            selectedSession: undefined,
            selectedSessionApplicableInstanceTypes: [],
            osFilter: OS_FILTER_ALL_ID,
            showDcvClientHelpModal: false,
            showCreateSessionForm: false,
            showUpdateSessionForm: false,
            showUpdateSessionPermissionForm: false,
            softwareStacks: {},
            userProjects: [],
            confirmAction: {
                actionTitle: "",
                actionText: "",
                onConfirm: () => { },
                onCancel: () => { },
            },
            activeConnectionConfirmModalOnConfirm: () => { },
            autoRefreshIntervalId: undefined,
            lastRefreshTimeInSec: 0,
        };
    }

    componentDidMount() {
        this.componentMounted = true;

        AppContext.get()
            .getClusterSettingsService()
            .getDirectoryServiceSettings()
            .then((settings) => {
                this.setState({
                    directoryServiceProvider: dot.pick("provider", settings),
                });
            });

        AppContext.get()
            .getClusterSettingsService()
            .getVirtualDesktopSettings()
            .then((settings) => {
                this.virtualDesktopSettings = settings;
            });

        Utils.fetchProjectsFilteredByVDIPermissions(this.isAdmin(), "create_sessions")
            .then((userProjects) => {
              this.setState({
                  userProjects,
              });
            });

        const refresh = () => {
            if (!this.componentMounted) {
                return Promise.resolve(true);
            }

            this.setState({
                lastRefreshTimeInSec: new Date().getSeconds() - this.lastRefreshTime.getSeconds(),
            });
        };

        this.refreshSessions();

        this.refreshInterval = setInterval(refresh, AUTO_REFRESH_TIME_IN_MS);
    }

    componentWillUnmount() {
        this.componentMounted = false;
        clearInterval(this.refreshInterval);
    }

    getProjectsClient(): ProjectsClient {
        return AppContext.get().client().projects();
    }

    getVirtualDesktopUtilsClient(): VirtualDesktopUtilsClient {
        return AppContext.get().client().virtualDesktopUtils();
    }

    getVirtualDesktopClient(): VirtualDesktopClient {
        return AppContext.get().client().virtualDesktop();
    }

    getUpdateSessionForm(): IdeaForm {
        return this.updateSessionForm.current!;
    }

    getCreateSessionForm(): VirtualDesktopCreateSessionForm {
        return this.createSessionForm.current!;
    }

    getUpdateSessionPermissionForm(): UpdateSessionPermissionModal {
        return this.updateSessionPermissionForm.current!;
    }

    getSessionActionConfirmModal(): IdeaConfirm {
        return this.sessionActionConfirmModal.current!;
    }

    getActiveConnectionConfirmModal(): IdeaConfirm {
        return this.activeConnectionConfirmModal.current!;
    }

    getScheduleModal(): VirtualDesktopScheduleModal {
        return this.scheduleModal.current!;
    }

    getAuthzClient(): AuthzClient {
        return AppContext.get().client().authz();
    }

    isAdmin(): boolean {
        return AppContext.get().auth().isAdmin();
    }

    canCreateSession(): boolean {
      if (this.isAdmin()) {
        return true;
      } else {
        return this.state.userProjects.length > 0;
      }
    }

    fetchSessions(): Promise<boolean> {
        return AppContext.get()
            .client()
            .virtualDesktop()
            .listSessions({
                filters: [
                    {
                        key: "base_os",
                        value: this.state.osFilter,
                    },
                    {
                        key: "owner",
                        value: AppContext.get().auth().getUsername(),
                    }
                ],
                paginator: {
                    page_size: 100,
                },
            })
            .then((result) => {
                return this.setSessions(result?.listing, this.state.osFilter);
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
                return false;
            });
    }

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

    async fetchSessionScreenshots() {
        const sessions = this.state.sessions;
        if (sessions.size === 0) {
            return;
        }

        let screenshots: VirtualDesktopSessionScreenshot[] = [];
        sessions.forEach((session) => {
            if (Utils.isEmpty(session.dcv_session_id) || session.dcv_session_id === undefined) {
                return true;
            } else if (session.state !== "READY") {
                // no screenshots required unless the session is ready.
                return true;
            } else if (this.state.screenshots[session.dcv_session_id] !== undefined && moment().subtract(5, "minutes").isBefore(this.state.screenshots[session.dcv_session_id].time)) {
                // do not ask for screenshots if we already have a screenshot that is less than 5 minutes old
                return true;
            }

            screenshots.push({
                idea_session_owner: AppContext.get().auth().getUsername(),
                idea_session_id: session.idea_session_id,
                dcv_session_id: session.dcv_session_id,
                create_time: session.created_on,
            });
        });

        if (Utils.isEmpty(screenshots)) {
            // not calling the screenshots API when we know that there are no sessions that are active.
            return;
        }

        screenshots = screenshots.sort((a: VirtualDesktopSessionScreenshot, b: VirtualDesktopSessionScreenshot) => {
            if (a === undefined && b === undefined) {
                return 0;
            }

            if (a === undefined || a.dcv_session_id === undefined) {
                return 1;
            }

            if (b === undefined || b.dcv_session_id === undefined) {
                return -1;
            }

            if (this.state.screenshots[a.dcv_session_id] === undefined && this.state.screenshots[b.dcv_session_id] === undefined) {
                return moment(a.create_time).diff(b.create_time);
            }

            if (this.state.screenshots[a.dcv_session_id] === undefined) {
                return 1;
            }

            if (this.state.screenshots[a.dcv_session_id] === undefined) {
                return -1;
            }

            return this.state.screenshots[a.dcv_session_id].time.diff(this.state.screenshots[b.dcv_session_id].time);
        });

        const delay = async (interval: number) => {
            return new Promise((resolve) => {
                setTimeout(() => resolve(true), interval);
            });
        };

        const batchSize = 3;
        const screenshotState = this.state.screenshots;
        for (let i = 0; i < screenshots.length; i += batchSize) {
            if (!this.componentMounted) {
                // No need to go fetching for screenshots if the component is not mounted.
                continue;
            }
            const batch = screenshots.slice(i, i + batchSize);
            let result = await this.getVirtualDesktopClient().getSessionScreenshot({
                screenshots: batch,
            });
            if (result.success) {
                result.success.forEach((screenshot) => {
                    screenshotState[screenshot.dcv_session_id!] = {
                        data: screenshot.image_data!,
                        time: moment(),
                    };
                });
            }
            this.setState({
                screenshots: screenshotState,
            });
            if (i + batchSize < screenshots.length) {
                await delay(1000);
            }
        }
    }

    setSessions = (sessions: VirtualDesktopSession[] | undefined, os_filter: string | undefined = OS_FILTER_ALL_ID): Promise<boolean> => {
        if (sessions === undefined) {
            return new Promise((resolve) => {
                resolve(true);
            });
        }

        let currentSessionsInState = new Map<string, VirtualDesktopSession>(this.state.sessions.entries());
        let sessionsToShowInState = new Map<string, VirtualDesktopSession>();
        let sessionsThatMightHaveBeenTerminated = new Map<string, VirtualDesktopSession>(this.state.sessions.entries());
        sessions.forEach((session) => {
            // this session is definitely not terminated yet
            sessionsThatMightHaveBeenTerminated.delete(session.idea_session_id!);

            let currentSessionInState = currentSessionsInState.get(session.idea_session_id!);
            if (currentSessionInState === undefined) {
                // we have no such session in our list. This is new session. We should show it.
                sessionsToShowInState.set(session.idea_session_id!, session);
                return;
            }

            // we have a local copy of the said session. Should we replace/this session object ?
            if (currentSessionInState.updated_on === undefined || session.updated_on === undefined) {
                // we have no information about updated on for the session. Let's replace it. We can do better though.
                sessionsToShowInState.set(session.idea_session_id!, session);
                return;
            }

            if (currentSessionInState.updated_on <= session.updated_on) {
                // the local copy that we have is outdated. We need to replace
                sessionsToShowInState.set(session.idea_session_id!, session);
                return;
            }

            // the local copy is more recent. Need to use that
            sessionsToShowInState.set(session.idea_session_id!, currentSessionInState);
        });

        sessionsThatMightHaveBeenTerminated.forEach((session: VirtualDesktopSession, _: string) => {
            // this is a list of sessions that we suspect might have been terminated
            if (Utils.isNotEmpty(os_filter) && os_filter !== OS_FILTER_ALL_ID && session.base_os !== undefined) {
                // there is an OS filter that is applied.
                // Any session that doesn't match the OS filter in our local copy also needs to be hidden.
                let os_filters: VirtualDesktopBaseOS[] = ["windows"];

                if (os_filter === OS_FILTER_LINUX_ID) {
                    os_filters = ["amazonlinux2", "rhel8", "rhel9"];
                }

                if (!os_filters?.includes(session?.base_os)) {
                    // this session does not pass the OS filter.
                    return;
                }
            }
            if (!(session.state === "DELETED" || session.state === "DELETING")) {
                // this session was NOT on path to termination. So we can assume that it was NOT terminated.
                sessionsToShowInState.set(session.idea_session_id!, session);
            }
        });

        return new Promise<boolean>((resolve) => {
            this.setState(
                {
                    sessions: sessionsToShowInState,
                },
                () => {
                    resolve(true);
                }
            );
        });
    };

    setSession = (session: VirtualDesktopSession): Promise<boolean> => {
        return this.setSessions([session]);
    };

    onDeleteSession = (session: VirtualDesktopSession): Promise<boolean> => {
        return new Promise((resolve) => {
            this.setState(
                {
                    selectedSession: session,
                    confirmAction: {
                        actionTitle: "Terminate Virtual Desktop",
                        actionText: "Are you sure you want to terminate virtual desktop: " + session.name + "?",
                        onConfirm: () => {
                            this.getVirtualDesktopClient()
                                .deleteSessions({
                                    sessions: [
                                        {
                                            idea_session_id: this.state.selectedSession?.idea_session_id,
                                            dcv_session_id: this.state.selectedSession?.dcv_session_id,
                                            owner: AppContext.get().auth().getUsername(),
                                            project: {
                                              project_id: this.state.selectedSession?.project?.project_id,
                                            },
                                        },
                                    ],
                                })
                                .then((result) => {
                                    if (result.failed && result.failed.length > 0) {
                                        // we got failure. We should treat this as error.
                                        result.failed.forEach((entry) => {
                                            this.setState(
                                                {
                                                    selectedSession: entry,
                                                    activeConnectionConfirmModalOnConfirm: () => {
                                                        this.getVirtualDesktopClient()
                                                            .deleteSessions({
                                                                sessions: [
                                                                    {
                                                                        idea_session_id: this.state.selectedSession?.idea_session_id,
                                                                        dcv_session_id: this.state.selectedSession?.dcv_session_id,
                                                                        force: true,
                                                                    },
                                                                ],
                                                            })
                                                            .then((result) => {
                                                                if (result.failed && result.failed.length > 0) {
                                                                    //TODO: error. Maybe banner ??
                                                                }
                                                                this.setSessions(result.success).finally();
                                                            })
                                                            .catch((error) => {
                                                                console.error(error);
                                                            });
                                                    },
                                                },
                                                () => {
                                                    this.getActiveConnectionConfirmModal().show();
                                                }
                                            );
                                        });
                                    }
                                    this.setSessions(result.success).finally();
                                })
                                .catch((error) => {
                                    console.error(error);
                                });
                        },
                        onCancel: () => {
                            this.setState({
                                selectedSession: undefined,
                            });
                        },
                    },
                },
                () => {
                    this.getSessionActionConfirmModal().show();
                    resolve(true);
                }
            );
        });
    };

    onRebootSession = (session: VirtualDesktopSession): Promise<boolean> => {
        return new Promise<boolean>((resolve) => {
            this.setState(
                {
                    selectedSession: session,
                    confirmAction: {
                        actionTitle: "Reboot Virtual Desktop",
                        actionText: "Are you sure you want to reboot virtual desktop: " + session.name + "?",
                        onConfirm: () => {
                            this.getVirtualDesktopClient()
                                .rebootSessions({
                                    sessions: [
                                        {
                                            idea_session_id: this.state.selectedSession?.idea_session_id,
                                            dcv_session_id: this.state.selectedSession?.dcv_session_id,
                                        },
                                    ],
                                })
                                .then((result) => {
                                    if (result.failed && result.failed.length > 0) {
                                        // we got failure. We should treat this as error.
                                        result.failed.forEach((entry) => {
                                            this.setState(
                                                {
                                                    selectedSession: entry,
                                                    activeConnectionConfirmModalOnConfirm: () => {
                                                        this.getVirtualDesktopClient()
                                                            .rebootSessions({
                                                                sessions: [
                                                                    {
                                                                        idea_session_id: this.state.selectedSession?.idea_session_id,
                                                                        dcv_session_id: this.state.selectedSession?.dcv_session_id,
                                                                        force: true,
                                                                    },
                                                                ],
                                                            })
                                                            .then((result) => {
                                                                if (result.failed && result.failed.length > 0) {
                                                                    //TODO: error. Maybe banner ??
                                                                }
                                                                this.setSessions(result.success).finally();
                                                            })
                                                            .catch((error) => {
                                                                console.error(error);
                                                            });
                                                    },
                                                },
                                                () => {
                                                    this.getActiveConnectionConfirmModal().show();
                                                }
                                            );
                                        });
                                    }
                                    this.setSessions(result.success).finally();
                                });
                        },
                        onCancel: () => {
                            this.setState({
                                selectedSession: undefined,
                            });
                        },
                    },
                },
                () => {
                    this.getSessionActionConfirmModal().show();
                    resolve(true);
                }
            );
        });
    };

    onStopSession = (session: VirtualDesktopSession): Promise<boolean> => {
        let actionTitle = "Stop Virtual Desktop";
        let actionText = "Are you sure you want to stop virtual desktop: " + session.name + "?";
        if (session.hibernation_enabled) {
            actionTitle = "Hibernate Virtual Desktop";
            actionText = "Are you sure you want to hibernate virtual desktop: " + session.name + "?";
        }

        return new Promise((resolve) => {
            this.setState(
                {
                    selectedSession: session,
                    confirmAction: {
                        actionTitle: actionTitle,
                        actionText: actionText,
                        onConfirm: () => {
                            this.getVirtualDesktopClient()
                                .stopSessions({
                                    sessions: [
                                        {
                                            idea_session_id: this.state.selectedSession?.idea_session_id,
                                            dcv_session_id: this.state.selectedSession?.dcv_session_id,
                                        },
                                    ],
                                })
                                .then((result) => {
                                    if (result.failed && result.failed.length > 0) {
                                        // we got failure. We should treat this as error.
                                        result.failed.forEach((entry) => {
                                            this.setState(
                                                {
                                                    selectedSession: entry,
                                                    activeConnectionConfirmModalOnConfirm: () => {
                                                        this.getVirtualDesktopClient()
                                                            .stopSessions({
                                                                sessions: [
                                                                    {
                                                                        idea_session_id: this.state.selectedSession?.idea_session_id,
                                                                        dcv_session_id: this.state.selectedSession?.dcv_session_id,
                                                                        force: true,
                                                                    },
                                                                ],
                                                            })
                                                            .then((result) => {
                                                                if (result.failed && result.failed.length > 0) {
                                                                    //TODO: error. Maybe banner ??
                                                                }
                                                                this.setSessions(result.success).finally();
                                                            })
                                                            .catch((error) => {
                                                                console.error(error);
                                                            });
                                                    },
                                                },
                                                () => {
                                                    this.getActiveConnectionConfirmModal().show();
                                                }
                                            );
                                        });
                                    }
                                    this.setSessions(result.success).finally();
                                })
                                .catch((error) => {
                                    console.error(error);
                                });
                        },
                        onCancel: () => {
                            this.setState({
                                selectedSession: undefined,
                            });
                        },
                    },
                },
                () => {
                    this.getSessionActionConfirmModal().show();
                    resolve(true);
                }
            );
        });
    };

    onStartSession = (session: VirtualDesktopSession): Promise<boolean> => {
        return this.getVirtualDesktopClient()
            .resumeSessions({
                sessions: [
                    {
                        idea_session_id: session.idea_session_id,
                        dcv_session_id: session.dcv_session_id,
                    },
                ],
            })
            .then((result) => {
                if (result.failed && result.failed.length > 0) {
                    //TODO: error. Maybe banner ??
                }
                return this.setSessions(result.success);
            });
    };

    onDownloadDcvSessionFile = (session: VirtualDesktopSession): Promise<boolean> => {
        return this.getVirtualDesktopClient()
            .getSessionConnectionInfo({
                connection_info: {
                    idea_session_id: session.idea_session_id,
                    dcv_session_id: session.dcv_session_id,
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
                sessionFileContent += `sessionid=${session.dcv_session_id}\n`;
                sessionFileContent += `host=${url.host}\n`;
                sessionFileContent += `port=443\n`;
                sessionFileContent += `webport=443\n`;
                sessionFileContent += `quicport=443\n`;
                sessionFileContent += `certificatevalidationpolicy=accept-untrusted\n`;
                sessionFileContent += `authtoken=${result.connection_info?.access_token}\n`;

                const element = document.createElement("a");
                element.setAttribute("href", "data:text/plain;charset=utf-8," + encodeURIComponent(sessionFileContent));
                element.setAttribute("download", `${session.name}.dcv`);
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
                    this.setFlashMessage(`${session.name} - Error retrieving session connection information. Please reboot the Virtual Desktop and try again.`, "error");
                } else {
                    this.setFlashMessage(`Something went wrong. An error occured when attempting to download DCV file for session ${session.name}. See logs for more information.`, "error");
                }
                return false;
            });
    };

    onLaunchSession = (session: VirtualDesktopSession): Promise<boolean> => {
        return this.getVirtualDesktopClient()
            .getSessionConnectionInfo({
                connection_info: {
                    dcv_session_id: session.dcv_session_id,
                },
            })
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
                    this.setFlashMessage(`${session.name} - Error retrieving session connection information. Please reboot the Virtual Desktop and try again.`, "error");
                } else {
                    this.setFlashMessage(`Something went wrong. An error occured when attempting to connect to session ${session.name}. See logs for more information.`, "error");
                }
                return false;
            });
    };

    onShareSession = (session: VirtualDesktopSession): Promise<boolean> => {
        this.setState(
            {
                selectedSession: session,
            },
            () => {
                this.showUpdateSessionPermissionForm();
            }
        );

        return Promise.resolve(true);
    };

    onShowSchedule = (session: VirtualDesktopSession): Promise<boolean> => {
        this.getScheduleModal().showSchedule(session);
        return Promise.resolve(true);
    };

    showUpdateSessionForm() {
        this.setState(
            {
                showUpdateSessionForm: true,
            },
            () => {
                this.getUpdateSessionForm().showModal();
            }
        );
    }

    showCreateSessionForm() {
        if (!this.isAdmin() && this.state.userProjects.length === 0) {
            // we don't have permissions to create our own sessions
            return;
        }
        this.setState(
            {
                showCreateSessionForm: true,
            },
            () => {
                this.getCreateSessionForm().showModal();
            }
        );
    }

    showUpdateSessionPermissionForm() {
        this.setState(
            {
                showUpdateSessionPermissionForm: true,
            },
            () => {
                this.getUpdateSessionPermissionForm()?.showModal();
            }
        );
    }

    hideUpdateSessionPermissionForm() {
        this.setState({
            showUpdateSessionPermissionForm: false,
        });
    }

    hideCreateSessionForm() {
        this.setState({
            showCreateSessionForm: false,
        });
    }

    hideUpdateSessionForm() {
        this.setState({
            showUpdateSessionForm: false,
        });
    }

    buildUpdateSessionForm() {
        return (
            <IdeaForm
                ref={this.updateSessionForm}
                name={"update-session"}
                modal={true}
                title={"Update Session Details for " + this.state.selectedSession?.name}
                modalSize={"medium"}
                onCancel={() => {
                    this.hideUpdateSessionForm();
                }}
                onSubmit={() => {
                    this.getUpdateSessionForm().clearError();
                    if (!this.getUpdateSessionForm().validate()) {
                        return;
                    }

                    if (this.state.selectedSession === undefined || this.state.selectedSession?.server === undefined) {
                        return;
                    }

                    const values = this.getUpdateSessionForm().getValues();
                    let session: VirtualDesktopSession = {
                        idea_session_id: this.state.selectedSession.idea_session_id,
                        owner: this.state.selectedSession.owner,
                        name: values.session_name,
                        server: {
                            instance_id: this.state.selectedSession.server.instance_id,
                            instance_type: values.instance_type,
                        },
                    };
                    return this.getVirtualDesktopClient()
                        .updateSession({
                            session: session,
                        })
                        .then((result) => {
                            this.hideUpdateSessionForm();
                            return this.setSession(result.session!);
                        })
                        .catch((error) => {
                            this.getUpdateSessionForm().setError(error.errorCode, error.message);
                            return false;
                        });
                }}
                params={[
                    {
                        name: "session_name",
                        title: "Session Name",
                        description: "Enter a name for the virtual desktop",
                        data_type: "str",
                        param_type: "text",
                        help_text: "Session Name is required. Use any characters and form a name of length between 3 and 24 characters, inclusive.",
                        default: this.state.selectedSession?.name,
                        validate: {
                            required: true,
                            regex: "^.{3,24}$",
                            message: "Use any characters and form a name of length between 3 and 24 characters, inclusive.",
                        },
                    },
                    {
                        name: "instance_type",
                        title: "Virtual Desktop Size",
                        description: "Select a virtual desktop instance type",
                        help_text: this.state.selectedSession?.hibernation_enabled ? "You can not update Virtual Desktop Size because Hibernation is enabled for this machine." : "",
                        data_type: "str",
                        readonly: this.state.selectedSession?.hibernation_enabled,
                        default: this.state.selectedSession?.server?.instance_type,
                        param_type: "select_or_text",
                        validate: {
                            required: true,
                        },
                        choices: this.state.selectedSessionApplicableInstanceTypes,
                    },
                ]}
            />
        );
    }

    buildUpdateSessionPermissionForm() {
        return (
            <UpdateSessionPermissionModal
                ref={this.updateSessionPermissionForm}
                modalSize={"large"}
                onCancel={() => {
                    this.hideUpdateSessionPermissionForm();
                }}
                onSubmit={(createdPermissions: VirtualDesktopSessionPermission[], updatedPermissions: VirtualDesktopSessionPermission[], deletedPermissions: VirtualDesktopSessionPermission[]) => {
                    return this.getVirtualDesktopClient()
                        .updateSessionPermissions({
                            create: createdPermissions,
                            update: updatedPermissions,
                            delete: deletedPermissions,
                        })
                        .then((_) => {
                            this.getUpdateSessionPermissionForm().hideModal();
                            this.setState({
                                showUpdateSessionPermissionForm: false,
                            });
                            return Promise.resolve(true);
                        })
                        .catch((error) => {
                            this.getUpdateSessionPermissionForm()?.setError(error.errorCode, error.message);
                            return Promise.resolve(false);
                        });
                }}
                session={this.state.selectedSession!}
            />
        );
    }

    buildCreateSessionForm() {
        return (
            <VirtualDesktopCreateSessionForm
                ref={this.createSessionForm}
                defaultName={`MyDesktop${this.state.sessions.size + 1}`}
                maxRootVolumeMemory={this.virtualDesktopSettings?.dcv_session.max_root_volume_memory}
                userProjects={this.state.userProjects}
                onSubmit={(session_name, username, project_id, base_os, software_stack_id, session_type, instance_type, storage_size, hibernation_enabled, vpc_subnet_id, tags) => {
                    return this.getVirtualDesktopClient()
                        .createSession({
                            session: {
                                name: session_name,
                                owner: username,
                                hibernation_enabled: hibernation_enabled,
                                software_stack: {
                                    stack_id: software_stack_id,
                                    base_os: base_os,
                                },
                                server: {
                                    instance_type: instance_type,
                                    root_volume_size: {
                                        value: storage_size,
                                        unit: "gb",
                                    },
                                    subnet_id: vpc_subnet_id,
                                },
                                project: {
                                    project_id: project_id,
                                },
                                type: session_type,
                                tags: tags,
                            },
                        })
                        .then((result) => {
                            this.getCreateSessionForm().hideForm();
                            this.setSession(result.session!).finally();
                            return Promise.resolve(true);
                        })
                        .catch((error) => {
                            this.getCreateSessionForm()?.setError(error.errorCode, error.message);
                            return Promise.resolve(false);
                        });
                }}
                onDismiss={() => {
                    this.hideCreateSessionForm();
                }}
            />
        );
    }

    buildActiveConnectionConfirmModal() {
        return (
            <IdeaConfirm
                ref={this.activeConnectionConfirmModal}
                title="Active connections exist!"
                onConfirm={this.state.activeConnectionConfirmModalOnConfirm}
                onCancel={() => {
                    this.setState({
                        selectedSession: undefined,
                    });
                }}
            >
                There exists {this.state.selectedSession?.connection_count} active connection(s). Are you sure you want to continue?
            </IdeaConfirm>
        );
    }

    buildSessionActionConfirmModal() {
        return (
            <IdeaConfirm ref={this.sessionActionConfirmModal} title={this.state.confirmAction.actionTitle} onConfirm={this.state.confirmAction.onConfirm} onCancel={this.state.confirmAction.onCancel}>
                {this.state.confirmAction.actionText}
            </IdeaConfirm>
        );
    }

    buildDcvClientHelpModal() {
        return (
            this.state.selectedSession && (
                <DcvClientHelpModal
                    session={this.state.selectedSession}
                    onDismiss={() => {
                        this.setState({
                            showDcvClientHelpModal: false,
                            selectedSession: undefined,
                        });
                    }}
                    onDownloadDcvSessionFile={this.onDownloadDcvSessionFile}
                    onLaunchSession={this.onLaunchSession}
                    visible={this.state.showDcvClientHelpModal}
                />
            )
        );
    }

    buildScheduleModal() {
        return (
            <VirtualDesktopScheduleModal
                ref={this.scheduleModal}
                onScheduleChange={(session) => {
                    return this.getVirtualDesktopClient()
                        .updateSession({
                            session: session,
                        })
                        .then((response) => {
                            return this.setSession(response.session!);
                        })
                        .catch((error) => {
                            this.getScheduleModal().setErrorMessage(error.message);
                            return false;
                        });
                }}
            />
        );
    }

    isActiveDirectory(): boolean {
        return this.state.directoryServiceProvider === "activedirectory" || this.state.directoryServiceProvider === "aws_managed_activedirectory";
    }

    refreshSessions(): void {
        this.setState(
            {
                loading: true,
            },
            () => {
                this.fetchSessions().then(() => {
                    this.lastRefreshTime = new Date();
                    this.setState({
                        loading: false,
                        lastRefreshTimeInSec: 0,
                    });
                    this.fetchSessionScreenshots().finally();
                });
            }
        );
    }

    formatTimeDisplay(lastRefreshTimeInSec: number): string {
        if (lastRefreshTimeInSec <= 60) {
            return "Last refreshed less than a minute ago";
        } else if (lastRefreshTimeInSec <= 60 * 60) {
            return `Last refreshed ${Math.floor(lastRefreshTimeInSec / 60)} minutes ago`;
        } else {
            return `Last refreshed ${Math.floor(lastRefreshTimeInSec / 60 / 60)} hour(s) ago`;
        }
    }

    buildListing() {
        const getSessions = (): VirtualDesktopSession[] => {
            let sessions: VirtualDesktopSession[] = [];
            this.state.sessions.forEach((session) => sessions.push(session));
            sessions.sort((session_a, session_b) => {
                if (session_a.created_on === undefined && session_b.created_on === undefined) {
                    return 0;
                }

                if (session_a.created_on === undefined) {
                    return -1;
                }

                if (session_b.created_on === undefined) {
                    return 1;
                }

                return session_a.created_on > session_b.created_on ? 1 : -1;
            });
            return sessions;
        };

        return (
            <Cards
                stickyHeader={true}
                header={
                    <Header
                        variant="awsui-h1-sticky"
                        actions={
                            <SpaceBetween direction="horizontal" size="l">
                                <Toggle
                                    description={this.formatTimeDisplay(this.state.lastRefreshTimeInSec)}
                                    checked={this.state.autoRefreshIntervalId !== undefined}
                                    onChange={(changeEvent) => {
                                        let intervalId: NodeJS.Timer | undefined = undefined;
                                        if (changeEvent.detail.checked) {
                                            intervalId = setInterval(() => this.refreshSessions(), AUTO_REFRESH_TIME_IN_MS);
                                        } else {
                                            clearInterval(this.state.autoRefreshIntervalId);
                                        }
                                        this.setState({
                                            autoRefreshIntervalId: intervalId,
                                        });
                                    }}
                                >
                                    Auto-refresh
                                </Toggle>
                                <Button
                                    variant="normal"
                                    iconName="refresh"
                                    onClick={() => {
                                        this.refreshSessions();
                                    }}
                                />
                                <SegmentedControl
                                    selectedId={this.state.osFilter}
                                    onChange={({ detail }) => {
                                        this.setState(
                                            {
                                                osFilter: detail.selectedId,
                                            },
                                            () => {
                                                this.fetchSessions().finally();
                                            }
                                        );
                                    }}
                                    options={[
                                        { text: "All", id: OS_FILTER_ALL_ID },
                                        { text: "Windows", id: OS_FILTER_WINDOWS_ID },
                                        { text: "Linux", id: OS_FILTER_LINUX_ID },
                                    ]}
                                />
                                <Button
                                    key="launch-new-virtual-desktop"
                                    variant="primary"
                                    disabled={!this.canCreateSession()}
                                    onClick={() => {
                                        this.showCreateSessionForm();
                                    }}
                                >
                                    Launch New Virtual Desktop
                                </Button>
                            </SpaceBetween>
                        }
                    >
                        Virtual Desktops
                    </Header>
                }
                trackBy="idea_session_id"
                ariaLabels={{
                    itemSelectionLabel: (e, t) => `select ${t.name}`,
                    selectionGroupLabel: "Item selection",
                }}
                loading={this.state.loading}
                loadingText="Retrieving your virtual desktops ..."
                variant="full-page"
                cardDefinition={{
                    sections: [
                        {
                            id: "card",
                            content: (session: VirtualDesktopSession) => {
                                return (
                                    <VirtualDesktopSessionCard
                                        isActiveDirectory={this.isActiveDirectory()}
                                        virtualDesktopClient={this.getVirtualDesktopClient()}
                                        session={session}
                                        onDeleteSession={this.onDeleteSession}
                                        onStartSession={this.onStartSession}
                                        onStopSession={this.onStopSession}
                                        onRebootSession={this.onRebootSession}
                                        onDownloadDcvSessionFile={this.onDownloadDcvSessionFile}
                                        onLaunchSession={this.onLaunchSession}
                                        onShowSchedule={this.onShowSchedule}
                                        onUpdateSessionPermission={this.onShareSession}
                                        onUpdateSession={(session) => {
                                            return new Promise<boolean>((resolve) =>
                                                this.getVirtualDesktopUtilsClient()
                                                    .listAllowedInstanceTypesForSession({
                                                        session: session,
                                                    })
                                                    .then((result) => {
                                                        this.setState(
                                                            {
                                                                selectedSession: session,
                                                                selectedSessionApplicableInstanceTypes: Utils.generateInstanceTypeListing(result.listing),
                                                            },
                                                            () => {
                                                                this.showUpdateSessionForm();
                                                                resolve(true);
                                                            }
                                                        );
                                                    })
                                            );
                                        }}
                                        onConnectHelp={(session) => {
                                            return new Promise<boolean>((resolve) => {
                                                this.setState(
                                                    {
                                                        showDcvClientHelpModal: true,
                                                        selectedSession: session,
                                                    },
                                                    () => {
                                                        resolve(true);
                                                    }
                                                );
                                            });
                                        }}
                                        onMounted={() => {
                                            let header = document.getElementsByClassName(CARD_HEADER_CLASS_NAME);
                                            for (let i = 0; i < header.length; i++) {
                                                header[i].setAttribute("style", "display: none;");
                                            }
                                        }}
                                        screenshot={this.state.screenshots[session?.dcv_session_id!]?.data}
                                    />
                                );
                            },
                        },
                    ],
                }}
                cardsPerRow={[
                    {
                        cards: 1,
                    },
                    {
                        minWidth: 800,
                        cards: 2,
                    },
                    {
                        minWidth: 1400,
                        cards: 3,
                    },
                    {
                        minWidth: 1920,
                        cards: 4,
                    },
                ]}
                empty={
                    <Box textAlign="center" color="inherit" padding={{ top: "xxxl", bottom: "s" }}>
                        <b>No virtual desktops found.</b>
                        <Box padding={{ top: "xxxl", bottom: "s" }} variant="p" color="inherit">
                            Click the button below to create a new virtual desktop.
                        </Box>
                        <Button disabled={!this.canCreateSession()} onClick={() => this.showCreateSessionForm()}>Launch New Virtual Desktop</Button>
                    </Box>
                }
                items={getSessions()}
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
                        text: "Virtual Desktops",
                        href: "",
                    },
                ]}
                contentType={"cards"}
                content={
                    <div>
                        {this.buildListing()}
                        {this.state.showCreateSessionForm && this.buildCreateSessionForm()}
                        {this.state.showUpdateSessionForm && this.buildUpdateSessionForm()}
                        {this.state.showUpdateSessionPermissionForm && this.buildUpdateSessionPermissionForm()}
                        {this.buildSessionActionConfirmModal()}
                        {this.buildActiveConnectionConfirmModal()}
                        {this.buildDcvClientHelpModal()}
                        {this.buildScheduleModal()}
                    </div>
                }
            />
        );
    }
}

export default withRouter(MyVirtualDesktopSessions);
