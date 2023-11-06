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

export interface IdeaConfirmProps {
    title: string;
    confirmLabel?: string;
    onConfirm?: () => void;
    cancelLabel?: string;
    onCancel?: () => void;
    children: React.ReactNode;
}

export interface IdeaConfirmState {
    showModal: boolean;
}

class IdeaConfirm extends Component<IdeaConfirmProps, IdeaConfirmState> {
    constructor(props: IdeaConfirmProps) {
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
                if (this.props.onCancel) {
                    this.props.onCancel();
                }
            }
        );
    }

    getConfirmLabel() {
        if (this.props.confirmLabel) {
            return this.props.confirmLabel;
        }
        return "Yes";
    }

    getCancelLabel() {
        if (this.props.cancelLabel) {
            return this.props.cancelLabel;
        }
        return "Cancel";
    }

    render() {
        return (
            <Modal
                visible={this.state.showModal}
                onDismiss={() => {
                    this.hide();
                }}
                header={<Header variant="h3">{this.props.title}</Header>}
                footer={
                    <Box float="right">
                        <SpaceBetween size="xs" direction="horizontal">
                            <Button
                                variant="link"
                                onClick={() => {
                                    this.hide();
                                }}
                            >
                                {this.getCancelLabel()}
                            </Button>
                            <Button
                                variant="primary"
                                onClick={() => {
                                    this.hide();
                                    if (this.props.onConfirm) {
                                        this.props.onConfirm();
                                    }
                                }}
                            >
                                {this.getConfirmLabel()}
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

export default IdeaConfirm;
