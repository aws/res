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

import { AUTH_PARAM_NEW_PASSWORD, AUTH_PARAM_USERNAME, AUTH_PARAM_VERIFICATION_CODE, IdeaAuthProps, IdeaAuthState } from "./auth-interfaces";
import { Box, Button, ColumnLayout, SpaceBetween, StatusIndicator } from "@cloudscape-design/components";
import AuthLayout from "./auth-layout";
import IdeaAuthContext from "./auth-context";
import IdeaForm from "../../components/form";
import { AppContext } from "../../common";
import { withRouter } from "../../navigation/navigation-utils";
import { NETWORK_ERROR, REQUEST_TIMEOUT } from "../../common/error-codes";

class IdeaAuthConfirmForgotPassword extends Component<IdeaAuthProps, IdeaAuthState> {
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

    getForm(): IdeaForm {
        return this.form.current!;
    }

    onSubmit() {
        this.setState(
            {
                loading: true,
            },
            () => {
                if (this.getForm().validate()) {
                    this.getForm().clearError();
                    const values = this.getForm().getValues();
                    AppContext.get()
                        .auth()
                        .confirmForgotPassword(values.verificationCode, values.password)
                        .then((ok) => {
                            if (ok) {
                                this.props.navigate("/");
                            } else {
                                // edge case: username was not found in local storage, prompt user to go through forgot password flow again.
                                this.props.navigate("/auth/forgot-password");
                            }
                        })
                        .catch((error) => {
                            if (error.errorCode === NETWORK_ERROR || error.errorCode === REQUEST_TIMEOUT) {
                                this.getForm().setError(error.errorCode, `Failed to communicate with backend service: ${error.message}`);
                            } else {
                                this.getForm().setError(error.errorCode, error.message);
                            }
                        })
                        .finally(() => {
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
    }

    render() {
        return (
            <AuthLayout
                content={
                    <ColumnLayout columns={1} className="auth-content">
                        <h3 className="title">Reset Password</h3>
                        <p className="description">We've sent a verification code to your account's email address. Please enter the verification code to reset your password.</p>
                        <IdeaForm
                            name="login-form"
                            ref={this.form}
                            showHeader={false}
                            showActions={false}
                            onSubmit={(_) => {
                                this.onSubmit();
                            }}
                            stretch={true}
                            params={[
                                {
                                    ...AUTH_PARAM_USERNAME,
                                    default: AppContext.get().auth().getForgotPasswordUserName(),
                                    readonly: true,
                                    auto_focus: false,
                                },
                                AUTH_PARAM_VERIFICATION_CODE,
                                {
                                    ...AUTH_PARAM_NEW_PASSWORD,
                                    auto_focus: false,
                                },
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
                                        Reset Password
                                    </Button>
                                    <p>Did not receive verification email? Please verify if the username is valid or if the email is marked as Spam or Junk. If not, click Resend Verification Email link below:</p>
                                    <Button
                                        variant="link"
                                        onClick={() => {
                                            this.props.navigate("/auth/forgot-password");
                                        }}
                                    >
                                        Resend Verification Email
                                    </Button>
                                    <Button
                                        variant="link"
                                        onClick={() => {
                                            this.props.navigate("/auth/login");
                                        }}
                                    >
                                        Go back to Sign In
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

export default withRouter(IdeaAuthConfirmForgotPassword);
