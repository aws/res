import React, { Component, RefObject } from "react";

import { IdeaSideNavigationProps } from "../../components/side-navigation";
import IdeaAppLayout, { IdeaAppLayoutProps } from "../../components/app-layout";
import { Button, Container, Header, SpaceBetween } from "@cloudscape-design/components";
import { withRouter } from "../../navigation/navigation-utils";

import ApplySnapshots from "./apply-snapshot"
import Snapshots from "./snapshots"

export interface SnapshotManagementProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {}

class SnapshotManagement extends Component<SnapshotManagementProps> {

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
                        text: "Snapshot Management",
                        href: "",
                    },
                ]}
                header={
                    <Header
                        variant={"h1"}
                    >
                        Snapshot Management
                    </Header>
                }
                contentType={"default"}
                content={
                    <React.Fragment>
                        <SpaceBetween size="xxl">
                            <Snapshots
                                ideaPageId="snapshots"
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
                            <ApplySnapshots
                                ideaPageId="apply-snapshots"
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
                        </SpaceBetween>
                    </React.Fragment>
                }
            />
        )
    }
}


export default withRouter(SnapshotManagement);