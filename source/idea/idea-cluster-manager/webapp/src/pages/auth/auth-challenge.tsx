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

import { AUTH_PARAM_NEW_PASSWORD, IdeaAuthProps, IdeaAuthState } from "./auth-interfaces";
import { Box, Button, ColumnLayout, SpaceBetween, StatusIndicator } from "@cloudscape-design/components";
import AuthLayout from "./auth-layout";
import IdeaAuthContext from "./auth-context";
import { withRouter } from "../../navigation/navigation-utils";
import IdeaForm from "../../components/form";
import { AppContext } from "../../common";
import { AUTH_LOGIN_CHALLENGE, NETWORK_ERROR, REQUEST_TIMEOUT } from "../../common/error-codes";
import { PasswordStrengthCheck } from "../../components/password-strength-check";

class IdeaAuthChallenge extends Component<IdeaAuthProps, IdeaAuthState> {
    static contextType = IdeaAuthContext;
    form: RefObject<IdeaForm>;
    passwordStrengthCheck: RefObject<PasswordStrengthCheck>;

    constructor(props: IdeaAuthProps) {
        super(props);
        this.form = React.createRef();
        this.passwordStrengthCheck = React.createRef();
        this.state = {
            loading: false,
            layoutLoading: false,
            canSubmit: false,
        };
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
                    if (!this.passwordStrengthCheck.current!.checkPassword(values.password)) {
                        return;
                    }
                    AppContext.get()
                        .auth()
                        .respondToAuthChallenge(values.password)
                        .then((_) => {
                            this.props.navigate("/");
                        })
                        .catch((error) => {
                            if (error.errorCode === AUTH_LOGIN_CHALLENGE) {
                                this.props.navigate("/auth/challenge");
                            } else if (error.errorCode === NETWORK_ERROR || error.errorCode === REQUEST_TIMEOUT) {
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
                        canSubmit: false,
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
                        <h3 className="title">Change Password</h3>
                        <p className="description">To prevent unauthorized access to your account, please change your password.</p>
                        <IdeaForm
                            name="login-form"
                            ref={this.form}
                            showHeader={false}
                            showActions={false}
                            stretch={true}
                            onStateChange={(event) => {
                                if (event.param.name === "password") {
                                    this.setState({
                                        canSubmit: this.passwordStrengthCheck.current!.checkPassword(event.value),
                                    });
                                }
                            }}
                            onSubmit={(_) => {
                                this.onSubmit();
                            }}
                            params={[AUTH_PARAM_NEW_PASSWORD]}
                        />

                        <PasswordStrengthCheck ref={this.passwordStrengthCheck} />
                        <SpaceBetween size={"xs"} direction={"vertical"} className="actions">
                            {!this.state.loading && (
                                <Button
                                    variant="primary"
                                    onClick={() => {
                                        this.onSubmit();
                                    }}
                                    disabled={!this.state.canSubmit}
                                >
                                    Change Password
                                </Button>
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

export default withRouter(IdeaAuthChallenge);
