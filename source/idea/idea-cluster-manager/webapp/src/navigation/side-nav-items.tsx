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

import { Box, Link, Popover, SideNavigationProps } from "@cloudscape-design/components";
import { AppContext } from "../common";

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

    if (context.getClusterSettingsService().isVirtualDesktopDeployed()) {
        userNav.items.push({
            type: "link",
            text: "My virtual desktops",
            href: "#/home/virtual-desktops",
        });
        userNav.items.push({
            type: "link",
            text: "Shared desktops",
            href: "#/home/shared-desktops",
        });
    }

    if (context.getClusterSettingsService().getIsFileBrowserEnabled()) {
        userNav.items.push({
            type: "link",
            text: "File browser",
            href: "#/home/file-browser",
        });
    }

    if (context.getClusterSettingsService().getIsSshEnabled()) {
        userNav.items.push({
            type: "link",
            text: "SSH access instructions",
            href: "#/home/ssh-access",
        });
    }

    // start admin section

    adminNavItems.push({
        type: "divider",
    });

    if (context.getClusterSettingsService().isVirtualDesktopDeployed() && context.auth().isAdmin()) {
        adminNavItems.push({
            type: "section",
            text: "Session management",
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
                    text: "Software stacks",
                    href: "#/virtual-desktop/software-stacks",
                },
                {
                    type: "link",
                    text: "Debugging",
                    href: "#/virtual-desktop/debug",
                },
                {
                    type: "link",
                    text: "Desktop settings",
                    href: "#/virtual-desktop/settings",
                },
            ],
        });
    }

    if (context.auth().isAdmin()) {
        adminNavItems.push({
            type: "section",
            text: "Environment Management",
            defaultExpanded: true,
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
                    text: "File systems",
                    href: "#/cluster/filesystem",
                },
                {
                    type: "link",
                    text: "S3 buckets",
                    href: "#/cluster/s3-bucket",
                },
                {
                    type: "link",
                    text: "Identity management",
                    href: "#/cluster/identity-management",
                    info: (
                    <Box color="text-status-info" display="inline">
                        <Popover
                            header="Introducing Identity management"
                            size="medium"
                            triggerType="text"
                            content={
                                <>
                                    A centralized location to manage Cognito users, Active Directory settings, and Single Sign-On.
                                </>
                            }
                            renderWithPortal={true}
                        >
                            <Box color="text-status-info" fontSize="body-s" fontWeight="bold">
                                New
                            </Box>
                        </Popover>
                    </Box>
                    )
                },
                {
                    type: "link",
                    text: "Permission policy",
                    href: "#/cluster/permissions",
                },
                {
                    type: "link",
                    text: "Environment status",
                    href: "#/cluster/status",
                },
                {
                    type: "link",
                    text: "Snapshot management",
                    href: "#/cluster/snapshot-management",
                },
                {
                    type: "link",
                    text: "Environment settings",
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
