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

import { SideNavigationProps } from "@cloudscape-design/components";
import { AppContext } from "../common";
import { Constants } from "../common/constants";

export const IdeaSideNavHeader = (context: AppContext): SideNavigationProps.Header => {
    return {
        text: context.getSubtitle(),
        href: "#/",
    };
};

export const IdeaSideNavItems = (context: AppContext): SideNavigationProps.Item[] => {
    const result: SideNavigationProps.Item[] = [];
    const adminNavItems: SideNavigationProps.Item[] = [];

    const userNav: any = {
        type: "section",
        text: "Desktops",
        defaultExpanded: true,
        items: [],
    };
    result.push(userNav);

    if (context.getClusterSettingsService().isVirtualDesktopDeployed() && context.auth().hasModuleAccess(Constants.MODULE_VIRTUAL_DESKTOP_CONTROLLER)) {
        userNav.items.push({
            type: "link",
            text: "My Virtual Desktops",
            href: "#/home/virtual-desktops",
        });
        userNav.items.push({
            type: "link",
            text: "Shared Desktops",
            href: "#/home/shared-desktops",
        });
    }

    if (context.auth().hasModuleAccess(Constants.MODULE_CLUSTER_MANAGER)) {
        userNav.items.push({
            type: "link",
            text: "File Browser",
            href: "#/home/file-browser",
        });
        if (context.getClusterSettingsService().isBastionHostDeployed()) {
            userNav.items.push({
                type: "link",
                text: "SSH Access Instructions",
                href: "#/home/ssh-access",
            });
        }
    }

    // start admin section

    adminNavItems.push({
        type: "divider",
    });

    if (context.getClusterSettingsService().isVirtualDesktopDeployed() && context.auth().isModuleAdmin(Constants.MODULE_VIRTUAL_DESKTOP_CONTROLLER)) {
        adminNavItems.push({
            type: "section",
            text: "Session Management",
            defaultExpanded: true,
            items: [
                {
                    type: "link",
                    text: "Dashboard",
                    href: "#/virtual-desktop/dashboard",
                },
                {
                    type: "link",
                    text: "Sessions",
                    href: "#/virtual-desktop/sessions",
                },
                {
                    type: "link",
                    text: "Software Stacks",
                    href: "#/virtual-desktop/software-stacks",
                },
                {
                    type: "link",
                    text: "Permission Profiles",
                    href: "#/virtual-desktop/permission-profiles",
                },
                {
                    type: "link",
                    text: "Debugging",
                    href: "#/virtual-desktop/debug",
                },
                {
                    type: "link",
                    text: "Desktop Settings",
                    href: "#/virtual-desktop/settings",
                },
            ],
        });
    }

    if (context.auth().isModuleAdmin(Constants.MODULE_CLUSTER_MANAGER)) {
        adminNavItems.push({
            type: "section",
            text: "Environment Management",
            defaultExpanded: false,
            items: [
                {
                    type: "link",
                    text: "Projects",
                    href: "#/cluster/projects",
                },
                {
                    type: "link",
                    text: "Users",
                    href: "#/cluster/users",
                },
                {
                    type: "link",
                    text: "Groups",
                    href: "#/cluster/groups",
                },
                {
                    type: "link",
                    text: "File Systems",
                    href: "#/cluster/filesystem",
                },
                {
                    type: "link",
                    text: "Environment Status",
                    href: "#/cluster/status",
                },
                {
                    type: "link",
                    text: "Environment Snapshots",
                    href: "#/cluster/snapshots",
                },
                {
                    type: "link",
                    text: "General Settings",
                    href: "#/cluster/settings",
                },
            ],
        });
    }

    // ignore divider and admin-zone text
    if (adminNavItems.length > 2) {
        adminNavItems.forEach((item) => {
            result.push(item);
        });
    }

    return result;
};
