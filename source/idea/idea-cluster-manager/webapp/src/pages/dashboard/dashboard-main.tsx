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
import { Container, Grid } from "@cloudscape-design/components";
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import { JobSubmissionsWidget } from "./job-submissions-widget";
import IdeaAppLayout, { IdeaAppLayoutProps } from "../../components/app-layout";
import { withRouter } from "../../navigation/navigation-utils";

export interface DashboardMainProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {}

export interface DashboardMainState {}

class DashboardMain extends Component<DashboardMainProps, DashboardMainState> {
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
                        text: "Dashboard",
                        href: "",
                    },
                ]}
                content={
                    <Container variant={"default"}>
                        <Grid gridDefinition={[{ colspan: { xxs: 12 } }]}>
                            <JobSubmissionsWidget />
                        </Grid>
                    </Container>
                }
            />
        );
    }
}

export default withRouter(DashboardMain);
