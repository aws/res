import React, { Component } from "react";

import { IdeaSideNavigationProps } from "../../components/side-navigation";
import IdeaAppLayout, { IdeaAppLayoutProps } from "../../components/app-layout";
import { Alert, Header, Link, SpaceBetween, Tabs, TabsProps } from "@cloudscape-design/components";
import { withRouter } from "../../navigation/navigation-utils";

import GlobalPermissions from "./global-permissions";
import PermissionProfilesDashboard from "./permission-profiles-dashboard";
import VirtualDesktopPermissionProfiles from "./desktop-sharing-profiles-dashboard";

export interface PermissionsProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {}

export interface PermissionsState {
    activeTabId: string;
    alertVisible: boolean;
}

class Permissions extends Component<PermissionsProps, PermissionsState> {

    constructor(props: PermissionsProps) {
        super(props);
        const { state } = this.props.location
        this.state = {
            activeTabId: state?.activeTabId ?? "project-roles",
            alertVisible: true,
        };
    }

    buildTabs(): TabsProps.Tab[] {
        return [
            {
                label: "Project roles",
                id: "project-roles",
                content: <PermissionProfilesDashboard
                    ideaPageId="permission-profiles"
                    toolsOpen={this.props.toolsOpen}
                    tools={this.props.tools}
                    onToolsChange={this.props.onToolsChange}
                    onPageChange={this.props.onPageChange}
                    sideNavItems={this.props.sideNavItems}
                    sideNavHeader={this.props.sideNavHeader}
                    onSideNavChange={this.props.onSideNavChange}
                    onFlashbarChange={this.props.onFlashbarChange}
                    flashbarItems={this.props.flashbarItems}
                />
            },
            {
                label: "Desktop sharing profiles",
                id: "desktop-sharing-profiles",
                content: <VirtualDesktopPermissionProfiles
                    ideaPageId="virtual-desktop-permission-profiles"
                    toolsOpen={this.props.toolsOpen}
                    tools={this.props.tools}
                    onToolsChange={this.props.onToolsChange}
                    onPageChange={this.props.onPageChange}
                    sideNavItems={this.props.sideNavItems}
                    sideNavHeader={this.props.sideNavHeader}
                    onSideNavChange={this.props.onSideNavChange}
                    onFlashbarChange={this.props.onFlashbarChange}
                    flashbarItems={this.props.flashbarItems}
                />
            }
        ];
    }

    render() {
        return (
            <IdeaAppLayout
                ideaPageId={this.props.ideaPageId}
                toolsOpen={this.props.toolsOpen}
                tools={this.props.tools}
                onToolsChange={this.props.onToolsChange}
                onPageChange={this.props.onPageChange}
                sideNavHeader={this.props.sideNavHeader}
                sideNavItems={this.props.sideNavItems}
                onSideNavChange={this.props.onSideNavChange}
                onFlashbarChange={this.props.onFlashbarChange}
                flashbarItems={this.props.flashbarItems}
                breadcrumbItems={[
                    {
                        text: "RES",
                        href: "#/",
                    },
                    {
                        text: "Environment Management",
                        href: "#/cluster/status",
                    },
                    {
                        text: "Permission policy",
                        href: "",
                    },
                ]}
                header={
                    <SpaceBetween size="xs">
                        <Header
                            variant={"h1"}
                            description={"Manage user permissions throughout the environment."}
                        >
                            Permission policy
                        </Header>
                        {this.state.alertVisible ? <Alert
                            statusIconAriaLabel="info"
                            type="info"
                            dismissible={true}
                            onDismiss={() => {
                                this.setState({ alertVisible: false })
                            }}
                        >
                            Properly managing a comprehensive permissions policy requires understanding the cascading effects permissions can have across the environment. Before making any changes, <Link
                                onFollow={() => {
                                    this.props.onToolsChange({open: true, pageId: 'permissions'});
                                }}
                                variant="primary"
                            >read Info</Link>
                        </Alert> : true}
                    </SpaceBetween>
                }
                contentType={"default"}
                content={
                    <React.Fragment>
                        <SpaceBetween size="xxl">
                            <GlobalPermissions
                                ideaPageId="global-permissions"
                                toolsOpen={this.props.toolsOpen}
                                tools={this.props.tools}
                                onToolsChange={this.props.onToolsChange}
                                onPageChange={this.props.onPageChange}
                                sideNavItems={this.props.sideNavItems}
                                sideNavHeader={this.props.sideNavHeader}
                                onSideNavChange={this.props.onSideNavChange}
                                onFlashbarChange={this.props.onFlashbarChange}
                                flashbarItems={this.props.flashbarItems}
                            />
                            <Tabs
                                onChange={(changeEvent) => {this.setState({
                                    activeTabId: changeEvent.detail.activeTabId,
                                })}}
                                activeTabId={this.state.activeTabId}
                                tabs={this.buildTabs()}
                            />
                        </SpaceBetween>
                    </React.Fragment>
                }
            />
        )
    }
}


export default withRouter(Permissions);