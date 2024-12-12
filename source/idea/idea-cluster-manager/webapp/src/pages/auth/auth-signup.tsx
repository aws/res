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

import { SignUpUserRequest } from "../../client/data-model";
import { AccountsClient } from "../../client";

import { AUTH_PARAM_SIGNUP_USER_EMAIL, AUTH_PARAM_SIGNUP_USER_PASSWORD, AUTH_PARAM_SIGNUP_USER_REENTER_PASSWORD, IdeaAuthProps, IdeaAuthState } from "./auth-interfaces";
import { Box, Button, ColumnLayout, SpaceBetween, StatusIndicator } from "@cloudscape-design/components";
import AuthLayout from "./auth-layout";
import IdeaAuthContext from "./auth-context";
import { AppContext } from "../../common";
import IdeaForm from "../../components/form";
import { withRouter } from "../../navigation/navigation-utils";

class RESAuthSignUp extends Component<IdeaAuthProps, IdeaAuthState> {
    static contextType = IdeaAuthContext;
    form: RefObject<IdeaForm>;

    constructor(props: IdeaAuthProps) {
        super(props);
        this.form = React.createRef();
        this.state = {
            loading: false,
            layoutLoading: false,
        };
    }

    accountsClient(): AccountsClient {
        return AppContext.get().client().accounts();
    }

    getForm(): IdeaForm {
        return this.form.current!;
    }

    onSubmit = () => {
        this.setState(
            {
                loading: true,
            },
            () => {
                if (this.getForm().validate()) {
                    this.getForm().clearError();
                    const values = this.getForm().getValues();
                    if (values.password !== values.reenterPassword) {
                        this.getForm().setError("GENERAL_ERROR", "Passwords do not match");
                        this.setState({
                            loading: false,
                        });
                        return;
                    }
                    const signUpUserRequest: SignUpUserRequest = {
                        email: values.email,
                        password: values.password,
                    };
                    this.accountsClient().signUpUser(signUpUserRequest).then(() => {
                        this.props.navigate("/auth/verify-account");
                    }).catch((error) => {
                        this.getForm().setError(error.errorCode, error.message);
                    }).finally(() => {
                        this.setState({
                            loading: false,
                        });
                    });
                } else {
                    this.setState({
                        loading: false,
                    });
                }
            }
        );
    };

    render() {
        return (
            <AuthLayout
                content={
                    <ColumnLayout columns={1} className="auth-content">
                        <h3 className="title">Create account</h3>
                        <IdeaForm
                            name="signup-form"
                            ref={this.form}
                            modalSize={"max"}
                            showHeader={false}
                            showActions={false}
                            onSubmit={(_) => {
                                this.onSubmit();
                            }}
                            stretch={true}
                            params={[
                                AUTH_PARAM_SIGNUP_USER_EMAIL,
                                AUTH_PARAM_SIGNUP_USER_PASSWORD,
                                AUTH_PARAM_SIGNUP_USER_REENTER_PASSWORD,
                            ]}
                        />
                        <SpaceBetween size={"xs"} direction={"vertical"} className="actions">
                            {!this.state.loading && (
                                <div>
                                    <Button
                                        variant="primary"
                                        onClick={() => {
                                            this.onSubmit();
                                        }}
                                    >
                                        Create account
                                    </Button>
                                </div>
                            )}
                            {this.state.loading && (
                                <Box textAlign={"center"}>
                                    <StatusIndicator type="loading" />
                                </Box>
                            )}
                        </SpaceBetween>
                    </ColumnLayout>
                }
            />
        );
    }
}

export default withRouter(RESAuthSignUp);
