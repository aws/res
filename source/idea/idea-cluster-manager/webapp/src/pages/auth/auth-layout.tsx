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

import React, { Component } from "react";
import { AppLayout, Grid } from "@cloudscape-design/components";
import { AppContext } from "../../common";
import "./auth.scss";
import Utils from "../../common/utils";

export interface AuthLayoutProps {
    loading?: boolean;
    content: JSX.Element;
}

export interface AuthLayoutState {
    ready: boolean;
}

class AuthLayout extends Component<AuthLayoutProps, AuthLayoutState> {
    constructor(props: AuthLayoutProps) {
        super(props);
        this.state = {
            ready: false,
        };
    }

    componentDidMount() {
        AppContext.get()
            .auth()
            .isLoggedIn()
            .then((status) => {
                // show loading animation spinner until the initial sso redirect is not complete
                if (!status && Utils.isSsoEnabled() && typeof window.idea.app.sso_auth_status === "undefined") {
                    return;
                }
                this.setState(
                    {
                        ready: true,
                    },
                    () => {
                        Utils.hideLoadingAnimation();
                    }
                );
            });
    }

    isLoading(): boolean {
        if (this.props.loading == null) {
            return false;
        }
        return this.props.loading;
    }

    render() {
        return (
            <AppLayout
                navigationHide={true}
                toolsHide={true}
                content={
                    this.state.ready && (
                        <main className="soca-app-content auth">
                            <Grid gridDefinition={[{ colspan: { xxs: 12, s: 6, l: 4 }, offset: { xxs: 0, s: 3, l: 4 } }]}>
                                <div className="auth-content-wrapper">
                                    {!this.isLoading() && this.props.content}
                                    <p className="copyright">{AppContext.get().getCopyRightText()}</p>
                                </div>
                            </Grid>
                        </main>
                    )
                }
            />
        );
    }
}

export default AuthLayout;
