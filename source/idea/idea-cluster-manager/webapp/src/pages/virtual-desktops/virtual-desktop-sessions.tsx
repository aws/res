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
import { TableProps } from "@cloudscape-design/components/table/interfaces";
import { Link } from "@cloudscape-design/components";
import { Project, SocaUserInputChoice, VirtualDesktopSession, VirtualDesktopSessionBatchResponsePayload } from "../../client/data-model";
import IdeaListView from "../../components/list-view";
import { AppContext } from "../../common";
import { ProjectsClient, VirtualDesktopAdminClient, VirtualDesktopClient } from "../../client";
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import IdeaConfirm from "../../components/modals";
import ReactJson from "react-json-view";
import IdeaView from "../../components/modals/view";
import { IdeaAppLayoutProps } from "../../components/app-layout";
import IdeaForm from "../../components/form";
import IdeaAppLayout from "../../components/app-layout/app-layout";
import VirtualDesktopSessionStatusIndicator from "./components/virtual-desktop-session-status-indicator";
import Utils from "../../common/utils";
import { FlashbarProps } from "@cloudscape-design/components/flashbar/interfaces";
import VirtualDesktopCreateSessionForm from "./forms/virtual-desktop-create-session-form";
import { withRouter } from "../../navigation/navigation-utils";
import VirtualDesktopDCVClient from "../../client/virtual-desktop-dcv-client";

export interface VirtualDesktopSessionsProps extends IdeaAppLayoutProps, IdeaSideNavigationProps { }

export interface VirtualDesktopSessionsState {
    showCreateSoftwareStackFromSessionForm: boolean;
    sessionForSoftwareStack: VirtualDesktopSession | undefined;
    projectChoices: SocaUserInputChoice[];
    sessionSelected: boolean;
    forceStop: boolean;
    forceTerminate: boolean;
    sessionHealth: any;
    showCreateSessionForm: boolean;
    projects: Project[] | undefined;
}

const VIRTUAL_DESKTOP_SESSIONS_TABLE_COLUMN_DEFINITIONS: TableProps.ColumnDefinition<VirtualDesktopSession>[] = [
    {
        id: "name",
        header: "Session Name",
        cell: (e) => <Link href={`/#/virtual-desktop/sessions/${e.idea_session_id}?owner=${e.owner}`}>{e.name}</Link>,
        sortingField: "name",
    },
    {
        id: "owner",
        header: "Owner",
        cell: (e) => e.owner,
        sortingField: "owner",
    },
    {
        id: "os",
        header: "Base OS",
        cell: (e) => Utils.getOsTitle(e.software_stack?.base_os),
    },
    {
        id: "instance_type",
        header: "Instance Type",
        cell: (e) => e.server?.instance_type,
    },
    {
        id: "state",
        header: "State",
        cell: (e) => {
            return <VirtualDesktopSessionStatusIndicator state={e.state!} hibernation_enabled={e.hibernation_enabled!} />;
        },
    },
    {
        id: "project_title",
        header: "Project",
        cell: (e) => e.project?.title,
    },
    {
        id: "created_on",
        header: "Created On",
        cell: (e) => new Date(e.created_on!).toLocaleString(),
    },
    {
        id: "connect-session",
        header: "Join Session",
        cell: (e) => {
            if (e.state === "READY") {
                let username: string | undefined = undefined;
                if (e.software_stack?.base_os === "windows") {
                    username = "administrator";
                }

                return (
                    <Link external>
                        <span
                            onClick={() => {
                                AppContext.get().client().virtualDesktopAdmin().joinSession(e.idea_session_id!, e.owner!, username).finally();
                            }}
                        >
                            Connect
                        </span>
                    </Link>
                );
            }
        },
    },
    {
        id: "updated_on",
        header: "Updated On",
        cell: (e) => new Date(e.updated_on!).toLocaleString(),
    },
];

const PREFERENCES_KEY = "user-sessions";

class VirtualDesktopSessions extends Component<VirtualDesktopSessionsProps, VirtualDesktopSessionsState> {
    listing: RefObject<IdeaListView>;
    deleteSessionsConfirmModal: RefObject<IdeaConfirm>;
    stopSessionsConfirmModal: RefObject<IdeaConfirm>;
    resumeSessionsConfirmModal: RefObject<IdeaConfirm>;
    sessionHealthModal: RefObject<IdeaView>;
    createSoftwareStackForm: RefObject<IdeaForm>;
    createSessionForm: RefObject<VirtualDesktopCreateSessionForm>;
    virtualDesktopSettings: any;

    constructor(props: VirtualDesktopSessionsProps) {
        super(props);
        this.listing = React.createRef();
        this.deleteSessionsConfirmModal = React.createRef();
        this.stopSessionsConfirmModal = React.createRef();
        this.resumeSessionsConfirmModal = React.createRef();
        this.sessionHealthModal = React.createRef();
        this.createSoftwareStackForm = React.createRef();
        this.createSessionForm = React.createRef();
        this.virtualDesktopSettings = undefined;

        this.state = {
            showCreateSoftwareStackFromSessionForm: false,
            sessionForSoftwareStack: undefined,
            sessionSelected: false,
            forceStop: false,
            projectChoices: [],
            forceTerminate: false,
            sessionHealth: {},
            showCreateSessionForm: false,
            projects: [],
        };

        // Hide the Join Session button since it does not work consistently
        this.setHiddenColumns();
    }

    componentDidMount() {
        Utils.fetchProjectsFilteredByVDIPermissions(this.isAdmin(), "create_terminate_others_sessions")
            .then((result) => {
                let projectChoices: SocaUserInputChoice[] = [];
                result.forEach((project) => {
                    projectChoices.push({
                        title: project.title,
                        value: project.project_id,
                        description: project.description,
                    });
                });
                this.setState(
                    {
                        projectChoices: projectChoices,
                        projects: result,
                    }
                );
            });

        AppContext.get()
            .getClusterSettingsService()
            .getVirtualDesktopSettings()
            .then((settings) => {
                this.virtualDesktopSettings = settings;
            });
    }

    setHiddenColumns(): void {
        AppContext.get().localStorage().setItem(`${PREFERENCES_KEY}-table-columns`, '{"connect-session": false}');
    }

    getProjectsClient(): ProjectsClient {
        return AppContext.get().client().projects();
    }

    getListing(): IdeaListView {
        return this.listing.current!;
    }

    canCreateSoftwareStack(): boolean {
        return this.getSelectedSessions().length === 1;
    }

    isSelected(): boolean {
        return this.state.sessionSelected;
    }

    getVirtualDCVClient(): VirtualDesktopDCVClient {
        return AppContext.get().client().virtualDesktopDCV();
    }

    getVirtualDesktopAdminClient(): VirtualDesktopAdminClient {
        return AppContext.get().client().virtualDesktopAdmin();
    }

    getVirtualDesktopClient(): VirtualDesktopClient {
        return AppContext.get().client().virtualDesktop();
    }

    getSelectedSessions(): VirtualDesktopSession[] {
        if (this.getListing() == null) {
            return [];
        }
        return this.getListing().getSelectedItems();
    }

    getTerminateSessionsConfirmModal(): IdeaConfirm {
        return this.deleteSessionsConfirmModal.current!;
    }

    getResumeSessionsConfirmModal(): IdeaConfirm {
        return this.resumeSessionsConfirmModal.current!;
    }

    getStopSessionsConfirmModal(): IdeaConfirm {
        return this.stopSessionsConfirmModal.current!;
    }

    getSessionHealthModal(): IdeaView {
        return this.sessionHealthModal.current!;
    }

    isAdmin(): boolean {
        return AppContext.get().auth().isAdmin();
    }

    hideCreateSoftwareStackForm() {
        this.setState({
            sessionForSoftwareStack: undefined,
            showCreateSoftwareStackFromSessionForm: false,
        });
    }

    showCreateSoftwareStackForm = (session: VirtualDesktopSession) => {
        this.setState(
            {
                sessionForSoftwareStack: session,
                showCreateSoftwareStackFromSessionForm: true,
            },
            () => {
                this.getCreateSoftwareStackForm().showModal();
            }
        );
    };

    buildCreateSoftwareStackFromSessionForm() {
        return (
            <IdeaForm
                ref={this.createSoftwareStackForm}
                name={"create-software-stack"}
                modal={true}
                title={"Create Software Stack for " + this.state.sessionForSoftwareStack?.name}
                modalSize={"medium"}
                onCancel={() => {
                    this.hideCreateSoftwareStackForm();
                }}
                onSubmit={() => {
                    this.getCreateSoftwareStackForm().clearError();
                    if (!this.getCreateSoftwareStackForm().validate()) {
                        return;
                    }
                    const values = this.getCreateSoftwareStackForm().getValues();

                    var projectValues: any[] = [];

                    values.projects.forEach((project: string) => {
                        projectValues.push({ project_id: project });
                    });

                    this.getVirtualDesktopAdminClient()
                        .createSoftwareStackFromSession({
                            session: this.state.sessionForSoftwareStack,
                            new_software_stack: {
                                name: values.name,
                                description: values.description,
                                min_storage: {
                                    value: values.root_storage_size,
                                    unit: "gb",
                                },
                                projects: projectValues,
                            },
                        })
                        .then(() => {
                            this.hideCreateSoftwareStackForm();
                        })
                        .catch((error) => {
                            this.getCreateSoftwareStackForm().setError(error.errorCode, error.message);
                        });
                }}
                params={[
                    {
                        name: "name",
                        title: "Name",
                        description: "Enter a name for the software stack",
                        data_type: "str",
                        param_type: "text",
                        validate: {
                            required: true,
                        },
                    },
                    {
                        name: "description",
                        title: "Description",
                        description: "Enter a user friendly description for the software stack",
                        data_type: "str",
                        param_type: "text",
                        validate: {
                            required: true,
                        },
                    },
                    {
                        name: "root_storage_size",
                        title: "Storage Size (GB)",
                        description: "Enter the storage size for your virtual desktop in GBs",
                        data_type: "int",
                        param_type: "text",
                        default: 10,
                        validate: {
                            required: true,
                        },
                    },
                    {
                        name: "projects",
                        title: "Projects",
                        description: "Select applicable projects for the software stack",
                        data_type: "str",
                        param_type: "select",
                        multiple: true,
                        default: [this.state.sessionForSoftwareStack?.project?.project_id],
                        choices: this.state.projectChoices,
                        validate: {
                            required: true,
                        },
                    },
                ]}
            />
        );
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

    displayFlashResponseBanner(result: VirtualDesktopSessionBatchResponsePayload, success_message: string, error_message: string) {
        let items: FlashbarProps.MessageDefinition[] = [];
        if (result.failed && result.failed.length > 0) {
            items.push({
                content: this.buildResponseBanner(result?.failed, error_message),
                type: "error",
                dismissible: true,
            });
        }

        if (result.success && result.success.length > 0) {
            items.push({
                content: this.buildResponseBanner(result?.success, success_message),
                type: "success",
                dismissible: true,
            });
        }

        this.props.onFlashbarChange({
            items: items,
        });
    }

    buildResponseBanner(sessions: VirtualDesktopSession[], message_string: string) {
        return (
            <div>
                {sessions.map((session, index) => {
                    if (session.failure_reason) {
                        return (
                            <p key={index}>
                                RES Session Id: {session?.idea_session_id}, Owner: {session.owner} - {message_string}: {session.failure_reason}
                            </p>
                        );
                    } else {
                        return (
                            <p key={index}>
                                RES Session Id: {session?.idea_session_id}, Owner: {session.owner} - {message_string}
                            </p>
                        );
                    }
                })}
            </div>
        );
    }

    buildResumeSessionsConfirmModal() {
        return (
            <IdeaConfirm
                ref={this.resumeSessionsConfirmModal}
                title={"Resume Session(s)"}
                onConfirm={() => {
                    const toResume: VirtualDesktopSession[] = [];
                    this.getSelectedSessions().forEach((session) =>
                        toResume.push({
                            idea_session_id: session.idea_session_id,
                            dcv_session_id: session.dcv_session_id,
                            owner: session.owner,
                        })
                    );
                    this.getVirtualDesktopAdminClient()
                        .resumeSessions({
                            sessions: toResume,
                        })
                        .then(
                            (result) => {
                                this.setState(
                                    {
                                        sessionSelected: false,
                                    },
                                    () => {
                                        this.displayFlashResponseBanner(result, "Request Submitted", "Error");
                                        this.getListing().fetchRecords();
                                    }
                                );
                            },
                            (error) => {
                                this.setFlashMessage(error.message, "error");
                            }
                        );
                }}
            >
                <p>Are you sure you want to resume below sessions:</p>
                {this.getSelectedSessions().map((session, index) => {
                    return (
                        <li key={index}>
                            {session.name} (Owner: {session.owner})
                        </li>
                    );
                })}
            </IdeaConfirm>
        );
    }

    buildDeleteSessionsConfirmModal() {
        return (
            <IdeaConfirm
                ref={this.deleteSessionsConfirmModal}
                title={this.state.forceTerminate ? "Force Delete Sessions" : "Delete Sessions"}
                onConfirm={() => {
                    const toDelete: VirtualDesktopSession[] = [];
                    this.getSelectedSessions().forEach((session) =>
                        toDelete.push({
                            idea_session_id: session.idea_session_id,
                            dcv_session_id: session.dcv_session_id,
                            project: {
                              project_id: session.project?.project_id,
                            },
                            owner: session.owner,
                            force: this.state.forceTerminate,
                        })
                    );
                    (this.isAdmin() ? this.getVirtualDesktopAdminClient() : this.getVirtualDesktopClient())
                        .deleteSessions({
                            sessions: toDelete,
                        })
                        .then(
                            (result) => {
                                this.setState(
                                    {
                                        sessionSelected: false,
                                    },
                                    () => {
                                        this.displayFlashResponseBanner(result, "Request Submitted", "Error");
                                        this.getListing().fetchRecords();
                                    }
                                );
                            },
                            (error) => {
                                this.setFlashMessage(error.message, "error");
                            }
                        );
                }}
            >
                <p>Are you sure you want to delete below sessions:</p>
                {this.getSelectedSessions().map((session, index) => {
                    return (
                        <li key={index}>
                            {session.name} (Owner: {session.owner})
                        </li>
                    );
                })}
            </IdeaConfirm>
        );
    }

    getCreateSoftwareStackForm(): IdeaForm {
        return this.createSoftwareStackForm.current!;
    }

    buildSessionHealthModal() {
        return (
            <IdeaView
                ref={this.sessionHealthModal}
                title={"Sessions Health"}
                acknowledgeVariant={"primary"}
                onAcknowledge={() =>
                    this.setState({
                        sessionHealth: {},
                    })
                }
            >
                <ReactJson defaultValue="" enableClipboard={false} name={false} src={this.state.sessionHealth} displayDataTypes={false} iconStyle={"circle"} onEdit={false} theme="grayscale:inverted" collapseStringsAfterLength={45} />
            </IdeaView>
        );
    }

    buildStopSessionsConfirmModal() {
        return (
            <IdeaConfirm
                ref={this.stopSessionsConfirmModal}
                title={this.state.forceStop ? "Force Stop/Hibernate Sessions" : "Stop/Hibernate Sessions"}
                onConfirm={() => {
                    const toStop: VirtualDesktopSession[] = [];
                    this.getSelectedSessions().forEach((session) =>
                        toStop.push({
                            idea_session_id: session.idea_session_id,
                            dcv_session_id: session.dcv_session_id,
                            owner: session.owner,
                            force: this.state.forceStop,
                        })
                    );
                    this.getVirtualDesktopAdminClient()
                        .stopSessions({
                            sessions: toStop,
                        })
                        .then(
                            (result) => {
                                this.setState(
                                    {
                                        sessionSelected: false,
                                    },
                                    () => {
                                        this.displayFlashResponseBanner(result, "Request Submitted", "Error");
                                        this.getListing().fetchRecords();
                                    }
                                );
                            },
                            (error) => {
                                this.setFlashMessage(error.message, "error");
                            }
                        );
                }}
            >
                <p>Are you sure you want to stop/hibernate below sessions:</p>
                {this.getSelectedSessions().map((session, index) => {
                    return (
                        <li key={index}>
                            {session.name} (Owner: {session.owner})
                        </li>
                    );
                })}
            </IdeaConfirm>
        );
    }

    showCreateSessionForm() {
        this.setState(
            {
                showCreateSessionForm: true,
            },
            () => {
                this.getCreateSessionForm().showModal();
            }
        );
    }

    getCreateSessionForm(): VirtualDesktopCreateSessionForm {
        return this.createSessionForm.current!;
    }

    hideCreateSessionForm() {
        this.setState({
            showCreateSessionForm: false,
        });
    }

    buildCreateSessionForm() {
        return (
            <VirtualDesktopCreateSessionForm
                ref={this.createSessionForm}
                maxRootVolumeMemory={this.virtualDesktopSettings?.dcv_session.max_root_volume_memory}
                isAdminView={true}
                userProjects={this.state.projects}
                onSubmit={(session_name, username, project_id, base_os, software_stack_id, session_type, instance_type, storage_size, hibernation_enabled, vpc_subnet_id, tags) => {
                    return (this.isAdmin() ? this.getVirtualDesktopAdminClient() : this.getVirtualDesktopClient())
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
                                tags: tags
                            },
                        })
                        .then((_) => {
                            this.getCreateSessionForm().hideForm();
                            this.getListing().fetchRecords();
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

    buildListing() {
        return (
            <IdeaListView
                ref={this.listing}
                title="Sessions"
                showPreferences={true}
                preferencesKey={PREFERENCES_KEY}
                description="Virtual Desktop sessions for all users. End-users see these sessions as Virtual Desktops."
                selectionType="multi"
                primaryAction={{
                    id: "create-session",
                    text: "Create Session",
                    onClick: () => {
                        this.showCreateSessionForm();
                    },
                }}
                secondaryActionsDisabled={!this.isSelected()}
                secondaryActions={[
                    {
                        id: "resume-session",
                        text: "Resume Session(s)",
                        disabled: !this.isSelected() || !this.isAdmin(),
                        onClick: () => {
                            this.setState(
                                {
                                    forceStop: true,
                                },
                                () => {
                                    this.getResumeSessionsConfirmModal().show();
                                }
                            );
                        },
                    },
                    {
                        id: "stop-session",
                        text: "Stop/Hibernate Session(s)",
                        disabled: !this.isSelected() || !this.isAdmin(),
                        onClick: () => {
                            this.setState(
                                {
                                    forceStop: true,
                                },
                                () => {
                                    this.getStopSessionsConfirmModal().show();
                                }
                            );
                        },
                    },
                    {
                        id: "force-stop-session",
                        text: "Force Stop/Hibernate Session(s)",
                        disabled: !this.isSelected() || !this.isAdmin(),
                        onClick: () => {
                            this.setState(
                                {
                                    forceStop: true,
                                },
                                () => {
                                    this.getStopSessionsConfirmModal().show();
                                }
                            );
                        },
                    },
                    {
                        id: "terminate-session",
                        text: "Terminate Session(s)",
                        disabled: !this.isSelected(),
                        onClick: () => {
                            this.setState(
                                {
                                    forceTerminate: false,
                                },
                                () => {
                                    this.getTerminateSessionsConfirmModal().show();
                                }
                            );
                        },
                    },
                    {
                        id: "force-terminate-session",
                        text: "Force Terminate Session(s)",
                        disabled: !this.isSelected(),
                        onClick: () => {
                            this.setState(
                                {
                                    forceTerminate: true,
                                },
                                () => {
                                    this.getTerminateSessionsConfirmModal().show();
                                }
                            );
                        },
                    },
                    {
                        id: "get-session-health",
                        text: "Session(s) Health",
                        disabled: !this.isSelected() || !this.isAdmin(),
                        onClick: () => {
                            let sessions: VirtualDesktopSession[] = [];
                            this.getSelectedSessions().forEach((session) => {
                                sessions.push({
                                    idea_session_id: session.idea_session_id,
                                    dcv_session_id: session.dcv_session_id,
                                });
                            });

                            this.getVirtualDCVClient()
                                .describeSessions({
                                    sessions: sessions,
                                })
                                .then((response) => {
                                    let health = response.response;
                                    delete health?.request_id;
                                    delete health?.next_token;
                                    this.setState(
                                        {
                                            sessionHealth: health?.sessions,
                                        },
                                        () => {
                                            this.getSessionHealthModal().show();
                                        }
                                    );
                                });
                        },
                    },
                    {
                        id: "create-software-stack",
                        text: "Create Software Stack",
                        disabled: !this.canCreateSoftwareStack() || !this.isAdmin(),
                        disabledReason: "Select exactly 1 session to enable this Action",
                        onClick: () => {
                            // we know that there is exactly 1 session
                            this.getSelectedSessions().forEach((session) => {
                                this.showCreateSoftwareStackForm(session);
                            });
                        },
                    },
                ]}
                showPaginator={true}
                onRefresh={() => {
                    this.setState(
                        {
                            sessionSelected: false,
                        },
                        () => {
                            this.getListing().fetchRecords();
                        }
                    );
                }}
                showDateRange={true}
                dateRange={{
                    type: "relative",
                    amount: 1,
                    unit: "month",
                }}
                dateRangeFilterKeyOptions={[
                    { value: "created_on", label: "Created" },
                    { value: "updated_on", label: "Updated" },
                ]}
                showFilters={true}
                filterType="select"
                selectFilters={[
                    {
                        name: "$all",
                    },
                    {
                        name: "state",
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
                        name: "base_os",
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
                            }
                        ],
                    },
                ]}
                onFilter={(filters) => {
                    return filters;
                }}
                onSelectionChange={(event) => {
                    this.setState({
                        sessionSelected: event.detail.selectedItems.length > 0,
                    });
                }}
                onFetchRecords={() => {
                    return (this.isAdmin() ? this.getVirtualDesktopAdminClient() : this.getVirtualDesktopClient())
                        .listSessions({
                            filters: this.getListing().getFilters(),
                            paginator: { page_size: 100 },
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
                columnDefinitions={VIRTUAL_DESKTOP_SESSIONS_TABLE_COLUMN_DEFINITIONS}
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
                        text: "Virtual Desktops",
                        href: "#/virtual-desktop/sessions",
                    },
                    {
                        text: "Sessions",
                        href: "",
                    },
                ]}
                content={
                    <div>
                        {this.buildResumeSessionsConfirmModal()}
                        {this.buildDeleteSessionsConfirmModal()}
                        {this.buildStopSessionsConfirmModal()}
                        {this.buildListing()}
                        {this.buildSessionHealthModal()}
                        {this.state.showCreateSoftwareStackFromSessionForm && this.buildCreateSoftwareStackFromSessionForm()}
                        {this.state.showCreateSessionForm && this.buildCreateSessionForm()}
                    </div>
                }
            />
        );
    }
}

export default withRouter(VirtualDesktopSessions);
