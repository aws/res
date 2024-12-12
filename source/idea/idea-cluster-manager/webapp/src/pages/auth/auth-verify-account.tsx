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

import { ConfirmSignUpRequest, ResendConfirmationCodeRequest } from "../../client/data-model";
import { AccountsClient } from "../../client";

import { AUTH_PARAM_SIGNUP_USER_EMAIL, AUTH_PARAM_VERIFICATION_CODE, IdeaAuthProps, IdeaAuthState } from "./auth-interfaces";
import { Alert, Box, Button, ColumnLayout, SpaceBetween, StatusIndicator } from "@cloudscape-design/components";
import AuthLayout from "./auth-layout";
import IdeaAuthContext from "./auth-context";
import { AppContext } from "../../common";
import IdeaForm from "../../components/form";
import { withRouter } from "../../navigation/navigation-utils";
import { Constants } from "../../common/constants";

export interface RESAuthVerifyAccountState extends IdeaAuthState{
    confirmationCodeResent: boolean;
}

class RESAuthVerifyAccount extends Component<IdeaAuthProps, RESAuthVerifyAccountState> {
    static contextType = IdeaAuthContext;
    form: RefObject<IdeaForm>;

    constructor(props: IdeaAuthProps) {
        super(props);
        this.form = React.createRef();
        this.state = {
            loading: false,
            layoutLoading: false,
            confirmationCodeResent: false,
        };
    }

    accountsClient(): AccountsClient {
        return AppContext.get().client().accounts();
    }

    getForm(): IdeaForm {
        return this.form.current!;
    }

    onSubmit = async () => {
        this.setState({
            loading: true
        });
    
        if (!this.getForm().validate()) {
            this.setState({
                loading: false
            });
            return;
        }
    
        this.setState({
            confirmationCodeResent: false
        });
        
        this.getForm().clearError();
        const values = this.getForm().getValues();
        
        const confirmSignUpRequest: ConfirmSignUpRequest = {
            email: values.email,
            confirmation_code: values.verificationCode
        };
    
        try {
            await this.accountsClient().confirmSignUp(confirmSignUpRequest);
            this.props.navigate("/auth/login");
        } catch (error : any) {
            this.getForm().setError(error.errorCode, error.message);
        } finally {
            this.setState({
                loading: false
            });
        }
    };

    resendConfirmationCode = async () => {
        this.setState({
            loading: true,
            confirmationCodeResent: false
        });
    
        this.getForm().clearError();
        const values = this.getForm().getValues();
        const usernameRegExpression = RegExp(Constants.USERNAME_FROM_EMAIL_REGEX);
    
        try {
            if (usernameRegExpression.test(values.email)) {
                const resendConfirmationCodeRequest: ResendConfirmationCodeRequest = {
                    username: usernameRegExpression.exec(values.email)![0],
                };
                
                await this.accountsClient().resendConfirmationCode(resendConfirmationCodeRequest);
                this.setState({
                    confirmationCodeResent: true
                });
            } else {
                this.getForm().setError("GENERAL_ERROR", "Email is required.");
            }
        } catch (error : any) {
            this.getForm().setError(error.errorCode, error.message);
        } finally {
            this.setState({
                loading: false
            });
        }
    };

    render() {
        return (
            <AuthLayout
                content={
                    <ColumnLayout columns={1} className="auth-content">
                        <h3 className="title">Verify email address</h3>
                        <p className="description">To verify your email, we've sent a verification code to your email.</p>
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
                                AUTH_PARAM_VERIFICATION_CODE
                            ]}
                        />
                        {!this.state.loading && (
                            <SpaceBetween size={"xs"} direction={"vertical"} className="actions">
                                {this.state.confirmationCodeResent && (
                                    <Alert type="info">
                                        Confirmation code has been resent. Check your email to access the code.
                                    </Alert>
                                )}
                                <Button
                                    variant="primary"
                                    onClick={async () => {
                                        await this.onSubmit();
                                    }}
                                >
                                    Verify
                                </Button>
                                <Button
                                    variant="link"
                                    onClick={async () => {
                                        await this.resendConfirmationCode();
                                    }}
                                >
                                    Resend verification code
                                </Button>
                            </SpaceBetween>
                        )}
                        {this.state.loading && (
                            <Box textAlign={"center"}>
                                <StatusIndicator type="loading" />
                            </Box>
                        )}
                    </ColumnLayout>
                }
            />
        );
    }
}

export default withRouter(RESAuthVerifyAccount);
