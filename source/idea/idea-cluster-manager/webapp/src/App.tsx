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
import "./App.scss";
import { IdeaAuthChallenge, IdeaAuthConfirmForgotPassword, IdeaAuthenticatedRoute, IdeaAuthForgotPassword, IdeaAuthLogin, IdeaAuthLoginRedirect } from "./pages/auth";
import Home from "./pages/home";
import { AppContext } from "./common";
import Users from "./pages/user-management/users";
import Groups from "./pages/user-management/groups";
import SocaFileBrowser from "./pages/home/file-browser";
import VirtualDesktopDashboard from "./pages/virtual-desktops/virtual-desktop-dashboard";
import VirtualDesktopSessions from "./pages/virtual-desktops/virtual-desktop-sessions";
import VirtualDesktopSoftwareStacks from "./pages/virtual-desktops/virtual-desktop-software-stacks";
import MyVirtualDesktopSessions from "./pages/virtual-desktops/my-virtual-desktop-sessions";
import VirtualDesktopSettings from "./pages/virtual-desktops/virtual-desktop-settings";
import VirtualDesktopSessionDetail from "./pages/virtual-desktops/virtual-desktop-session-detail";
import VirtualDesktopDebug from "./pages/virtual-desktops/virtual-desktop-debug";
import { DashboardMain } from "./pages/dashboard";
import AccountSettings from "./pages/account/account-settings";
import SSHAccess from "./pages/home/ssh-access";
import ClusterSettings from "./pages/cluster-admin/cluster-settings";
import ClusterStatus from "./pages/cluster-admin/cluster-status";
import Projects from "./pages/cluster-admin/projects";
import ConfigureProject from "./pages/cluster-admin/configure-project";
import FileSystems from "./pages/cluster-admin/filesystem";
import S3Buckets from "./pages/cluster-admin/s3-bucket";
import AddS3Bucket from "./pages/cluster-admin/add-s3-bucket";
import EditS3Bucket from "./pages/cluster-admin/edit-s3-bucket";
import { Box, HelpPanel, SideNavigationProps, StatusIndicator } from "@cloudscape-design/components";
import { NonCancelableCustomEvent } from "@cloudscape-design/components/internal/events";
import { FlashbarProps } from "@cloudscape-design/components/flashbar/interfaces";
import EmailTemplates from "./pages/cluster-admin/email-templates";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import { applyDensity, applyMode, Density, Mode } from "@cloudscape-design/global-styles";
import VirtualDesktopPermissionProfiles from "./pages/virtual-desktops/virtual-desktop-permission-profiles";
import VirtualDesktopPermissionProfileDetail from "./pages/virtual-desktops/virtual-desktop-permission-profile-detail";
import MySharedVirtualDesktopSessions from "./pages/virtual-desktops/my-shared-virtual-desktop-sessions";
import VirtualDesktopSoftwareStackDetail from "./pages/virtual-desktops/virtual-desktop-software-stack-detail";
import { IdeaSideNavHeader, IdeaSideNavItems } from "./navigation/side-nav-items";
import { IdeaAppNavigationProps, withRouter } from "./navigation/navigation-utils";
import { Routes, Route, Navigate } from "react-router-dom";
import IdeaLogTail from "./pages/home/log-tail";
import Utils from "./common/utils";
import SnapshotManagement from "./pages/snapshots/snapshot-management"
import PermissionProfilesDashboard from "./pages/permission-profiles/permission-profiles-dashboard";
import PermissionProfilesView from "./pages/permission-profiles/view-permission-profile";
import ConfigurePermissionProfile from "./pages/permission-profiles/configure-permission-profile";
import AuthzClient from "./client/authz-client";

export interface IdeaWebPortalAppProps extends IdeaAppNavigationProps {}

export interface IdeaWebPortalAppState {
    sideNavHeader: SideNavigationProps.Header;
    sideNavItems: SideNavigationProps.Item[];
    isLoggedIn: boolean;
    isInitialized: boolean;
    toolsOpen: boolean;
    tools: React.ReactNode;
    flashbarItems: FlashbarProps.MessageDefinition[];
    hasProjects?: boolean;
    projectOwnerRoles?: string[];
}

export interface OnToolsChangeEvent {
    pageId: string;
    open: boolean;
}

export interface OnPageChangeEvent {
    pageId: string;
}

export interface OnFlashbarChangeEvent {
    items: FlashbarProps.MessageDefinition[];
    append?: boolean;
}

class IdeaWebPortalApp extends Component<IdeaWebPortalAppProps, IdeaWebPortalAppState> {
    constructor(props: IdeaWebPortalAppProps) {
        super(props);
        this.state = {
            isLoggedIn: false,
            isInitialized: false,
            sideNavHeader: {
                text: "...",
                href: "#/",
            },
            sideNavItems: [],
            toolsOpen: false,
            tools: null,
            flashbarItems: [],
            hasProjects: false,
            projectOwnerRoles: [],
        };
    }

    componentDidMount() {
        AppContext.setOnRoute(this.onRoute);
        const context = AppContext.get();
        context
            .auth()
            .isLoggedIn()
            .then((loginStatus) => {
                const init = () => {
                    if (!context.auth().isAdmin()) {
                      const isInProject = async (): Promise<{
                          isInProject: boolean;
                          canCreateSession: boolean;
                      }> => {
                          const output = {
                              isInProject: false,
                              canCreateSession: false,
                          }
                          const user = await context.auth().getUser();
                          const authzClient: AuthzClient = context.client().authz();
                          const projects = await context.client().projects().getUserProjects({ username: user.username });
                          if (!projects.projects || projects.projects.length === 0) {
                              return output;
                          }
                          output.isInProject = true;
                          const rolePermissions = await authzClient.listRoles({
                              include_permissions: true,
                          });
                          const projectRoleAssignments: Promise<void>[] = [];
                          
                          // for every project, we check if the user has permission to create sessions
                          // in that project
                          for (const project of projects.projects!) {
                              const resource_key = `${project.project_id!}:project`;
                              projectRoleAssignments.push(Promise.resolve(
                                  authzClient.listRoleAssignments({ resource_key })
                                  .then(async (result) => {
                                      for (const roleAssignment of result.items) {
                                          let currentUserIsInRole = user.additional_groups?.includes(roleAssignment.actor_id) || roleAssignment.actor_id === user.username!;

                                          if (currentUserIsInRole) {
                                              const rolePermission = rolePermissions.items.find(perm => perm.role_id === roleAssignment.role_id);
                                              if (rolePermission && rolePermission.vdis?.create_terminate_others_sessions) {
                                                  output.canCreateSession = true;
                                                  return; // we only need to know if one of the roles allows creating sessions
                                              }
                                          }
                                      }

                                  })
                              ));
                          }
                          await Promise.all(projectRoleAssignments);

                          return output;
                      };
                      isInProject()
                      .then((hasProjects) => {
                          // user is not assigned to any projects, don't render projects page
                          if (!hasProjects.isInProject)
                              return;
                          const result: SideNavigationProps.Item[] = [...this.state.sideNavItems];
                          result.push({
                              type: "divider",
                          });
                          if (hasProjects.canCreateSession) {
                              result.push({
                                  type: "section",
                                  text: "Session Management",
                                  defaultExpanded: true,
                                  items: [
                                      {
                                        type: "link",
                                        text: "Sessions",
                                        href: "#/virtual-desktop/sessions",
                                      }
                                  ]
                              });
                          }
                          result.push({
                              type: "section",
                              text: "Environment Management",
                              defaultExpanded: true,
                              items: [
                                  {
                                      type: "link",
                                      text: "Projects",
                                      href: "#/cluster/projects",
                                  }
                              ]
                          });
                          this.setState( { sideNavItems: result, hasProjects: hasProjects.isInProject });
                      });
                    }
                    this.setState({
                        isInitialized: true,
                        isLoggedIn: loginStatus,
                        sideNavHeader: IdeaSideNavHeader(context),
                        sideNavItems: IdeaSideNavItems(context),
                    });
                    context.setHooks(this.onLogin, this.onLogout);
                };

                if (loginStatus) {
                    context
                        .getClusterSettingsService()
                        .initialize()
                        .then((_) => {
                            init();
                        });
                } else {
                    init();
                }
            })
            .catch((error) => {
                console.error(error);
                this.setState({
                    isInitialized: true,
                    isLoggedIn: false,
                });
            });
    }

    onLogin = (): Promise<boolean> => {
        return new Promise((resolve, reject) => {
            const context = AppContext.get();
            context
                .getClusterSettingsService()
                .initialize()
                .then((_) => {
                    this.setState(
                        {
                            isLoggedIn: true,
                            sideNavHeader: IdeaSideNavHeader(context),
                            sideNavItems: IdeaSideNavItems(context),
                        },
                        () => {
                            resolve(true);
                        }
                    );
                })
                .catch((error) => {
                    console.error(error);
                    reject(false);
                });
        });
    };

    onLogout = (): Promise<boolean> => {
        return new Promise((resolve, _) => {
            this.setState(
                {
                    isLoggedIn: false,
                },
                () => {
                    applyDensity(Density.Comfortable);
                    applyMode(Mode.Light);
                    resolve(true);
                }
            );
        });
    };

    onRoute = (path: string) => {
        this.props.navigate(path);
    };

    onSideNavChange = (event: NonCancelableCustomEvent<SideNavigationProps.ChangeDetail>) => {
        const items = this.state.sideNavItems;
        items.forEach((item) => {
            if (item.type === "section") {
                if (item.text === event.detail.item.text) {
                    item.defaultExpanded = event.detail.expanded;
                }
            }
        });
        this.setState({
            sideNavItems: [...items],
        });
    };

    fetchContextHelp = (pageId: string) => {
        let helpContent = require(`./docs/${pageId}.md`);
        let footer = require(`./docs/_footer.md`);
        fetch(helpContent).then((helpContentResponse) => {
            fetch(footer).then((footerResponse) => {
                helpContentResponse.text().then((content) => {
                    footerResponse.text().then((footerContent) => {
                        let lines = content.split("\n");
                        if (lines.length === 0) {
                            return;
                        }
                        const header = lines[0];
                        const children = lines.splice(1).join("\n");
                        this.setState({
                            tools: <HelpPanel header={<ReactMarkdown children={header} />} children={<ReactMarkdown children={children} remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]} />} footer={<ReactMarkdown children={footerContent} remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]} />} />,
                        });
                    });
                });
            });
        });
    };

    onPageChange = (event: OnPageChangeEvent) => {
        if (this.state.toolsOpen) {
            this.setState(
                {
                    tools: (
                        <Box textAlign={"center"} margin={"xxxl"}>
                            <StatusIndicator type="loading" />
                        </Box>
                    ),
                },
                () => {
                    this.fetchContextHelp(event.pageId);
                }
            );
        }
        if (this.state.flashbarItems.length > 0) {
            this.setState({
                flashbarItems: [],
            });
        }
    };

    onToolsChange = (event: OnToolsChangeEvent) => {
        this.setState(
            {
                toolsOpen: event.open,
                tools: event.open ? (
                    <Box textAlign={"center"} margin={"xxxl"}>
                        <StatusIndicator type="loading" />
                    </Box>
                ) : null,
            },
            () => {
                this.fetchContextHelp(event.pageId);
            }
        );
    };

    onFlashbarChange = (event: OnFlashbarChangeEvent) => {
        let items: FlashbarProps.MessageDefinition[] = [];
        if (typeof event.append !== "undefined" && event.append) {
            this.state.flashbarItems.forEach((item) => {
                items.push(item);
            });
        }
        event.items.forEach((item, index) => {
            item.id = Utils.getUUID();
            if (item.dismissible) {
                // create a closure to retain the index
                const dismiss = (id: string) => {
                    return () => {
                        let updatedItems = [...this.state.flashbarItems];
                        updatedItems = updatedItems.filter((item) => item.id !== id);
                        this.setState({
                            flashbarItems: updatedItems,
                        });
                    };
                };
                item.onDismiss = dismiss(item.id!);
            }
            items.push(item);
        });
        this.setState({
            flashbarItems: items,
        });
    };

    render() {
        return (
            this.state.isInitialized && (
                <Routes>
                    {/*authentication pages*/}
                    <Route
                        path="/auth/login"
                        element={
                            <IdeaAuthenticatedRoute path="/auth/login" isLoggedIn={this.state.isLoggedIn}>
                                <IdeaAuthLogin />
                            </IdeaAuthenticatedRoute>
                        }
                    />
                    <Route
                        path="/auth/login-redirect"
                        element={
                            <IdeaAuthenticatedRoute path="/auth/login-redirect" isLoggedIn={this.state.isLoggedIn}>
                                <IdeaAuthLoginRedirect />
                            </IdeaAuthenticatedRoute>
                        }
                    />
                    <Route
                        path="/auth/forgot-password"
                        element={
                            <IdeaAuthenticatedRoute path="/auth/forgot-password" isLoggedIn={this.state.isLoggedIn}>
                                <IdeaAuthForgotPassword />
                            </IdeaAuthenticatedRoute>
                        }
                    />
                    <Route
                        path="/auth/confirm-forgot-password"
                        element={
                            <IdeaAuthenticatedRoute path="/auth/confirm-forgot-password" isLoggedIn={this.state.isLoggedIn}>
                                <IdeaAuthConfirmForgotPassword />
                            </IdeaAuthenticatedRoute>
                        }
                    />
                    <Route
                        path="/auth/challenge"
                        element={
                            <IdeaAuthenticatedRoute isLoggedIn={this.state.isLoggedIn}>
                                <IdeaAuthChallenge />
                            </IdeaAuthenticatedRoute>
                        }
                    />

                    {/*home*/}
                    <Route
                        path="/"
                        element={
                            <IdeaAuthenticatedRoute isLoggedIn={this.state.isLoggedIn}>
                                <Home
                                    ideaPageId="home"
                                    toolsOpen={this.state.toolsOpen}
                                    tools={this.state.tools}
                                    onToolsChange={this.onToolsChange}
                                    onPageChange={this.onPageChange}
                                    sideNavItems={this.state.sideNavItems}
                                    sideNavHeader={this.state.sideNavHeader}
                                    onSideNavChange={this.onSideNavChange}
                                    onFlashbarChange={this.onFlashbarChange}
                                    flashbarItems={this.state.flashbarItems}
                                />
                            </IdeaAuthenticatedRoute>
                        }
                    />

                    <Route
                        path="/dashboard"
                        element={
                            <IdeaAuthenticatedRoute isLoggedIn={this.state.isLoggedIn}>
                                <DashboardMain
                                    ideaPageId="dashboard"
                                    toolsOpen={this.state.toolsOpen}
                                    tools={this.state.tools}
                                    onToolsChange={this.onToolsChange}
                                    onPageChange={this.onPageChange}
                                    sideNavItems={this.state.sideNavItems}
                                    sideNavHeader={this.state.sideNavHeader}
                                    onSideNavChange={this.onSideNavChange}
                                    onFlashbarChange={this.onFlashbarChange}
                                    flashbarItems={this.state.flashbarItems}
                                />
                            </IdeaAuthenticatedRoute>
                        }
                    />

                    {/*account settings*/}
                    <Route
                        path="/home/account-settings"
                        element={
                            <IdeaAuthenticatedRoute isLoggedIn={this.state.isLoggedIn}>
                                <AccountSettings
                                    ideaPageId="account-settings"
                                    toolsOpen={this.state.toolsOpen}
                                    tools={this.state.tools}
                                    onToolsChange={this.onToolsChange}
                                    onPageChange={this.onPageChange}
                                    sideNavItems={this.state.sideNavItems}
                                    sideNavHeader={this.state.sideNavHeader}
                                    onSideNavChange={this.onSideNavChange}
                                    onFlashbarChange={this.onFlashbarChange}
                                    flashbarItems={this.state.flashbarItems}
                                />
                            </IdeaAuthenticatedRoute>
                        }
                    />

                    {/*user home*/}
                    <Route
                        path="/home/virtual-desktops"
                        element={
                            <IdeaAuthenticatedRoute isLoggedIn={this.state.isLoggedIn}>
                                <MyVirtualDesktopSessions
                                    ideaPageId="my-virtual-desktop-sessions"
                                    toolsOpen={this.state.toolsOpen}
                                    tools={this.state.tools}
                                    onToolsChange={this.onToolsChange}
                                    onPageChange={this.onPageChange}
                                    sideNavItems={this.state.sideNavItems}
                                    sideNavHeader={this.state.sideNavHeader}
                                    onSideNavChange={this.onSideNavChange}
                                    onFlashbarChange={this.onFlashbarChange}
                                    flashbarItems={this.state.flashbarItems}
                                />
                            </IdeaAuthenticatedRoute>
                        }
                    />
                    <Route
                        path="/home/shared-desktops"
                        element={
                            <IdeaAuthenticatedRoute isLoggedIn={this.state.isLoggedIn}>
                                <MySharedVirtualDesktopSessions
                                    ideaPageId="my-shared-virtual-desktop-sessions"
                                    toolsOpen={this.state.toolsOpen}
                                    tools={this.state.tools}
                                    onToolsChange={this.onToolsChange}
                                    onPageChange={this.onPageChange}
                                    sideNavItems={this.state.sideNavItems}
                                    sideNavHeader={this.state.sideNavHeader}
                                    onSideNavChange={this.onSideNavChange}
                                    onFlashbarChange={this.onFlashbarChange}
                                    flashbarItems={this.state.flashbarItems}
                                />
                            </IdeaAuthenticatedRoute>
                        }
                    />
                    <Route
                        path="/home/file-browser"
                        element={
                            <IdeaAuthenticatedRoute isLoggedIn={this.state.isLoggedIn}>
                                <SocaFileBrowser
                                    ideaPageId="file-browser"
                                    toolsOpen={this.state.toolsOpen}
                                    tools={this.state.tools}
                                    onToolsChange={this.onToolsChange}
                                    onPageChange={this.onPageChange}
                                    sideNavItems={this.state.sideNavItems}
                                    sideNavHeader={this.state.sideNavHeader}
                                    onSideNavChange={this.onSideNavChange}
                                    onFlashbarChange={this.onFlashbarChange}
                                    flashbarItems={this.state.flashbarItems}
                                />
                            </IdeaAuthenticatedRoute>
                        }
                    />
                    <Route
                        path="/home/file-browser/tail"
                        element={
                            <IdeaAuthenticatedRoute isLoggedIn={this.state.isLoggedIn}>
                                <IdeaLogTail
                                    ideaPageId="log-tail"
                                    toolsOpen={this.state.toolsOpen}
                                    tools={this.state.tools}
                                    onToolsChange={this.onToolsChange}
                                    onPageChange={this.onPageChange}
                                    sideNavItems={this.state.sideNavItems}
                                    sideNavHeader={this.state.sideNavHeader}
                                    onSideNavChange={this.onSideNavChange}
                                    onFlashbarChange={this.onFlashbarChange}
                                    flashbarItems={this.state.flashbarItems}
                                />
                            </IdeaAuthenticatedRoute>
                        }
                    />
                    <Route
                        path="/home/ssh-access"
                        element={
                            <IdeaAuthenticatedRoute isLoggedIn={this.state.isLoggedIn}>
                                <SSHAccess
                                    ideaPageId="ssh-access"
                                    toolsOpen={this.state.toolsOpen}
                                    tools={this.state.tools}
                                    onToolsChange={this.onToolsChange}
                                    onPageChange={this.onPageChange}
                                    sideNavItems={this.state.sideNavItems}
                                    sideNavHeader={this.state.sideNavHeader}
                                    onSideNavChange={this.onSideNavChange}
                                    onFlashbarChange={this.onFlashbarChange}
                                    flashbarItems={this.state.flashbarItems}
                                />
                            </IdeaAuthenticatedRoute>
                        }
                    />

                    {/*virtual desktop*/}
                    <Route
                        path="/virtual-desktop/dashboard"
                        element={
                            <IdeaAuthenticatedRoute isLoggedIn={this.state.isLoggedIn}>
                                <VirtualDesktopDashboard
                                    ideaPageId="virtual-desktop-dashboard"
                                    toolsOpen={this.state.toolsOpen}
                                    tools={this.state.tools}
                                    onToolsChange={this.onToolsChange}
                                    onPageChange={this.onPageChange}
                                    sideNavItems={this.state.sideNavItems}
                                    sideNavHeader={this.state.sideNavHeader}
                                    onSideNavChange={this.onSideNavChange}
                                    onFlashbarChange={this.onFlashbarChange}
                                    flashbarItems={this.state.flashbarItems}
                                />
                            </IdeaAuthenticatedRoute>
                        }
                    />
                    <Route
                        path="/virtual-desktop/sessions/:idea_session_id"
                        element={
                            <IdeaAuthenticatedRoute isLoggedIn={this.state.isLoggedIn}>
                                <VirtualDesktopSessionDetail
                                    ideaPageId="virtual-desktop-session-detail"
                                    toolsOpen={this.state.toolsOpen}
                                    tools={this.state.tools}
                                    onToolsChange={this.onToolsChange}
                                    onPageChange={this.onPageChange}
                                    sideNavItems={this.state.sideNavItems}
                                    sideNavHeader={this.state.sideNavHeader}
                                    onSideNavChange={this.onSideNavChange}
                                    onFlashbarChange={this.onFlashbarChange}
                                    flashbarItems={this.state.flashbarItems}
                                />
                            </IdeaAuthenticatedRoute>
                        }
                    />
                    <Route
                        path="/virtual-desktop/sessions"
                        element={
                            <IdeaAuthenticatedRoute isLoggedIn={this.state.isLoggedIn} isProjectOwner={this.state.hasProjects}>
                                <VirtualDesktopSessions
                                    ideaPageId="virtual-desktop-sessions"
                                    toolsOpen={this.state.toolsOpen}
                                    tools={this.state.tools}
                                    onToolsChange={this.onToolsChange}
                                    onPageChange={this.onPageChange}
                                    sideNavItems={this.state.sideNavItems}
                                    sideNavHeader={this.state.sideNavHeader}
                                    onSideNavChange={this.onSideNavChange}
                                    onFlashbarChange={this.onFlashbarChange}
                                    flashbarItems={this.state.flashbarItems}
                                />
                            </IdeaAuthenticatedRoute>
                        }
                    />
                    <Route
                        path="/virtual-desktop/software-stacks"
                        element={
                            <IdeaAuthenticatedRoute isLoggedIn={this.state.isLoggedIn}>
                                <VirtualDesktopSoftwareStacks
                                    ideaPageId="virtual-desktop-software-stacks"
                                    toolsOpen={this.state.toolsOpen}
                                    tools={this.state.tools}
                                    onToolsChange={this.onToolsChange}
                                    onPageChange={this.onPageChange}
                                    sideNavItems={this.state.sideNavItems}
                                    sideNavHeader={this.state.sideNavHeader}
                                    onSideNavChange={this.onSideNavChange}
                                    onFlashbarChange={this.onFlashbarChange}
                                    flashbarItems={this.state.flashbarItems}
                                />
                            </IdeaAuthenticatedRoute>
                        }
                    />
                    <Route
                        path="/virtual-desktop/software-stacks/:software_stack_id/:software_stack_base_os"
                        element={
                            <IdeaAuthenticatedRoute isLoggedIn={this.state.isLoggedIn}>
                                <VirtualDesktopSoftwareStackDetail
                                    ideaPageId="virtual-desktop-software-stack-detail"
                                    toolsOpen={this.state.toolsOpen}
                                    tools={this.state.tools}
                                    onToolsChange={this.onToolsChange}
                                    onPageChange={this.onPageChange}
                                    sideNavItems={this.state.sideNavItems}
                                    sideNavHeader={this.state.sideNavHeader}
                                    onSideNavChange={this.onSideNavChange}
                                    onFlashbarChange={this.onFlashbarChange}
                                    flashbarItems={this.state.flashbarItems}
                                />
                            </IdeaAuthenticatedRoute>
                        }
                    />
                    <Route
                        path="/virtual-desktop/settings"
                        element={
                            <IdeaAuthenticatedRoute isLoggedIn={this.state.isLoggedIn}>
                                <VirtualDesktopSettings
                                    ideaPageId="virtual-desktop-settings"
                                    toolsOpen={this.state.toolsOpen}
                                    tools={this.state.tools}
                                    onToolsChange={this.onToolsChange}
                                    onPageChange={this.onPageChange}
                                    sideNavItems={this.state.sideNavItems}
                                    sideNavHeader={this.state.sideNavHeader}
                                    onSideNavChange={this.onSideNavChange}
                                    onFlashbarChange={this.onFlashbarChange}
                                    flashbarItems={this.state.flashbarItems}
                                />
                            </IdeaAuthenticatedRoute>
                        }
                    />
                    <Route
                        path="/virtual-desktop/debug"
                        element={
                            <IdeaAuthenticatedRoute isLoggedIn={this.state.isLoggedIn}>
                                <VirtualDesktopDebug
                                    ideaPageId="virtual-desktop-debug"
                                    toolsOpen={this.state.toolsOpen}
                                    tools={this.state.tools}
                                    onToolsChange={this.onToolsChange}
                                    onPageChange={this.onPageChange}
                                    sideNavItems={this.state.sideNavItems}
                                    sideNavHeader={this.state.sideNavHeader}
                                    onSideNavChange={this.onSideNavChange}
                                    onFlashbarChange={this.onFlashbarChange}
                                    flashbarItems={this.state.flashbarItems}
                                />
                            </IdeaAuthenticatedRoute>
                        }
                    />
                    <Route
                        path="/virtual-desktop/permission-profiles/:profile_id"
                        element={
                            <IdeaAuthenticatedRoute isLoggedIn={this.state.isLoggedIn}>
                                <VirtualDesktopPermissionProfileDetail
                                    ideaPageId="virtual-desktop-permission-profile-detail"
                                    toolsOpen={this.state.toolsOpen}
                                    tools={this.state.tools}
                                    onToolsChange={this.onToolsChange}
                                    onPageChange={this.onPageChange}
                                    sideNavItems={this.state.sideNavItems}
                                    sideNavHeader={this.state.sideNavHeader}
                                    onSideNavChange={this.onSideNavChange}
                                    onFlashbarChange={this.onFlashbarChange}
                                    flashbarItems={this.state.flashbarItems}
                                />
                            </IdeaAuthenticatedRoute>
                        }
                    />
                    <Route
                        path="/virtual-desktop/permission-profiles"
                        element={
                            <IdeaAuthenticatedRoute isLoggedIn={this.state.isLoggedIn}>
                                <VirtualDesktopPermissionProfiles
                                    ideaPageId="virtual-desktop-permission-profiles"
                                    toolsOpen={this.state.toolsOpen}
                                    tools={this.state.tools}
                                    onToolsChange={this.onToolsChange}
                                    onPageChange={this.onPageChange}
                                    sideNavItems={this.state.sideNavItems}
                                    sideNavHeader={this.state.sideNavHeader}
                                    onSideNavChange={this.onSideNavChange}
                                    onFlashbarChange={this.onFlashbarChange}
                                    flashbarItems={this.state.flashbarItems}
                                />
                            </IdeaAuthenticatedRoute>
                        }
                    />
                    {/* environment */}
                    <Route
                        path="/cluster/projects"
                        element={
                            <IdeaAuthenticatedRoute isLoggedIn={this.state.isLoggedIn} isProjectOwner={this.state.hasProjects || false}>
                                <Projects
                                    ideaPageId="projects"
                                    toolsOpen={this.state.toolsOpen}
                                    tools={this.state.tools}
                                    onToolsChange={this.onToolsChange}
                                    onPageChange={this.onPageChange}
                                    sideNavItems={this.state.sideNavItems}
                                    sideNavHeader={this.state.sideNavHeader}
                                    onSideNavChange={this.onSideNavChange}
                                    onFlashbarChange={this.onFlashbarChange}
                                    flashbarItems={this.state.flashbarItems}
                                    projectOwnerRoles={this.state.projectOwnerRoles}
                                />
                            </IdeaAuthenticatedRoute>
                        }
                    />
                     <Route
                        path="/cluster/projects/configure"
                        element={
                            <IdeaAuthenticatedRoute isLoggedIn={this.state.isLoggedIn} isProjectOwner={this.state.hasProjects}>
                                <ConfigureProject
                                    ideaPageId="configure-project"
                                    toolsOpen={this.state.toolsOpen}
                                    tools={this.state.tools}
                                    onToolsChange={this.onToolsChange}
                                    onPageChange={this.onPageChange}
                                    sideNavItems={this.state.sideNavItems}
                                    sideNavHeader={this.state.sideNavHeader}
                                    onSideNavChange={this.onSideNavChange}
                                    onFlashbarChange={this.onFlashbarChange}
                                    flashbarItems={this.state.flashbarItems}
                                />
                            </IdeaAuthenticatedRoute>
                        }
                    />
                    <Route
                        path="/cluster/users"
                        element={
                            <IdeaAuthenticatedRoute isLoggedIn={this.state.isLoggedIn}>
                                <Users
                                    ideaPageId="users"
                                    toolsOpen={this.state.toolsOpen}
                                    tools={this.state.tools}
                                    onToolsChange={this.onToolsChange}
                                    onPageChange={this.onPageChange}
                                    sideNavItems={this.state.sideNavItems}
                                    sideNavHeader={this.state.sideNavHeader}
                                    onSideNavChange={this.onSideNavChange}
                                    onFlashbarChange={this.onFlashbarChange}
                                    flashbarItems={this.state.flashbarItems}
                                />
                            </IdeaAuthenticatedRoute>
                        }
                    />
                    <Route
                        path="/cluster/groups"
                        element={
                            <IdeaAuthenticatedRoute isLoggedIn={this.state.isLoggedIn}>
                                <Groups
                                    ideaPageId="groups"
                                    toolsOpen={this.state.toolsOpen}
                                    tools={this.state.tools}
                                    onToolsChange={this.onToolsChange}
                                    onPageChange={this.onPageChange}
                                    sideNavItems={this.state.sideNavItems}
                                    sideNavHeader={this.state.sideNavHeader}
                                    onSideNavChange={this.onSideNavChange}
                                    onFlashbarChange={this.onFlashbarChange}
                                    flashbarItems={this.state.flashbarItems}
                                />
                            </IdeaAuthenticatedRoute>
                        }
                    />
                    <Route
                        path="/cluster/filesystem"
                        element={
                            <IdeaAuthenticatedRoute isLoggedIn={this.state.isLoggedIn}>
                                <FileSystems
                                    ideaPageId="filesystem"
                                    toolsOpen={this.state.toolsOpen}
                                    tools={this.state.tools}
                                    onToolsChange={this.onToolsChange}
                                    onPageChange={this.onPageChange}
                                    sideNavItems={this.state.sideNavItems}
                                    sideNavHeader={this.state.sideNavHeader}
                                    onSideNavChange={this.onSideNavChange}
                                    onFlashbarChange={this.onFlashbarChange}
                                    flashbarItems={this.state.flashbarItems}
                                />
                            </IdeaAuthenticatedRoute>
                        }
                    />
                    <Route
                        path="/cluster/s3-bucket"
                        element={
                            <IdeaAuthenticatedRoute isLoggedIn={this.state.isLoggedIn}>
                                <S3Buckets
                                    ideaPageId="s3-bucket"
                                    toolsOpen={this.state.toolsOpen}
                                    tools={this.state.tools}
                                    onToolsChange={this.onToolsChange}
                                    onPageChange={this.onPageChange}
                                    sideNavItems={this.state.sideNavItems}
                                    sideNavHeader={this.state.sideNavHeader}
                                    onSideNavChange={this.onSideNavChange}
                                    onFlashbarChange={this.onFlashbarChange}
                                    flashbarItems={this.state.flashbarItems}
                                />
                            </IdeaAuthenticatedRoute>
                        }
                    />
                    <Route
                        path="/cluster/s3-bucket/add-bucket"
                        element={
                            <IdeaAuthenticatedRoute isLoggedIn={this.state.isLoggedIn}>
                                <AddS3Bucket
                                    ideaPageId="add-bucket"
                                    toolsOpen={this.state.toolsOpen}
                                    tools={this.state.tools}
                                    onToolsChange={this.onToolsChange}
                                    onPageChange={this.onPageChange}
                                    sideNavItems={this.state.sideNavItems}
                                    sideNavHeader={this.state.sideNavHeader}
                                    onSideNavChange={this.onSideNavChange}
                                    onFlashbarChange={this.onFlashbarChange}
                                    flashbarItems={this.state.flashbarItems}
                                />
                            </IdeaAuthenticatedRoute>
                        }
                    />
                    <Route
                        path="/cluster/s3-bucket/edit-bucket"
                        element={
                            <IdeaAuthenticatedRoute isLoggedIn={this.state.isLoggedIn}>
                                <EditS3Bucket
                                    ideaPageId="edit-bucket"
                                    toolsOpen={this.state.toolsOpen}
                                    tools={this.state.tools}
                                    onToolsChange={this.onToolsChange}
                                    onPageChange={this.onPageChange}
                                    sideNavItems={this.state.sideNavItems}
                                    sideNavHeader={this.state.sideNavHeader}
                                    onSideNavChange={this.onSideNavChange}
                                    onFlashbarChange={this.onFlashbarChange}
                                    flashbarItems={this.state.flashbarItems}
                                />
                            </IdeaAuthenticatedRoute>
                        }
                    />
                    <Route
                        path="/cluster/permission-profiles"
                        element={
                            <IdeaAuthenticatedRoute isLoggedIn={this.state.isLoggedIn}>
                                <PermissionProfilesDashboard
                                    ideaPageId="permission-profiles"
                                    toolsOpen={this.state.toolsOpen}
                                    tools={this.state.tools}
                                    onToolsChange={this.onToolsChange}
                                    onPageChange={this.onPageChange}
                                    sideNavItems={this.state.sideNavItems}
                                    sideNavHeader={this.state.sideNavHeader}
                                    onSideNavChange={this.onSideNavChange}
                                    onFlashbarChange={this.onFlashbarChange}
                                    flashbarItems={this.state.flashbarItems}
                                />
                            </IdeaAuthenticatedRoute>
                        }
                    />
                    <Route
                        path="/cluster/permission-profiles/:profile_id"
                        element={
                            <IdeaAuthenticatedRoute isLoggedIn={this.state.isLoggedIn}>
                                <PermissionProfilesView
                                    ideaPageId="permission-profiles-view-detail"
                                    toolsOpen={this.state.toolsOpen}
                                    tools={this.state.tools}
                                    onToolsChange={this.onToolsChange}
                                    onPageChange={this.onPageChange}
                                    sideNavItems={this.state.sideNavItems}
                                    sideNavHeader={this.state.sideNavHeader}
                                    onSideNavChange={this.onSideNavChange}
                                    onFlashbarChange={this.onFlashbarChange}
                                    flashbarItems={this.state.flashbarItems}
                                />
                            </IdeaAuthenticatedRoute>
                        }
                    />
                    <Route
                        path="/cluster/permission-profiles/configure"
                        element={
                            <IdeaAuthenticatedRoute isLoggedIn={this.state.isLoggedIn}>
                                <ConfigurePermissionProfile
                                    ideaPageId="permission-profiles-configure"
                                    toolsOpen={this.state.toolsOpen}
                                    tools={this.state.tools}
                                    onToolsChange={this.onToolsChange}
                                    onPageChange={this.onPageChange}
                                    sideNavItems={this.state.sideNavItems}
                                    sideNavHeader={this.state.sideNavHeader}
                                    onSideNavChange={this.onSideNavChange}
                                    onFlashbarChange={this.onFlashbarChange}
                                    flashbarItems={this.state.flashbarItems}
                                />
                            </IdeaAuthenticatedRoute>
                        }
                    />
                    <Route
                        path="/cluster/status"
                        element={
                            <IdeaAuthenticatedRoute isLoggedIn={this.state.isLoggedIn}>
                                <ClusterStatus
                                    ideaPageId="cluster-status"
                                    toolsOpen={this.state.toolsOpen}
                                    tools={this.state.tools}
                                    onToolsChange={this.onToolsChange}
                                    onPageChange={this.onPageChange}
                                    sideNavItems={this.state.sideNavItems}
                                    sideNavHeader={this.state.sideNavHeader}
                                    onSideNavChange={this.onSideNavChange}
                                    onFlashbarChange={this.onFlashbarChange}
                                    flashbarItems={this.state.flashbarItems}
                                />
                            </IdeaAuthenticatedRoute>
                        }
                    />
                    {/*<Route*/}
                    {/*    path="/cluster/email-templates"*/}
                    {/*    element={*/}
                    {/*        <IdeaAuthenticatedRoute isLoggedIn={this.state.isLoggedIn}>*/}
                    {/*            <EmailTemplates*/}
                    {/*                ideaPageId="email-templates"*/}
                    {/*                toolsOpen={this.state.toolsOpen}*/}
                    {/*                tools={this.state.tools}*/}
                    {/*                onToolsChange={this.onToolsChange}*/}
                    {/*                onPageChange={this.onPageChange}*/}
                    {/*                sideNavItems={this.state.sideNavItems}*/}
                    {/*                sideNavHeader={this.state.sideNavHeader}*/}
                    {/*                onSideNavChange={this.onSideNavChange}*/}
                    {/*                onFlashbarChange={this.onFlashbarChange}*/}
                    {/*                flashbarItems={this.state.flashbarItems}*/}
                    {/*            />*/}
                    {/*        </IdeaAuthenticatedRoute>*/}
                    {/*    }*/}
                    {/*/>*/}
                    <Route
                        path="/cluster/snapshot-management"
                        element={
                            <IdeaAuthenticatedRoute isLoggedIn={this.state.isLoggedIn}>
                                <SnapshotManagement
                                    ideaPageId="snapshot-management"
                                    toolsOpen={this.state.toolsOpen}
                                    tools={this.state.tools}
                                    onToolsChange={this.onToolsChange}
                                    onPageChange={this.onPageChange}
                                    sideNavItems={this.state.sideNavItems}
                                    sideNavHeader={this.state.sideNavHeader}
                                    onSideNavChange={this.onSideNavChange}
                                    onFlashbarChange={this.onFlashbarChange}
                                    flashbarItems={this.state.flashbarItems}
                                />
                            </IdeaAuthenticatedRoute>
                        }
                    />
                    <Route
                        path="/cluster/settings"
                        element={
                            <IdeaAuthenticatedRoute isLoggedIn={this.state.isLoggedIn}>
                                <ClusterSettings
                                    ideaPageId="cluster-settings"
                                    toolsOpen={this.state.toolsOpen}
                                    tools={this.state.tools}
                                    onToolsChange={this.onToolsChange}
                                    onPageChange={this.onPageChange}
                                    sideNavItems={this.state.sideNavItems}
                                    sideNavHeader={this.state.sideNavHeader}
                                    onSideNavChange={this.onSideNavChange}
                                    onFlashbarChange={this.onFlashbarChange}
                                    flashbarItems={this.state.flashbarItems}
                                />
                            </IdeaAuthenticatedRoute>
                        }
                    />

                    <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
            )
        );
    }
}

export default withRouter(IdeaWebPortalApp);
