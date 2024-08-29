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
import { Navigate } from "react-router-dom";
import { IdeaAppNavigationProps } from "../../navigation/navigation-utils";
import { withRouter } from "../../navigation/navigation-utils";
import { AppContext } from "../../common";
import { Constants } from "../../common/constants";
import Utils from "../../common/utils";

export interface IdeaAuthRouteProps extends IdeaAppNavigationProps {
    isLoggedIn: boolean;
    children: React.ReactNode;
    isProjectOwner?: boolean;
}

class IdeaAuthenticatedRoute extends Component<IdeaAuthRouteProps> {
    render() {
        const context = AppContext.get();
        const currentUrl = new URL(window.location.href);
        const currentPath = currentUrl.hash.substring(1);
        const isAuthRoute = currentPath.startsWith("/auth/");
        const isVirtualDesktopAdminRoute = currentPath.startsWith("/virtual-desktop");
        const isClusterAdminRoute = currentPath.startsWith("/cluster");

        if (this.props.isLoggedIn) {
            if (isAuthRoute) {
                return <Navigate to="/" />;
            } else if (isVirtualDesktopAdminRoute && (!context.getClusterSettingsService().isVirtualDesktopDeployed() || !context.auth().isAdmin())) {
                if (this.props.isProjectOwner) {
                  return this.props.children;
                }  
                return <Navigate to="/" />;
            } else if (isClusterAdminRoute && !context.auth().isAdmin()) {
                if (this.props.isProjectOwner) {
                  return this.props.children;
                }
                return <Navigate to="/" />;
            } else {
                return this.props.children;
            }
        } else {
            if (isAuthRoute) {
                return this.props.children;
            } else {
                if (Utils.isSsoEnabled()) {
                    return <Navigate to="/auth/login-redirect" />;
                } else {
                    return <Navigate to="/auth/login" />;
                }
            }
        }
    }
}

export default withRouter(IdeaAuthenticatedRoute);
