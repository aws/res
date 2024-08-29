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
import IdeaForm from "../../../components/form";
import { SocaUserInputParamMetadata, VirtualDesktopPermission, VirtualDesktopPermissionProfile } from "../../../client/data-model";
import Utils from "../../../common/utils";
import dot from "dot-object";
import { AppContext } from "../../../common";
import VirtualDesktopUtilsClient from "../../../client/virtual-desktop-utils-client";

export interface VirtualDesktopPermissionProfileFormProps {
    editMode: boolean;
    profileToEdit?: VirtualDesktopPermissionProfile;
    onDismiss: () => void;
    onSubmit: (permissionProfile: VirtualDesktopPermissionProfile) => Promise<boolean>;
}

export interface VirtualDesktopPermissionProfileFormState {
    showModal: boolean;
    base_permissions: VirtualDesktopPermission[];
    loading: boolean;
}

class VirtualDesktopPermissionProfileForm extends Component<VirtualDesktopPermissionProfileFormProps, VirtualDesktopPermissionProfileFormState> {
    form: RefObject<IdeaForm>;
    permissionProfileInputHistory: { [key: string]: boolean };

    constructor(props: VirtualDesktopPermissionProfileFormProps) {
        super(props);
        this.form = React.createRef();
        this.permissionProfileInputHistory = {};
        this.state = {
            showModal: false,
            base_permissions: [],
            loading: true,
        };
    }

    hideForm() {
        this.permissionProfileInputHistory = {};
        this.setState(
            {
                showModal: false,
            },
            () => {
                this.props.onDismiss();
            }
        );
    }

    showModal() {
        this.setState(
            {
                showModal: true,
            },
            () => {
                this.getForm().showModal();
            }
        );
    }

    getForm() {
        return this.form.current!;
    }

    setError(errorCode: string, errorMessage: string) {
        this.getForm().setError(errorCode, errorMessage);
    }

    buildTitle(): string {
        if (this.props.editMode) {
            return `Update Desktop Shared Setting: ${this.props.profileToEdit?.title}`;
        }
        return "Register new Desktop Shared Setting";
    }

    getVirtualDesktopUtilsClient(): VirtualDesktopUtilsClient {
        return AppContext.get().client().virtualDesktopUtils();
    }

    componentDidMount() {
        this.getVirtualDesktopUtilsClient()
            .getBasePermissions({})
            .then((response) => {
                this.setState({
                    loading: false,
                    base_permissions: response.permissions!,
                });
            });
    }

    buildDefaultTitle(): string {
        if (this.props.editMode) {
            return this.props.profileToEdit?.title!;
        }
        return "";
    }

    buildDefaultProfileID(): string {
        if (this.props.editMode) {
            return this.props.profileToEdit?.profile_id!;
        }
        return "";
    }

    buildDefaultDescription(): string {
        if (this.props.editMode) {
            return this.props.profileToEdit?.description!;
        }
        return "";
    }

    getDefaultValueForPermission(basePermission: VirtualDesktopPermission): boolean {
        let defaultValue = false;
        this.props.profileToEdit?.permissions?.forEach((permission) => {
            if (basePermission.key === permission.key) {
                defaultValue = permission.enabled!;
                this.permissionProfileInputHistory[permission.key!] = permission.enabled!;
            }
        });
        return defaultValue;
    }

    buildFormParams(): any {
        let formParams: SocaUserInputParamMetadata[];
        if (this.state.loading) {
            formParams = [
                {
                    name: "loading",
                    title: "Loading base permissions",
                    data_type: "str",
                    param_type: "heading3",
                    readonly: true,
                },
            ];
        } else {
            formParams = [
                {
                    name: "profile_id",
                    title: "Desktop Shared Setting ID",
                    description: "Enter a Unique ID for the Desktop Shared Setting",
                    data_type: "str",
                    param_type: "text",
                    default: this.buildDefaultProfileID(),
                    readonly: this.props.editMode,
                    validate: {
                        required: true,
                    },
                },
                {
                    name: "title",
                    title: "Title",
                    description: "Enter a user friendly Title for the Shared Setting",
                    data_type: "str",
                    default: this.buildDefaultTitle(),
                    param_type: "text",
                    validate: {
                        required: true,
                    },
                },
                {
                    name: "description",
                    title: "Description",
                    description: "Enter a user friendly description for the Desktop Shared Setting",
                    data_type: "str",
                    default: this.buildDefaultDescription(),
                    param_type: "text",
                    validate: {
                        required: true,
                    },
                },
            ];

            this.state.base_permissions.forEach((permission: VirtualDesktopPermission) => {
                formParams.push({
                    name: permission.key!,
                    title: permission.name!,
                    data_type: "bool",
                    default: this.getDefaultValueForPermission(permission),
                    description: permission.description!,
                    param_type: "checkbox",
                    validate: {
                        required: true,
                    },
                });
            });
        }
        return formParams;
    }

    render() {
        return (
            this.state.showModal && (
                <IdeaForm
                    ref={this.form}
                    name="permission-profile-form"
                    modal={true}
                    modalSize="large"
                    columns={3}
                    title={this.buildTitle()}
                    onStateChange={(event) => {
                        if (event.param.name === "builtin") {
                            this.state.base_permissions.forEach((permission: VirtualDesktopPermission) => {
                                if (permission.key === "builtin") {
                                    return;
                                }
                                let field = this.getForm()?.getFormField(permission.key!);
                                if (event.value) {
                                    this.permissionProfileInputHistory[permission.key!] = Utils.asBoolean(field?.getValueAsString(), false);
                                    field?.setValue(true);
                                    field?.disable(true);
                                } else {
                                    let history = this.permissionProfileInputHistory[permission.key!];
                                    if (Utils.isEmpty(history)) {
                                        history = false;
                                    }
                                    field?.setValue(history);
                                    field?.disable(false);
                                }
                            });
                        }
                    }}
                    onCancel={() => {
                        this.hideForm();
                    }}
                    onSubmit={() => {
                        this.getForm().clearError();
                        if (!this.getForm().validate()) {
                            return;
                        }
                        const values = this.getForm().getValues();

                        let permissions: VirtualDesktopPermission[] = [];
                        this.state.base_permissions.forEach((permission: VirtualDesktopPermission) => {
                            permissions.push({
                                ...permission,
                                enabled: Utils.asBoolean(dot.pick(permission.key!, values), false),
                            });
                        });

                        let permission_profile: VirtualDesktopPermissionProfile = {
                            profile_id: values.profile_id,
                            title: values.title,
                            description: values.description,
                            permissions: permissions,
                        };

                        return this.props
                            .onSubmit(permission_profile)
                            .then((result) => {
                                this.hideForm();
                                return Promise.resolve(result);
                            })
                            .catch((error) => {
                                this.getForm().setError(error.errorCode, error.message);
                                return Promise.resolve(false);
                            });
                    }}
                    params={this.buildFormParams()}
                />
            )
        );
    }
}

export default VirtualDesktopPermissionProfileForm;
