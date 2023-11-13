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
import { Box, BreadcrumbGroup, Flashbar, SpaceBetween } from "@cloudscape-design/components";
import { AppContext } from "../../common";
import AppLayout from "@cloudscape-design/components/app-layout";
import { NonCancelableEventHandler } from "@cloudscape-design/components/internal/events";
import { AppLayoutProps } from "@cloudscape-design/components/app-layout/interfaces";
import { BreadcrumbGroupProps } from "@cloudscape-design/components/breadcrumb-group/interfaces";
import { OnFlashbarChangeEvent, OnPageChangeEvent, OnToolsChangeEvent } from "../../App";
import { FlashbarProps } from "@cloudscape-design/components/flashbar/interfaces";
import { withRouter } from "../../navigation/navigation-utils";
import IdeaSideNavigation, { IdeaSideNavigationProps } from "../side-navigation";
import IdeaNavbar from "../navbar";
import Utils from "../../common/utils";

export interface IdeaAppLayoutProps extends IdeaSideNavigationProps {
    ideaPageId: string;
    contentType?: AppLayoutProps.ContentType;
    header?: React.ReactNode;
    content?: React.ReactNode;
    disableContentHeaderOverlap?: boolean;
    navigation?: React.ReactNode;
    breadcrumbItems?: BreadcrumbGroupProps.Item[];
    splitPanel?: React.ReactNode;
    toolsOpen: boolean;
    tools: React.ReactNode;
    onToolsChange: (event: OnToolsChangeEvent) => void;
    onPageChange: (event: OnPageChangeEvent) => void;
    splitPanelSize?: number;
    splitPanelOpen?: boolean;
    splitPanelPreferences?: AppLayoutProps.SplitPanelPreferences;
    onSplitPanelResize?: NonCancelableEventHandler<AppLayoutProps.SplitPanelResizeDetail>;
    onSplitPanelToggle?: NonCancelableEventHandler<AppLayoutProps.ChangeDetail>;
    onSplitPanelPreferencesChange?: NonCancelableEventHandler<AppLayoutProps.SplitPanelPreferences>;
    onFlashbarChange: (event: OnFlashbarChangeEvent) => void;
    flashbarItems: FlashbarProps.MessageDefinition[];
    sideNavActivePath?: string;
}

export interface IdeaAppLayoutState {}

class IdeaAppLayout extends Component<IdeaAppLayoutProps, IdeaAppLayoutState> {
    componentDidMount() {
        Utils.hideLoadingAnimation();

        this.props.onPageChange({
            pageId: this.props.ideaPageId,
        });
    }

    buildBreadCrumbs() {
        let items = this.props.breadcrumbItems;
        if (!items) {
            return null;
        }
        return <BreadcrumbGroup items={items} ariaLabel="Breadcrumbs" />;
    }

    buildNotifications() {
        return <Flashbar items={this.props.flashbarItems} />;
    }

    buildFooter() {
        return (
            <footer className="soca-app-footer">
                <Box textAlign="center">
                    <SpaceBetween direction="vertical" size="xxxs">
                        <span>{AppContext.get().getCopyRightText()}</span>
                        <span>
                            <small>
                                <b>Release:</b> v{AppContext.get().releaseVersion()}
                                &nbsp;v{AppContext.get().releaseVersion()}
                            </small>
                        </span>
                    </SpaceBetween>
                </Box>
            </footer>
        );
    }

    render() {
        return (
            <div>
                <div id="h" style={{ position: "sticky", top: 0, zIndex: 1002 }}>
                    <IdeaNavbar />
                </div>
                <AppLayout
                    headerSelector="#h"
                    navigation={
                        <IdeaSideNavigation
                            sideNavHeader={this.props.sideNavHeader}
                            sideNavItems={this.props.sideNavItems}
                            onSideNavChange={this.props.onSideNavChange}
                            activePath={this.props.sideNavActivePath}
                            navigate={this.props.navigate}
                            location={this.props.location}
                            params={this.props.params}
                            searchParams={this.props.searchParams}
                            setSearchParams={this.props.setSearchParams}
                        />
                    }
                    contentHeader={this.props.header}
                    breadcrumbs={this.buildBreadCrumbs()}
                    stickyNotifications={true}
                    notifications={this.buildNotifications()}
                    disableContentHeaderOverlap={typeof this.props.disableContentHeaderOverlap !== "undefined" ? this.props.disableContentHeaderOverlap : false}
                    content={
                        <section>
                            <main className="soca-app-content">{this.props.content}</main>
                        </section>
                    }
                    contentType={this.props.contentType ? this.props.contentType : "table"}
                    tools={this.props.tools}
                    toolsOpen={this.props.toolsOpen}
                    onToolsChange={(event) => {
                        if (this.props.onToolsChange) {
                            this.props.onToolsChange({
                                open: event.detail.open,
                                pageId: this.props.ideaPageId,
                            });
                        }
                    }}
                    splitPanel={this.props.splitPanel}
                    splitPanelSize={this.props.splitPanelSize}
                    splitPanelOpen={this.props.splitPanelOpen}
                    splitPanelPreferences={this.props.splitPanelPreferences}
                    onSplitPanelResize={this.props.onSplitPanelResize}
                    onSplitPanelToggle={this.props.onSplitPanelToggle}
                    onSplitPanelPreferencesChange={this.props.onSplitPanelPreferencesChange}
                />
            </div>
        );
    }
}

export default withRouter(IdeaAppLayout);
