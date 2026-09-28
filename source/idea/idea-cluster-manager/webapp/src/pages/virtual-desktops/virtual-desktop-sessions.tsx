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
import { Project, SocaUserInputChoice } from "../../client/data-model";
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
import VirtualDesktopCreateSessionForm from "./forms/virtual-desktop-create-session-form";
import VirtualDesktopScheduleModal from "./components/virtual-desktop-schedule-modal";
import { withRouter } from "../../navigation/navigation-utils";
import { fetchAllSessions } from "../../common/sessions-fetcher";
import { VirtualDesktopSession, VirtualDesktopSoftwareStack } from "../../client/generated/api";

export interface VirtualDesktopSessionsProps extends IdeaAppLayoutProps, IdeaSideNavigationProps { }

export interface VirtualDesktopSessionsState {
    showCreateSoftwareStackFromSessionForm: boolean;
    sessionForSoftwareStack: VirtualDesktopSession | undefined;
    softwareStackForSession: VirtualDesktopSoftwareStack | undefined;
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
        cell: (e) => Utils.getOsTitle(e.base_os),
        sortingComparator: (a, b) => (a.base_os || '').localeCompare(b.base_os || '')
    },
    {
        id: "instance_type",
        header: "Instance Type",
        cell: (e) => e.server?.instance_type,
        sortingComparator: (a, b) => (a.server?.instance_type || '').localeCompare(b.server?.instance_type || '')
    },
    {
        id: "state",
        header: "State",
        cell: (e) => {
            return <VirtualDesktopSessionStatusIndicator state={e.state!} hibernation_enabled={e.hibernation_enabled!} />;
        },
        sortingField: "state",
    },
    {
        id: "project_title",
        header: "Project",
        cell: (e) => e.project?.title,
        sortingComparator: (a, b) => (a.project?.title || '').localeCompare(b.project?.title || '')
    },
    {
        id: "created_on",
        header: "Created On",
        cell: (e) => new Date(e.created_on!).toLocaleString(),
        sortingField: "created_on",
    },
    {
        id: "updated_on",
        header: "Updated On",
        cell: (e) => new Date(e.updated_on!).toLocaleString(),
        sortingField: "updated_on",
    },
];

const PREFERENCES_KEY = "user-sessions";

class VirtualDesktopSessions extends Component<VirtualDesktopSessionsProps, VirtualDesktopSessionsState> {
    listing: RefObject<IdeaListView>;
    deleteSessionsConfirmModal: RefObject<IdeaConfirm>;
    stopSessionsConfirmModal: RefObject<IdeaConfirm>;
    rebootSessionsConfirmModal: RefObject<IdeaConfirm>;
    resumeSessionsConfirmModal: RefObject<IdeaConfirm>;
    sessionHealthModal: RefObject<IdeaView>;
    createSoftwareStackForm: RefObject<IdeaForm>;
    createSessionForm: RefObject<VirtualDesktopCreateSessionForm>;
    scheduleModal: RefObject<VirtualDesktopScheduleModal>;
    virtualDesktopSettings: any;

    constructor(props: VirtualDesktopSessionsProps) {
        super(props);
        this.listing = React.createRef();
        this.deleteSessionsConfirmModal = React.createRef();
        this.stopSessionsConfirmModal = React.createRef();
        this.rebootSessionsConfirmModal = React.createRef();
        this.resumeSessionsConfirmModal = React.createRef();
        this.sessionHealthModal = React.createRef();
        this.createSoftwareStackForm = React.createRef();
        this.createSessionForm = React.createRef();
        this.scheduleModal = React.createRef();
        this.virtualDesktopSettings = undefined;

        this.state = {
            showCreateSoftwareStackFromSessionForm: false,
            sessionForSoftwareStack: undefined,
            softwareStackForSession: undefined,
            sessionSelected: false,
            forceStop: false,
            projectChoices: [],
            forceTerminate: false,
            sessionHealth: {},
            showCreateSessionForm: false,
            projects: [],
        };
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

    getProjectsClient(): ProjectsClient {
        return AppContext.get().client().projects();
    }

    getListing(): IdeaListView {
        return this.listing.current!;
    }

    canCreateSoftwareStack(): boolean {
        const sessions = this.getSelectedSessions();
        return sessions.length === 1 && sessions[0].state === "READY";
    }

    isSelected(): boolean {
        return this.state.sessionSelected;
    }

    hasErrorStateSessions(): boolean {
        return this.getSelectedSessions().some(session => session.state === "ERROR");
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

    getRebootSessionsConfirmModal(): IdeaConfirm {
        return this.rebootSessionsConfirmModal.current!;
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
            softwareStackForSession: undefined,
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
                if (session.software_stack_id && session.base_os) {
                    this.getVirtualDesktopAdminClient()
                        .getSoftwareStack({
                            stackId: session.software_stack_id,
                            baseOs: session.base_os as any,
                        })
                        .then((result) => {
                            this.setState({ softwareStackForSession: result.softwareStack as VirtualDesktopSoftwareStack }, () => {
                                this.getCreateSoftwareStackForm().showModal();
                            });
                        })
                        .catch((error) => {
                            this.setFlashMessage(`Failed to load software stack: ${error.message}`, "error");
                        });
                } else {
                    this.getCreateSoftwareStackForm().showModal();
                }
            }
        );
    };

    buildCreateSoftwareStackFromSessionForm() {
        const get_min_storage = (): number => {
            return this.state.softwareStackForSession?.min_storage?.value ?? 50
        }
        return (
            <IdeaForm
                ref={this.createSoftwareStackForm}
                name={"create-software-stack"}
                modal={true}
                title={"Create Software Stack for " + this.state.sessionForSoftwareStack?.name}
                alert={"The session will be rebooted when creating a software stack."}
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

                    const sessionPayload = {...this.state.sessionForSoftwareStack!};

                    this.getVirtualDesktopAdminClient()
                        .createSoftwareStackFromSession({
                            session: sessionPayload as any,
                            software_stack: {
                                ...this.state.softwareStackForSession,
                                name: values.name,
                                description: values.description,
                                min_storage: {
                                    value: values.root_storage_size,
                                    unit: "gb",
                                },
                                projects: projectValues,
                            } as any,
                        })
                        .then(() => {
                            this.setFlashMessage("New software stack is provisioning and that it may take several minutes before it can be used", "success");
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
                            regex: "^[\\(\\)\\.\\/\\-\\'\\@\\w \\\[\\\]]{3,128}$",
                            message: "Use 3-128 alphanumeric characters, parentheses (()), square brackets ([]), spaces ( ), periods (.), slashes (/), dashes (-), single quotes (‘), at-signs (@), or underscores(_).",
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
                        default: get_min_storage(),
                        validate: {
                            required: true,
                            min: get_min_storage(),
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
                            owner: session.owner,
                        })
                    );
                    this.getVirtualDesktopClient()
                        .batchStartSession({
                            sessions: toResume,
                        })
                        .then(
                            (result) => {
                                this.setState(
                                    {
                                        sessionSelected: false,
                                    },
                                    () => {
                                        const failedNames = result['unsuccessful_list']?.map((entry) => entry.session?.name ?? entry.session?.idea_session_id).join(', ');
                                        this.setFlashMessage(
                                            `Successfully submitted start request for ${result['successful_list']?.length ?? 0} session(s).` +
                                            (result['unsuccessful_list']?.length ? ` Failed to start: ${failedNames}.` : ''),
                                            result['unsuccessful_list']?.length ? "error" : "success"
                                        );
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
                            owner: session.owner,
                            force: this.state.forceTerminate,
                        })
                    );
                    this.getVirtualDesktopClient()
                        .batchDeleteSession({
                            sessions: toDelete,
                        })
                        .then(
                            (result) => {
                                this.setState(
                                    {
                                        sessionSelected: false,
                                    },
                                    () => {
                                        this.setFlashMessage(
                                            `Successfully submitted delete request for ${result['successful_list']?.length ?? 0} session(s).` +
                                            (result['unsuccessful_list']?.length ? ` ${result['unsuccessful_list'].length} session(s) failed.` : ''),
                                            result['unsuccessful_list']?.length ? "error" : "success"
                                        );
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
                            owner: session.owner,
                            name: session.name,
                            hibernation_enabled: session.hibernation_enabled ?? false,
                            force: this.state.forceStop,
                        })
                    );
                    this.getVirtualDesktopClient()
                        .batchStopSession({
                            sessions: toStop,
                        })
                        .then(
                            (result) => {
                                this.setState(
                                    {
                                        sessionSelected: false,
                                    },
                                    () => {
                                        this.setFlashMessage(
                                            `Successfully submitted stop request for ${result['successful_list']?.length ?? 0} session(s).` +
                                            (result['unsuccessful_list']?.length ? ` ${result['unsuccessful_list'].length} session(s) failed.` : ''),
                                            result['unsuccessful_list']?.length ? "error" : "success"
                                        );
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

    buildRebootSessionsConfirmModal() {
        const errorStateSessions = this.getSelectedSessions().filter(session => session.state === "ERROR");
        const skippedSessions = this.getSelectedSessions().filter(session => session.state !== "ERROR");
        
        return (
            <IdeaConfirm
                ref={this.rebootSessionsConfirmModal}
                title={"Reboot Session(s)"}
                onConfirm={() => {
                    const toReboot: VirtualDesktopSession[] = [];
                    errorStateSessions.forEach((session) =>
                        toReboot.push({
                            idea_session_id: session.idea_session_id,
                            owner: session.owner,
                        })
                    );
                    this.getVirtualDesktopClient()
                        .batchRebootSession({
                            sessions: toReboot,
                        })
                        .then(
                            (result) => {
                                this.setState(
                                    {
                                        sessionSelected: false,
                                    },
                                    () => {
                                        const successCount = result['successful_list']?.length ?? 0;
                                        const failedNames = result['unsuccessful_list']?.map((entry) => entry.session?.name ?? entry.session?.idea_session_id).join(', ');
                                        let message = '';
                                        if (successCount > 0) {
                                            message += `Successfully submitted reboot request for ${successCount} session(s).`;
                                        }
                                        if (result['unsuccessful_list']?.length) {
                                            message += (message ? ' ' : '') + `Failed to reboot: ${failedNames}.`;
                                        }
                                        this.setFlashMessage(message, result['unsuccessful_list']?.length ? "error" : "success");
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
                <p>Are you sure you want to reboot below sessions in Error state:</p>
                {errorStateSessions.map((session, index) => {
                    return (
                        <li key={index}>
                            {session.name} (Owner: {session.owner}, State: {session.state})
                        </li>
                    );
                })}
                {skippedSessions.length > 0 && (
                    <>
                        <p style={{ marginTop: '16px' }}>The following sessions will be skipped (not in Error state):</p>
                        {skippedSessions.map((session, index) => {
                            return (
                                <li key={index}>
                                    {session.name} (Owner: {session.owner}, State: {session.state})
                                </li>
                            );
                        })}
                    </>
                )}
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
                    return this.getVirtualDesktopClient()
                        .batchCreateSession({
                            sessions: [{
                                name: session_name,
                                owner: username,
                                hibernation_enabled: hibernation_enabled,
                                software_stack_id: software_stack_id,
                                base_os: base_os,
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
                            }],
                        })
                        .then((result) => {
                            if (result.unsuccessful_list?.length > 0) {
                                const failure = result.unsuccessful_list[0];
                                this.getCreateSessionForm().setError(failure.error_code, failure.message);
                                return Promise.resolve(false);
                            }
                            if (result.successful_list?.length > 0) {
                                this.getCreateSessionForm().hideForm();
                                this.getListing().fetchRecords();
                                return Promise.resolve(true);
                            }
                            this.getCreateSessionForm().setError('UNKNOWN', 'No session was created');
                            return Promise.resolve(false);
                        })
                        .catch((error) => {
                            const errorMessage = error?.response?.data?.message || error?.message || 'Failed to create session';
                            this.getCreateSessionForm().setError(error.errorCode || '400', errorMessage);
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
                                    forceStop: false,
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
                        id: "edit-schedule",
                        text: "Edit Schedule",
                        disabled: this.getSelectedSessions().length !== 1 || !this.isAdmin(),
                        disabledReason: "Select exactly 1 session to enable this Action",
                        onClick: () => {
                            this.scheduleModal.current?.showSchedule(this.getSelectedSessions()[0]);
                        },
                    },
                    {
                        id: "reboot-session",
                        text: "Reboot Session(s)",
                        disabled: !this.hasErrorStateSessions() || !this.isAdmin(),
                        disabledReason: "Select at least one session in Error state to enable this Action",
                        onClick: () => {
                            this.getRebootSessionsConfirmModal().show();
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
                        id: "create-software-stack",
                        text: "Create Software Stack From Session",
                        disabled: !this.canCreateSoftwareStack() || !this.isAdmin(),
                        disabledReason: "Select exactly 1 session in READY state to enable this Action",
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
                onSelectionChange={(event) => {
                    this.setState({
                        sessionSelected: event.detail.selectedItems.length > 0,
                    });
                }}
                onFetchRecords={async () => {
                    const filters = this.getListing().getFilters();
                    const dateRange = this.getListing().getFormatedDateRange();
                    const result = await fetchAllSessions(
                        this.getVirtualDesktopClient(),
                        filters,
                        dateRange,
                        this.props.onFlashbarChange
                    )
                    return {
                        listing: result.listing,
                        filters: filters,
                        date_range: dateRange,
                    }
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
                        {this.buildRebootSessionsConfirmModal()}
                        {this.buildListing()}
                        {this.buildSessionHealthModal()}
                        {this.state.showCreateSoftwareStackFromSessionForm && this.buildCreateSoftwareStackFromSessionForm()}
                        {this.state.showCreateSessionForm && this.buildCreateSessionForm()}
                        <VirtualDesktopScheduleModal
                            ref={this.scheduleModal}
                            modalType="session"
                            onScheduleChange={(session) => {
                                return this.getVirtualDesktopClient()
                                    .updateSession(
                                        session.idea_session_id!,
                                        {
                                            session: session as VirtualDesktopSession,
                                        })
                                    .then(() => {
                                        this.setFlashMessage("Session schedule updated successfully.", "success");
                                        this.getListing().fetchRecords();
                                        return true;
                                    })
                                    .catch((error) => {
                                        this.scheduleModal.current?.setErrorMessage(error.message);
                                        return false;
                                    });
                            }}
                        />
                    </div>
                }
            />
        );
    }
}

export default withRouter(VirtualDesktopSessions);
