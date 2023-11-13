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
import { Box, Button, Header, Modal, SpaceBetween } from "@cloudscape-design/components";
import { ButtonProps } from "@cloudscape-design/components/button/interfaces";

export interface IdeaViewProps {
    title: string;
    acknowledgeLabel?: string;
    onAcknowledge?: () => void;
    acknowledgeVariant?: ButtonProps.Variant;
    children: React.ReactNode;
}

export interface IdeaViewState {
    showModal: boolean;
}

class IdeaView extends Component<IdeaViewProps, IdeaViewState> {
    constructor(props: IdeaViewProps) {
        super(props);
        this.state = {
            showModal: false,
        };
    }

    show() {
        this.setState({
            showModal: true,
        });
    }

    hide() {
        this.setState(
            {
                showModal: false,
            },
            () => {
                if (this.props.onAcknowledge) {
                    this.props.onAcknowledge();
                }
            }
        );
    }

    getAckLabel() {
        if (this.props.acknowledgeLabel) {
            return this.props.acknowledgeLabel;
        }
        return "Ok";
    }

    render() {
        let ackVariant = this.props.acknowledgeVariant;
        if (ackVariant === undefined) {
            ackVariant = "link";
        }

        return (
            <Modal
                visible={this.state.showModal}
                onDismiss={() => {
                    this.hide();
                }}
                size={"large"}
                header={<Header variant="h3">{this.props.title}</Header>}
                footer={
                    <Box float="right">
                        <SpaceBetween size="xs" direction="horizontal">
                            <Button
                                variant={ackVariant}
                                onClick={() => {
                                    this.hide();
                                }}
                            >
                                {this.getAckLabel()}
                            </Button>
                        </SpaceBetween>
                    </Box>
                }
            >
                {this.props.children}
            </Modal>
        );
    }
}

export default IdeaView;
