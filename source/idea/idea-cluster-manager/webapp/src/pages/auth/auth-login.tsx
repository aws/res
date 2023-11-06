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

import { AUTH_PARAM_USERNAME, AUTH_PARAM_PASSWORD, IdeaAuthProps, IdeaAuthState } from "./auth-interfaces";
import { Box, Button, ColumnLayout, SpaceBetween, StatusIndicator } from "@cloudscape-design/components";
import AuthLayout from "./auth-layout";
import IdeaAuthContext from "./auth-context";
import { AppContext } from "../../common";
import { AUTH_LOGIN_CHALLENGE, AUTH_PASSWORD_RESET_REQUIRED, NETWORK_ERROR, REQUEST_TIMEOUT } from "../../common/error-codes";
import IdeaForm from "../../components/form";
import Utils from "../../common/utils";
import { withRouter } from "../../navigation/navigation-utils";

class IdeaAuthLogin extends Component<IdeaAuthProps, IdeaAuthState> {
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

    onSubmit = () => {
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
                        .login(values.username, values.password)
                        .then((_) => {
                            this.props.navigate("/");
                        })
                        .catch((error) => {
                            if (error.errorCode === AUTH_LOGIN_CHALLENGE) {
                                this.props.navigate("/auth/challenge");
                            } else if (error.errorCode === AUTH_PASSWORD_RESET_REQUIRED) {
                                this.props.navigate("/auth/confirm-forgot-password");
                            } else {
                                if (error.errorCode === NETWORK_ERROR || error.errorCode === REQUEST_TIMEOUT) {
                                    this.getForm().setError(error.errorCode, `Failed to communicate with backend service: ${error.message}`);
                                } else {
                                    this.getForm().setError(error.errorCode, "Error in authenticating given username/password combination");
                                    this.getForm().setParamValue("password", "");
                                }
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
    };

    render() {
        const getSubtitle = () => {
            return AppContext.get().getSubtitle();
        };
        const hasSubtitle = () => {
            return Utils.isNotEmpty(getSubtitle());
        };
        return (
            <AuthLayout
                content={
                    <ColumnLayout columns={1} className="auth-content">
                        <h3 className="title">{AppContext.get().getTitle()}</h3>
                        {hasSubtitle() && <p className="subtitle">{getSubtitle()}</p>}
                        <IdeaForm
                            name="login-form"
                            ref={this.form}
                            modalSize={"max"}
                            showHeader={false}
                            showActions={false}
                            onSubmit={(_) => {
                                this.onSubmit();
                            }}
                            stretch={true}
                            params={[AUTH_PARAM_USERNAME, AUTH_PARAM_PASSWORD]}
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
                                        Sign In
                                    </Button>
                                    <Button
                                        variant="link"
                                        onClick={() => {
                                            this.props.navigate("/auth/forgot-password");
                                        }}
                                    >
                                        Forgot Password?
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

export default withRouter(IdeaAuthLogin);
