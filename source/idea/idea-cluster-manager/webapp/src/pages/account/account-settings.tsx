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

import { IdeaSideNavigationProps } from "../../components/side-navigation";
import { Button, ButtonDropdown, ColumnLayout, Container, Header, SpaceBetween, Tabs } from "@cloudscape-design/components";
import { KeyValue, KeyValueGroup } from "../../components/key-value";
import { AuthClient } from "../../client";
import { AppContext } from "../../common";
import { AuthService } from "../../service";
import { User } from "../../client/data-model";
import IdeaForm from "../../components/form";
import IdeaAppLayout, { IdeaAppLayoutProps } from "../../components/app-layout";
import { withRouter } from "../../navigation/navigation-utils";

export interface AccountSettingsProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {}

export interface AccountSettingsState {
    user: User | null;
    usersInGroup: User[] | null;
}

class AccountSettings extends Component<AccountSettingsProps, AccountSettingsState> {
    changePasswordForm: RefObject<IdeaForm>;
    addUserToGroupForm: RefObject<IdeaForm>;
    removeUserFromGroupForm: RefObject<IdeaForm>;

    constructor(props: AccountSettingsProps) {
        super(props);
        this.changePasswordForm = React.createRef();
        this.addUserToGroupForm = React.createRef();
        this.removeUserFromGroupForm = React.createRef();
        this.state = {
            user: null,
            usersInGroup: null,
        };
    }

    componentDidMount() {
        this.fetchUser().then(() => {
            this.fetchUsersInGroup().finally();
        });
    }

    getAuthService(): AuthService {
        return AppContext.get().auth();
    }

    getAuthClient(): AuthClient {
        return AppContext.get().client().auth();
    }

    getChangePasswordForm(): IdeaForm {
        return this.changePasswordForm.current!;
    }

    getAddUserToGroupForm(): IdeaForm {
        return this.addUserToGroupForm.current!;
    }

    getRemoveUserFromGroupForm(): IdeaForm {
        return this.removeUserFromGroupForm.current!;
    }

    fetchUser(): Promise<boolean> {
        return new Promise<boolean>((resolve, reject) => {
            this.getAuthService()
                .getUser()
                .then((user) => {
                    this.setState(
                        {
                            user: user,
                        },
                        () => {
                            resolve(true);
                        }
                    );
                })
                .catch((e) => {
                    console.error(e);
                    reject(false);
                });
        });
    }

    fetchUsersInGroup() {
        return this.getAuthClient()
            .listUsersInGroup({
                group_names: [this.state.user?.group_name!],
            })
            .then((result) => {
                this.setState({
                    usersInGroup: result.listing!,
                });
                return true;
            });
    }

    buildAddUserToGroupForm() {
        return (
            <IdeaForm
                ref={this.addUserToGroupForm}
                name="add-user-to-group"
                title="Add Users to your Group"
                modal={true}
                modalSize="medium"
                onSubmit={() => {
                    if (!this.getAddUserToGroupForm().validate()) {
                        return Promise.resolve(false);
                    }
                    let values: any = this.getAddUserToGroupForm().getValues();
                    return this.getAuthClient()
                        .addUserToGroup(values)
                        .then(() => {
                            return this.fetchUsersInGroup().then(() => {
                                this.getAddUserToGroupForm().hideModal();
                                return true;
                            });
                        })
                        .catch((error) => {
                            this.getAddUserToGroupForm().setError(error.errorCode, error.message);
                            return false;
                        });
                }}
                params={[
                    {
                        name: "usernames",
                        title: "Username",
                        description: "Enter the usernames of the user you want to remove from your group",
                        multiple: true,
                        validate: {
                            required: true,
                        },
                    },
                ]}
            />
        );
    }

    buildRemoveUserFromGroupForm() {
        return (
            <IdeaForm
                ref={this.removeUserFromGroupForm}
                name="remove-user-from-group"
                title="Remove Users from your Group"
                modal={true}
                modalSize="medium"
                onSubmit={() => {
                    if (!this.getRemoveUserFromGroupForm().validate()) {
                        return Promise.resolve(false);
                    }
                    let values: any = this.getRemoveUserFromGroupForm().getValues();
                    return this.getAuthClient()
                        .removeUserFromGroup(values)
                        .then(() => {
                            return this.fetchUsersInGroup().then(() => {
                                this.getRemoveUserFromGroupForm().hideModal();
                                return true;
                            });
                        })
                        .catch((error) => {
                            this.getRemoveUserFromGroupForm().setError(error.errorCode, error.message);
                            return false;
                        });
                }}
                params={[
                    {
                        name: "usernames",
                        title: "Username",
                        description: "Enter the usernames of the user you want to remove from your group",
                        multiple: true,
                        validate: {
                            required: true,
                        },
                    },
                ]}
            />
        );
    }

    buildChangePasswordForm() {
        return (
            <IdeaForm
                ref={this.changePasswordForm}
                name="change-password"
                title="Change Password"
                modal={true}
                modalSize="medium"
                onSubmit={() => {
                    if (!this.getChangePasswordForm().validate()) {
                        return Promise.resolve(false);
                    }
                    let values: any = this.getChangePasswordForm().getValues();

                    return this.getAuthClient()
                        .changePassword(values)
                        .then(() => {
                            return this.getAuthClient()
                                .globalSignOut({})
                                .then(() => {
                                    this.getChangePasswordForm().hideModal();
                                    return AppContext.get()
                                        .auth()
                                        .logout()
                                        .then(() => {
                                            return true;
                                        });
                                })
                                .catch((error) => {
                                    this.getChangePasswordForm().setError(error.errorCode, error.message);
                                    return false;
                                });
                        })
                        .catch((error) => {
                            this.getChangePasswordForm().setError(error.errorCode, error.message);
                            return false;
                        });
                }}
                params={[
                    {
                        name: "old_password",
                        title: "Old Password",
                        description: "Enter your current password",
                        param_type: "password",
                        data_type: "str",
                        validate: {
                            required: true,
                        },
                    },
                    {
                        name: "new_password",
                        title: "New Password",
                        description: "Enter your new password",
                        param_type: "new-password",
                        data_type: "str",
                        validate: {
                            required: true,
                        },
                    },
                ]}
            />
        );
    }

    render() {
        const isPasswordRotationApplicable = () => {
            return AppContext.get().auth().isPasswordExpirationApplicable();
        };

        const getPasswordExpiresIn = () => {
            const expiresIn = AppContext.get().auth().getPasswordExpiresInDays();
            if (expiresIn > 0) {
                if (expiresIn > 1) {
                    return `${expiresIn} days`;
                } else {
                    return `1 day`;
                }
            }
            return "Password Expired";
        };

        const getUsersInGroup = () => {
            const result: string[] = [];
            if (this.state.usersInGroup) {
                this.state.usersInGroup.forEach((user) => {
                    result.push(user.username!);
                });
            }
            return result;
        };

        return (
            <IdeaAppLayout
                ideaPageId={this.props.ideaPageId}
                tools={this.props.tools}
                toolsOpen={this.props.toolsOpen}
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
                        text: "Account Settings",
                        href: "#",
                    },
                ]}
                header={
                    <Header
                        variant="h1"
                        actions={
                            <SpaceBetween size="s" direction="horizontal">
                                <ButtonDropdown
                                    onItemClick={(event) => {
                                        if (event.detail.id === "add-user-to-group") {
                                            this.getAddUserToGroupForm().showModal();
                                        } else if (event.detail.id === "remove-user-from-group") {
                                            this.getRemoveUserFromGroupForm().showModal();
                                        }
                                    }}
                                    items={[
                                        {
                                            id: "add-user-to-group",
                                            text: "Add User to my Group",
                                        },
                                        {
                                            id: "remove-user-from-group",
                                            text: "Remove User from my Group",
                                        },
                                    ]}
                                >
                                    Actions
                                </ButtonDropdown>
                                <Button
                                    variant="primary"
                                    onClick={() => {
                                        this.getChangePasswordForm().showModal();
                                    }}
                                >
                                    Change Password
                                </Button>
                            </SpaceBetween>
                        }
                    >
                        {" "}
                        Account Settings
                    </Header>
                }
                contentType={"default"}
                content={
                    <div>
                        {this.buildChangePasswordForm()}
                        {this.buildAddUserToGroupForm()}
                        {this.buildRemoveUserFromGroupForm()}
                        <ColumnLayout columns={1}>
                            <Container>
                                <Tabs
                                    tabs={[
                                        {
                                            id: "profile",
                                            label: "My Profile",
                                            content: this.state.user && (
                                                <ColumnLayout columns={2}>
                                                    <KeyValueGroup title="My Profile">
                                                        <KeyValue title="Username" value={this.state.user?.username} />
                                                        <KeyValue title="Email" value={this.state.user?.email} />
                                                        <KeyValue title="Home Directory" value={this.state.user?.home_dir} />
                                                        <KeyValue title="Login Shell" value={this.state.user?.login_shell} />
                                                        <KeyValue title="Is Administrator?" value={this.state.user?.role=='admin'?'Yes':'No'} type="boolean" />
                                                        <KeyValue title="Synced On" value={new Date(this.state.user?.synced_on!).toLocaleString()} />
                                                        {isPasswordRotationApplicable() && <KeyValue title="Password Expires In" value={getPasswordExpiresIn()} />}
                                                    </KeyValueGroup>
                                                    <KeyValueGroup title="LDAP Info">
                                                        <KeyValue title="UID" value={this.state.user?.uid} />
                                                        <KeyValue title="GID" value={this.state.user?.gid} />
                                                        <KeyValue title="Group Name" value={this.state.user.group_name} />
                                                        <KeyValue title="Additional users in my group" value={getUsersInGroup()} />
                                                    </KeyValueGroup>
                                                </ColumnLayout>
                                            ),
                                        },
                                    ]}
                                />
                            </Container>
                        </ColumnLayout>
                    </div>
                }
            />
        );
    }
}

export default withRouter(AccountSettings);
