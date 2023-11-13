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

import { Component } from "react";
import { SideNavigation, SideNavigationProps } from "@cloudscape-design/components";
import { NonCancelableEventHandler } from "@cloudscape-design/components/internal/events";
import { Constants } from "../../common/constants";
import Utils from "../../common/utils";
import { IdeaAppNavigationProps } from "../../navigation/navigation-utils";
import "./side-navigation.scss";

export interface IdeaSideNavigationProps extends IdeaAppNavigationProps {
    sideNavHeader: SideNavigationProps.Header;
    sideNavItems: SideNavigationProps.Item[];
    onSideNavChange: NonCancelableEventHandler<SideNavigationProps.ChangeDetail>;
    activePath?: string;
}

const SIDE_NAV_ROOT_CLASS_NAME = "awsui_root_l0dv0_1mtlo_93";
const SIDE_NAV_LINK_CLASS_NAME = "awsui_link_l0dv0_1mtlo_180";

class IdeaSideNavigation extends Component<IdeaSideNavigationProps> {
    onFollowHandler(event: CustomEvent<SideNavigationProps.FollowDetail>) {
        event.preventDefault();
        if (event.detail.href) {
            this.props.navigate(event.detail.href.substring(1));
        }
    }

    componentDidMount() {
        let sideNavRoot = document.getElementsByClassName(SIDE_NAV_ROOT_CLASS_NAME);
        if (sideNavRoot.length > 0) {
            let links = sideNavRoot[0].getElementsByClassName(SIDE_NAV_LINK_CLASS_NAME);
            for (let i = 0; i < links.length; i++) {
                let link = links[i];
                if (link.textContent!.trim() === Constants.ADMIN_ZONE_LINK_TEXT) {
                    link.setAttribute("id", "idea-admin-zone-link");
                }
            }
        }
    }

    getActivePath(): string {
        if (Utils.isNotEmpty(this.props.activePath)) {
            return `#${this.props.activePath}`;
        } else {
            return `#${this.props.location.pathname}`;
        }
    }

    render() {
        return (
            <SideNavigation
                className="idea-side-nav"
                header={this.props.sideNavHeader}
                items={this.props.sideNavItems}
                activeHref={this.getActivePath()}
                onFollow={this.onFollowHandler.bind(this)}
                onChange={(event) => {
                    if (this.props.onSideNavChange) {
                        this.props.onSideNavChange(event);
                    }
                }}
            />
        );
    }
}

export default IdeaSideNavigation;
