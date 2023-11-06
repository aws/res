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
import { Button, ButtonDropdown, Header, SpaceBetween, SplitPanel } from "@cloudscape-design/components";
import { ButtonDropdownProps } from "@cloudscape-design/components/button-dropdown/interfaces";

export interface IdeaSplitPanelAction {
    id: string;
    text: string;
    onClick: () => void;
    disabled?: boolean;
}

export interface IdeaSplitPanelProps {
    title: string;
    description?: string;
    children: React.ReactNode;
    primaryAction?: IdeaSplitPanelAction;
    secondaryActions?: IdeaSplitPanelAction[];
    hidePreferencesButton?: boolean;
}

export interface IdeaSplitPanelState {}

class IdeaSplitPanel extends Component<IdeaSplitPanelProps, IdeaSplitPanelState> {
    private buildActions() {
        const secondaryActions: ButtonDropdownProps.ItemOrGroup[] = [];
        if (this.props.secondaryActions) {
            this.props.secondaryActions.forEach((action) => {
                secondaryActions.push({
                    id: action.id,
                    text: action.text,
                    disabled: action.disabled,
                });
            });
        }

        return (
            <SpaceBetween direction="horizontal" size="xs">
                {secondaryActions.length > 0 && <ButtonDropdown items={secondaryActions}>Actions</ButtonDropdown>}
                {this.props.primaryAction && (
                    <Button
                        variant="normal"
                        disabled={this.props.primaryAction.disabled}
                        onClick={() => {
                            if (this.props.primaryAction?.onClick) {
                                this.props.primaryAction.onClick();
                            }
                        }}
                    >
                        {this.props.primaryAction?.text}
                    </Button>
                )}
            </SpaceBetween>
        );
    }

    render() {
        return (
            <SplitPanel
                header={this.props.title}
                hidePreferencesButton={this.props.hidePreferencesButton ? this.props.hidePreferencesButton : true}
                i18nStrings={{
                    preferencesTitle: "Split panel preferences",
                    preferencesPositionLabel: "Split panel position",
                    preferencesPositionDescription: "Choose the default split panel position for the service.",
                    preferencesPositionSide: "Side",
                    preferencesPositionBottom: "Bottom",
                    preferencesConfirm: "Confirm",
                    preferencesCancel: "Cancel",
                    closeButtonAriaLabel: "Close panel",
                    openButtonAriaLabel: "Open panel",
                    resizeHandleAriaLabel: "Resize split panel",
                }}
            >
                <Header variant="h3" description={this.props.description} actions={this.buildActions()} />
                {this.props.children}
            </SplitPanel>
        );
    }
}

export default IdeaSplitPanel;
