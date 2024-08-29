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
import { Box, Button, Container, Form, Grid, Header, Modal, SpaceBetween } from "@cloudscape-design/components";
import { ModalProps } from "@cloudscape-design/components/modal/interfaces";
import { GetUserResult, SocaUserInputChoice, SocaUserInputParamMetadata, User, VirtualDesktopPermissionProfile, VirtualDesktopSession, VirtualDesktopSessionPermission } from "../../../client/data-model";
import { AuthClient, ProjectsClient, VirtualDesktopClient } from "../../../client";
import { AppContext } from "../../../common";
import { IdeaFormField, IdeaFormFieldLifecycleEvent, IdeaFormFieldStateChangeEvent, IdeaFormFieldStateChangeEventHandler } from "../../../components/form-field";
import Utils from "../../../common/utils";
import { faTrash, faUndo } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconDefinition } from "@fortawesome/fontawesome-svg-core";
import VirtualDesktopUtilsClient from "../../../client/virtual-desktop-utils-client";

export interface PermissionRowProps {
    usersList: User[];
    permissionProfileList: VirtualDesktopPermissionProfile[];
    existing: boolean;
    row?: SessionPermissionRow;
    onDeleteButtonClicked: (row_id: string, buttonState: "delete" | "undo") => void;
    onStateChange: IdeaFormFieldStateChangeEventHandler;
    onLifeCycleChange: PermissionRowLifeCycleEventHandler;
}

export interface PermissionRowState {
    isDeleted: boolean;
    selectedProfileId: string;
    selectedExpiryDate: string;
}

type LifeCycleEventType = "mounted" | "unmounted";

export interface PermissionRowLifeCycleEvent {
    type: LifeCycleEventType;
    ref: PermissionRow;
}

export type PermissionRowLifeCycleEventHandler = (event: PermissionRowLifeCycleEvent) => void;

class PermissionRow extends Component<PermissionRowProps, PermissionRowState> {
    registry: { [k: string]: IdeaFormField };

    constructor(props: PermissionRowProps) {
        super(props);
        this.registry = {};
        this.state = {
            isDeleted: false,
            selectedProfileId: "",
            selectedExpiryDate: "",
        };
    }

    componentDidMount() {
        if (this.props.onLifeCycleChange) {
            this.props.onLifeCycleChange({
                type: "mounted",
                ref: this,
            });
        }
    }

    componentWillUnmount() {
        if (this.props.onLifeCycleChange) {
            this.props.onLifeCycleChange({
                type: "unmounted",
                ref: this,
            });
        }
    }

    onStateChange(event: IdeaFormFieldStateChangeEvent) {
        if (event.param.name === "permission-profile") {
            this.setState({
                selectedProfileId: event.value,
            });
        } else if (event.param.name === "expiry-date") {
            this.setState({
                selectedExpiryDate: event.value,
            });
        }

        if (this.props.onStateChange) {
            this.props.onStateChange(event);
        }
    }

    buildPermissionProfileChoices(): SocaUserInputChoice[] {
        let choices: SocaUserInputChoice[] = [];
        this.props.permissionProfileList.forEach((permissionProfile) => {
            choices.push({
                title: permissionProfile.title,
                description: permissionProfile.description,
                value: permissionProfile.profile_id,
            });
        });
        return choices;
    }

    getDefaultPermissionProfileOption(): string {
        if (this.props.existing) {
            return this.props.row?.permission?.permission_profile?.profile_id!;
        }
        return this.state.selectedProfileId;
    }

    getDefaultUserChoice(): string {
        if (this.props.existing) {
            return this.props.row?.permission?.actor_name!;
        }
        return "";
    }

    getDefaultExpiryDate(): string {
        if (this.props.existing) {
            return this.props.row?.permission?.expiry_date!;
        }
        return this.state.selectedExpiryDate;
    }

    onDeleteButtonClicked() {
        if (this.props.existing) {
            this.setState(
                {
                    isDeleted: !this.state.isDeleted,
                },
                () => {
                    let buttonState: "delete" | "undo" = "undo";
                    if (this.state.isDeleted) {
                        buttonState = "delete";
                    }
                    this.props.onDeleteButtonClicked(this.props.row?.row_id!, buttonState);
                }
            );
            return;
        }
        this.props.onDeleteButtonClicked(this.props.row?.row_id!, "delete");
    }

    getDeleteButtonIcon(): IconDefinition {
        if (this.state.isDeleted) {
            return faUndo;
        }
        return faTrash;
    }

    buildDatePickerParams(): SocaUserInputParamMetadata {
        if (this.state.isDeleted) {
            return {
                name: "will-be-deleted",
                data_type: "str",
                param_type: "heading4",
                default: "",
                title: "",
            };
        }
        return {
            name: "expiry-date",
            data_type: "str",
            param_type: "datepicker",
            default: this.getDefaultExpiryDate(),
            validate: {
                required: true,
            },
        };
    }

    buildPermissionProfileParams(): SocaUserInputParamMetadata {
        if (this.state.isDeleted) {
            return {
                name: "will-be-deleted",
                data_type: "str",
                param_type: "heading4",
                default: "Will delete the rule...",
                title: "Will delete the rule...",
            };
        }
        return {
            name: "permission-profile",
            data_type: "str",
            param_type: "select",
            default: this.getDefaultPermissionProfileOption(),
            validate: {
                required: true,
            },
            choices: this.buildPermissionProfileChoices(),
        };
    }

    validate(): boolean {
        let isValid = true;
        Object.keys(this.registry).forEach((key) => {
            let isEntryValid = this.registry[key].triggerValidate();
            // this is split in 2 lines to enforce validation for all entries. Thereby showing all errors on the screen at once.
            isValid = isValid && isEntryValid;
        });
        return isValid;
    }

    onLifeCycleEvent(event: IdeaFormFieldLifecycleEvent) {
        if (event.type === "mounted") {
            this.registry[event.ref.props.param.name!] = event.ref;
        } else {
            delete this.registry[event.ref.props.param.name!];
        }
    }

    render() {
        return (
            <Grid gridDefinition={[{ colspan: 3 }, { colspan: 5 }, { colspan: 3 }, { colspan: 1 }]}>
                <IdeaFormField
                    module={"actor"}
                    onLifecycleEvent={(event) => this.onLifeCycleEvent(event)}
                    onStateChange={(event) => this.onStateChange(event)}
                    group={{
                        name: this.props.row?.row_id,
                    }}
                    param={{
                        name: "actor",
                        data_type: "str",
                        param_type: "select_or_text",
                        readonly: this.props.existing,
                        default: this.getDefaultUserChoice(),
                        validate: {
                            required: true,
                        },
                        choices: Utils.generateUserSelectionChoices(this.props.usersList),
                    }}
                />
                <IdeaFormField
                    module={"permission-profile"}
                    onLifecycleEvent={(event) => this.onLifeCycleEvent(event)}
                    onStateChange={(event) => this.onStateChange(event)}
                    group={{
                        name: this.props.row?.row_id,
                    }}
                    param={this.buildPermissionProfileParams()}
                />
                <IdeaFormField
                    module={"expiry-date"}
                    onLifecycleEvent={(event) => this.onLifeCycleEvent(event)}
                    onStateChange={(event) => this.onStateChange(event)}
                    group={{
                        name: this.props.row?.row_id,
                    }}
                    param={this.buildDatePickerParams()}
                />
                <Button variant={"link"} iconSvg={<FontAwesomeIcon icon={this.getDeleteButtonIcon()} size="xs" />} onClick={() => this.onDeleteButtonClicked()}></Button>
            </Grid>
        );
    }
}

export interface SessionPermissionRow {
    row_id: string;
    existing: boolean;
    permission?: VirtualDesktopSessionPermission;
}

export interface UpdateSessionPermissionModalProps {
    modalSize?: ModalProps.Size;
    onCancel: () => void;
    onSubmit: (createdPermissions: VirtualDesktopSessionPermission[], updatedPermissions: VirtualDesktopSessionPermission[], deletedPermissions: VirtualDesktopSessionPermission[]) => Promise<boolean>;
    session: VirtualDesktopSession;
}

export interface UpdateSessionPermissionModalState {
    showModal: boolean;
    users: User[];
    userListLoaded: boolean;
    permissionProfiles: VirtualDesktopPermissionProfile[];
    permissionProfilesLoaded: boolean;
    existingPermissions: VirtualDesktopSessionPermission[];
    existingPermissionsLoaded: boolean;
    allRows: { [k: string]: SessionPermissionRow };
    visibleRows: { [k: string]: boolean };
    errorCode?: string | null;
    message?: string | null;
}

class UpdateSessionPermissionModal extends Component<UpdateSessionPermissionModalProps, UpdateSessionPermissionModalState> {
    allRowValues: {
        [k: string]: {
            row_id: string;
            action: "create" | "delete" | "update";
            actor?: string | undefined;
            profileId?: string | undefined;
            expiryDate?: string | undefined;
        };
    };

    rowRegistry: { [k: string]: PermissionRow };

    constructor(props: UpdateSessionPermissionModalProps) {
        super(props);
        this.allRowValues = {};
        this.rowRegistry = {};
        this.state = {
            showModal: false,
            permissionProfiles: [],
            users: [],
            allRows: {},
            visibleRows: {},
            existingPermissions: [],
            userListLoaded: false,
            permissionProfilesLoaded: false,
            existingPermissionsLoaded: false,
        };
    }

    createInitRows() {
        if (this.state.existingPermissionsLoaded && this.state.userListLoaded && this.state.permissionProfilesLoaded) {
            let rows: { [k: string]: SessionPermissionRow } = {};
            let visibleRows: { [k: string]: boolean } = {};
            this.state.existingPermissions.forEach((permission) => {
                let row_id = Utils.getUUID();
                rows[row_id] = {
                    row_id: row_id,
                    existing: true,
                    permission: permission,
                };
                visibleRows[row_id] = true;
            });
            this.setState({
                allRows: rows,
                visibleRows: visibleRows,
            });
        }
    }

    componentDidMount() {
      this.buildUserList();
      this.getVirtualDesktopUtilsClient()
            .listPermissionProfiles({})
            .then((response) => {
                this.setState(
                    {
                        permissionProfiles: response.listing!.filter(profile => profile.profile_id != 'admin_profile'),
                        permissionProfilesLoaded: true,
                    },
                    () => {
                        this.createInitRows();
                    }
                );
            });

        this.getVirtualDesktopClient()
            .listSessionPermissions({
                idea_session_id: this.props.session?.idea_session_id,
            })
            .then((response) => {
                this.setState(
                    {
                        existingPermissions: response.listing!,
                        existingPermissionsLoaded: true,
                    },
                    () => {
                        this.createInitRows();
                    }
                );
            });
    }

    getProjectsClient(): ProjectsClient {
        return AppContext.get().client().projects();
    }

    getAuthClient(): AuthClient {
        return AppContext.get().client().auth();
    }

    getVirtualDesktopClient(): VirtualDesktopClient {
        return AppContext.get().client().virtualDesktop();
    }

    getVirtualDesktopUtilsClient(): VirtualDesktopUtilsClient {
        return AppContext.get().client().virtualDesktopUtils();
    }

    buildUserList(): void {
        AppContext.get().client().authz().listRoleAssignments({
            resource_key: `${this.props.session.project?.project_id}:project`
        }).then(async (response) => {
            const groups: string[] = [];
            const userSet: Set<string> = new Set<string>();
            const users: User[] = [];
            const username = AppContext.get().auth().getUsername();
            for (const assignment of response.items) {
                if (assignment.actor_type === "group") {
                    groups.push(assignment.actor_id);
                }
                if (assignment.actor_type === "user" && assignment.actor_id !== username) {
                    userSet.add(assignment.actor_id);
                    users.push({
                        username: assignment.actor_id,
                    });
                }
            }

            const group_response = await this.getAuthClient()
                .listUsersInGroup({
                    group_names: groups,
                });
            group_response.listing?.forEach((user) => {
                if (username === user.username || userSet.has(user.username!)) {
                    return;
                }
                userSet.add(user.username!);
                users.push(user);
            });
            this.setState(
                {
                    users: users,
                    userListLoaded: true,
                },
                () => {
                    this.createInitRows();
                }
            );
        });
    }

    handleRowDeleteButtonClicked(row_id: string, buttonState: "delete" | "undo") {
        let row = this.state.allRows[row_id];

        if (row.existing) {
            if (buttonState === "undo") {
                this.allRowValues[row_id].action = "update";
            } else {
                this.allRowValues[row_id].action = "delete";
            }
        } else {
            // not an existing row, we can deprecate and delete
            let visibleRows = this.state.visibleRows;
            visibleRows[row_id] = false;
            this.setState({
                visibleRows: visibleRows,
            });
        }
    }

    getModalSize(): ModalProps.Size {
        if (this.props.modalSize != null) {
            return this.props.modalSize;
        }
        return "large";
    }

    showModal() {
        this.setState({
            showModal: true,
        });
    }

    hideModal() {
        this.setState({
            showModal: false,
            visibleRows: {},
            allRows: {},
        });
    }

    isActorUnique(name: string): boolean {
        let isUnique = true;
        Object.keys(this.allRowValues).forEach((row_id) => {
            if (this.allRowValues[row_id].actor === name) {
                isUnique = false;
            }
        });
        return isUnique;
    }

    onStateChange(event: IdeaFormFieldStateChangeEvent) {
        let row_id = event.ref.props.group?.name!;
        let row = this.state.allRows[row_id];
        if (row.existing) {
            this.allRowValues[row_id].action = "update";
        }

        if (event.param.name === "permission-profile") {
            this.allRowValues[row_id].profileId = event.value;
        } else if (event.param.name === "expiry-date") {
            this.allRowValues[row_id].expiryDate = event.value;
        } else if (event.param.name === "actor") {
            if (this.isActorUnique(event.value)) {
                this.allRowValues[row_id].actor = event.value;
            } else {
                event.ref.setState({
                    errorMessage: `Actor name must be unique. There already exists rule for actor: ${event.value}`,
                });
            }
        }
    }

    onLifeCycleChange(event: PermissionRowLifeCycleEvent) {
        let row_id = event.ref.props.row?.row_id!;
        if (event.type === "mounted") {
            this.allRowValues[row_id] = {
                row_id: row_id,
                action: "create",
            };
            this.rowRegistry[row_id] = event.ref;
        } else {
            delete this.allRowValues[row_id];
            delete this.rowRegistry[row_id];
        }
    }

    createNewRow() {
        let rows = this.state.allRows;
        let visibleRows = this.state.visibleRows;
        let row_id = Utils.getUUID();
        rows[row_id] = {
            row_id: row_id,
            existing: false,
        };
        visibleRows[row_id] = true;
        this.setState({
            allRows: rows,
            visibleRows: visibleRows,
        });
    }

    buildForm() {
        return (
            <form onSubmit={(e) => e.preventDefault()}>
                <Form
                    header={
                        <Header
                            description={"Select the username, desktop shared setting and the expiry date of the rules"}
                            actions={
                                <Button
                                    variant={"normal"}
                                    onClick={() => {
                                        this.createNewRow();
                                    }}
                                >
                                    {" "}
                                    Add User{" "}
                                </Button>
                            }
                            variant={"h2"}
                        />
                    }
                    variant="embedded"
                    errorText={this.state.message}
                >
                    <Container variant={"stacked"}>
                        {Object.keys(this.state.allRows).map((row_id) => {
                            let row = this.state.allRows[row_id];
                            let ref: RefObject<PermissionRow> = React.createRef();
                            return (
                                this.state.visibleRows[row.row_id] && (
                                    <PermissionRow
                                        ref={ref}
                                        key={row.row_id}
                                        usersList={this.state.users}
                                        onLifeCycleChange={(event) => this.onLifeCycleChange(event)}
                                        permissionProfileList={this.state.permissionProfiles}
                                        existing={row.existing}
                                        row={row}
                                        onDeleteButtonClicked={(row_id, buttonState) => this.handleRowDeleteButtonClicked(row_id, buttonState)}
                                        onStateChange={(event) => this.onStateChange(event)}
                                    />
                                )
                            );
                        })}
                    </Container>
                </Form>
            </form>
        );
    }

    setError(errorCode: string, message: string) {
        this.setState({
            errorCode: errorCode,
            message: message,
        });
    }

    render() {
        return (
            <Modal
                visible={this.state.showModal}
                size={this.getModalSize()}
                onDismiss={() => {
                    this.setState(
                        {
                            showModal: false,
                        },
                        () => {
                            if (this.props.onCancel) {
                                this.props.onCancel();
                            }
                        }
                    );
                }}
                header={
                    <div>
                        <Header variant="h2">{"Update Permission for " + this.props.session.name}</Header>
                    </div>
                }
                footer={
                    <Box float="right">
                        <SpaceBetween direction={"horizontal"} size={"xs"}>
                            <Button
                                variant={"normal"}
                                onClick={() => {
                                    this.setState(
                                        {
                                            showModal: false,
                                            visibleRows: {},
                                            allRows: {},
                                        },
                                        () => {
                                            if (this.props.onCancel) {
                                                this.props.onCancel();
                                            }
                                        }
                                    );
                                }}
                            >
                                Cancel
                            </Button>
                            <Button
                                variant={"primary"}
                                onClick={() => {
                                    let isValid = true;
                                    Object.keys(this.rowRegistry).forEach((key) => {
                                        let isEntryValid = this.rowRegistry[key].validate();
                                        // this is split in 2 lines to enforce validation for all entries. Thereby showing all errors on the screen at once.
                                        isValid = isValid && isEntryValid;
                                    });

                                    if (!isValid) {
                                        return;
                                    }

                                    let addedPermissions: VirtualDesktopSessionPermission[] = [];
                                    let updatedPermissions: VirtualDesktopSessionPermission[] = [];
                                    let deletedPermissions: VirtualDesktopSessionPermission[] = [];
                                    Object.keys(this.allRowValues).forEach((key) => {
                                        let rowValue = this.allRowValues[key];
                                        let row_id = rowValue.row_id;
                                        if (!this.state.visibleRows[row_id]) {
                                            return;
                                        }

                                        let permission: VirtualDesktopSessionPermission = {
                                            idea_session_id: this.props.session.idea_session_id,
                                            idea_session_owner: this.props.session.owner,
                                            idea_session_name: this.props.session.name,
                                            idea_session_instance_type: this.props.session.server?.instance_type!,
                                            idea_session_base_os: this.props.session.base_os,
                                            idea_session_state: this.props.session.state,
                                            idea_session_created_on: this.props.session.created_on,
                                            idea_session_type: this.props.session.type,
                                            actor_name: this.allRowValues[key].actor,
                                            actor_type: "USER",
                                            expiry_date: `${Date.parse(this.allRowValues[key].expiryDate!)}`,
                                            permission_profile: {
                                                profile_id: this.allRowValues[key].profileId,
                                            },
                                        };

                                        if (rowValue.action === "create") {
                                            addedPermissions.push(permission);
                                        } else if (rowValue.action === "update") {
                                            updatedPermissions.push(permission);
                                        } else {
                                            deletedPermissions.push(permission);
                                        }
                                    });

                                    if (this.props.onSubmit) {
                                        return this.props.onSubmit(addedPermissions, updatedPermissions, deletedPermissions);
                                    } else {
                                        return Promise.resolve(true);
                                    }
                                }}
                            >
                                Save
                            </Button>
                        </SpaceBetween>
                    </Box>
                }
            >
                {this.buildForm()}
            </Modal>
        );
    }
}

export default UpdateSessionPermissionModal;
