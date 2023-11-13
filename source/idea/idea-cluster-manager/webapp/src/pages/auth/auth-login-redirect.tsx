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
 
import { IdeaAuthProps, IdeaAuthState } from "./auth-interfaces";
import {  ColumnLayout, Flashbar, FlashbarProps, Link } from "@cloudscape-design/components";
import AuthLayout from "./auth-layout";
import { AppContext } from "../../common";
import Utils from "../../common/utils";
import { withRouter } from "../../navigation/navigation-utils";

const ERROR_MESSAGES : { [key: string]: string } = {
    "UserNotFound": "User not found"
}

class IdeaAuthLoginRedirect extends Component<IdeaAuthProps, IdeaAuthState> {
    constructor(props: IdeaAuthProps) {
        super(props);
        this.state = {
            loading: false,
            layoutLoading: false,
        };
    }

    render() {
        const getSubtitle = () => {
            return AppContext.get().getSubtitle();
        };
        const hasSubtitle = () => {
            return Utils.isNotEmpty(getSubtitle());
        };
        
        const redirectToHome = () => {
            window.location.href = "/";
        }

        const getFlashBarItem = (message: string | React.ReactNode, type: FlashbarProps.Type = "error")  => {
            return  {
                content: message,
                dismissible: false,
                type: type,
            }
        }

        const checkErrorMsg = () => {
            try {
                const error_msg : string = window.idea.app.error_msg;
                if(error_msg && ERROR_MESSAGES[error_msg] != undefined) {
                    return <Flashbar items={[getFlashBarItem(ERROR_MESSAGES[error_msg])]}/>;
                } else {
                    return "";    
                }
            } catch {
                return "";
            }
        }

        return (
            <AuthLayout
                content={
                    <ColumnLayout columns={1} className="auth-content">
                        <h3 className="title">{AppContext.get().getTitle()}</h3>
                        {hasSubtitle() && <p className="subtitle">{getSubtitle()}</p>}
                        { !this.state.loading && (<div className="description">
                            Error logging in. Click <Link onFollow={() => redirectToHome()}>here</Link> to try again.
                        </div>)}
                        {checkErrorMsg()}
                    </ColumnLayout>
                }
            />
        );
    }
}

export default withRouter(IdeaAuthLoginRedirect);