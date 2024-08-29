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
import { IdeaFormField, IdeaFormFieldRegistry, IdeaFormFieldLifecycleEvent, IdeaFormFieldStateChangeEvent } from "../form-field";
import {Box, Button, ColumnLayout, Container, Form, Header, Modal, SpaceBetween} from "@cloudscape-design/components";
import Utils from "../../common/utils";
import dot from "dot-object";
import { GetParamChoicesRequest, GetParamChoicesResult, SocaUserInputGroupMetadata, SocaUserInputParamMetadata } from "../../client/data-model";
import { IdeaFormFieldStateChangeEventHandler } from "../form-field";
import { ModalProps } from "@cloudscape-design/components/modal/interfaces";
import { OnToolsChangeEvent } from "../../App";

export interface IdeaFormContainerGroup {
    title: string
    name: string
}

export interface IdeaFormProps {
    name: string;
    showHeader?: boolean;
    showActions?: boolean;
    showSecondaryCta?: boolean;
    title?: string;
    description?: string;
    params: ReadonlyArray<SocaUserInputParamMetadata>;
    groups?: ReadonlyArray<SocaUserInputGroupMetadata>;
    primaryCtaTitle?: string;
    secondaryCtaTitle?: string;
    onSubmit?: IdeaFormOnSubmit;
    onCancel?: IdeaFormOnCancel;
    values?: any;
    modal?: boolean;
    modalSize?: ModalProps.Size;
    onFetchOptions?: (req: GetParamChoicesRequest) => Promise<GetParamChoicesResult>;
    columns?: number;
    onStateChange?: IdeaFormFieldStateChangeEventHandler;
    stretch?: boolean;
    loading?: boolean;
    loadingText?: string;
    useContainers?: boolean;
    containerGroups?: ReadonlyArray<IdeaFormContainerGroup>;
    toolsOpen?: boolean;
    tools?: React.ReactNode; 
    onToolsChange?: (event: OnToolsChangeEvent) => void;
}

export interface IdeaFormState {
    errorCode?: string | null;
    message?: string | null;
    showModal: boolean;
    values: {
        [k: string]: any;
    };
    visibility: {
        [k: string]: boolean;
    };
    submitInProgress: boolean;
}

export interface IdeaFormOnSubmitEvent {
    form: IdeaForm;
}

export interface IdeaFormOnCancelEvent {
    form: IdeaForm;
}

export type IdeaFormOnSubmit = (event: IdeaFormOnSubmitEvent) => Promise<boolean> | void;
export type IdeaFormOnCancel = (event: IdeaFormOnCancelEvent) => void;

class IdeaForm extends Component<IdeaFormProps, IdeaFormState> {
    registry: IdeaFormFieldRegistry;

    constructor(props: IdeaFormProps) {
        super(props);
        this.registry = new IdeaFormFieldRegistry();
        this.state = {
            errorCode: null,
            message: null,
            showModal: false,
            values: this.props.values ? this.props.values : {},
            visibility: {},
            submitInProgress: false,
        };
    }

    componentDidMount() {
        this.triggerVisibility();
    }

    isVisible(param: string): boolean {
        if (param in this.state.visibility) {
            return this.state.visibility[param];
        } else {
            return true;
        }
    }

    showHeader(): boolean {
        if (this.props.showHeader != null) {
            return this.props.showHeader;
        }
        return !this.isModal();
    }

    showActions(): boolean {
        if (this.props.showActions != null) {
            return this.props.showActions;
        }
        return !this.isModal();
    }

    showSecondaryCta(): boolean {
        if (this.props.showSecondaryCta == null) {
            return true;
        }
        return this.props.showSecondaryCta;
    }

    onLifecycleEvent = (event: IdeaFormFieldLifecycleEvent) => {
        if (event.type === "mounted") {
            this.registry.add(event.ref);
        } else if (event.type === "unmounted") {
            this.registry.delete(event.ref.props.param.name!);
        }
    };

    triggerVisibility() {
        const visibility = this.state.visibility;
        this.props.params.forEach((param) => {
            visibility[param.name!] = Utils.canShowFormField(this.registry, this.state.values, param.when);
        });
        this.setState({
            visibility: visibility,
        });
    }

    onStateChange = (event: IdeaFormFieldStateChangeEvent) => {
        this.registry.add(event.ref);
        this.setValue(event.ref.getParamName(), event.ref.getTypedValue(), () => {
            this.triggerVisibility();
            if (this.props.onStateChange) {
                this.props.onStateChange(event);
            }
        });
    };

    validate(): boolean {
        let result = true;
        this.registry.list().forEach((field) => {
            const fieldResult = field.triggerValidate();
            if (!fieldResult) {
                result = fieldResult;
            }
        });
        return result;
    }

    private setValue(name: string, value: any, callback?: () => void) {
        const values = this.state.values;
        dot.del(name, values);
        dot.str(name, value, values);
        this.setState(
            {
                values: values,
            },
            callback
        );
    }

    setParamValue(name: string, value: any) {
        const field = this.getFormField(name);
        if (field) {
            field.setValue(value);
        }
    }

    getValue(name: string): any {
        return dot.pick(name, this.state.values);
    }

    getValues(): any {
        const values = {};
        this.props.params.forEach((param) => {
            if (param.name && this.isVisible(param.name)) {
                if (param.name in values) {
                    dot.del(param.name, values);
                }
                dot.str(param.name!, dot.pick(param.name, this.state.values), values);
            }
        });
        return values;
    }

    setError(errorCode: string, message: string) {
        this.setState({
            errorCode: errorCode,
            message: message,
        });
    }

    clearError() {
        this.setState({
            errorCode: null,
            message: null,
        });
    }

    reset() {
        return new Promise<void>((resolve) => {
            this.clearError();
            this.registry.list().forEach((field) => {
                field.reset().finally();
            });
            return resolve();
        });
    }

    isModal(): boolean {
        if (this.props.modal != null) {
            return this.props.modal;
        }
        return false;
    }

    getModalSize(): ModalProps.Size {
        if (this.props.modalSize != null) {
            return this.props.modalSize;
        }
        return "medium";
    }

    showModal() {
        this.setState({
            showModal: true,
        });
    }

    hideModal() {
        this.setState(
            {
                showModal: false,
            },
            () => {
                this.reset().finally();
            }
        );
    }

    handleOnSubmit() {
        if (this.props.onSubmit) {
            const result = this.props.onSubmit({
                form: this,
            });
            if (result) {
                this.setState({
                    submitInProgress: true,
                });
                result.finally(() => {
                    this.setState({
                        submitInProgress: false,
                    });
                });
            }
        }
    }

    getFormField(param: string): IdeaFormField | null {
        return this.registry.getFormField(param);
    }

    buildFormActions() {
        const getPrimaryCtaTitle = (): string => {
            if (this.props.primaryCtaTitle) {
                return this.props.primaryCtaTitle;
            }
            return "Submit";
        };
        const getSecondaryCtaTitle = (): string => {
            if (this.props.secondaryCtaTitle) {
                return this.props.secondaryCtaTitle;
            }
            return "Cancel";
        };
        return (
            <SpaceBetween direction="horizontal" size="xs">
                {this.showSecondaryCta() && (
                    <Button
                        formAction="none"
                        variant="link"
                        onClick={() => {
                            this.hideModal();
                            if (this.props.onCancel) {
                                this.props.onCancel({
                                    form: this,
                                });
                            }
                        }}
                    >
                        {getSecondaryCtaTitle()}
                    </Button>
                )}
                <Button
                    loading={this.state.submitInProgress}
                    variant="primary"
                    onClick={() => {
                        this.handleOnSubmit();
                    }}
                >
                    {getPrimaryCtaTitle()}
                </Button>
            </SpaceBetween>
        );
    }

    buildForm() {
        const getValue = (param: SocaUserInputParamMetadata): any => {
            if (this.props.values) {
                return this.props.values[param.name!];
            }
            return param.default;
        };


        const numColumns = () => (this.props.columns != null ? this.props.columns : 1);

        return (
            <form onSubmit={(e) => e.preventDefault()}>
                <Form actions={this.showActions() && this.buildFormActions()} header={this.showHeader() && <Header variant="h2">{this.props.title}</Header>} errorText={this.state.message}>
                    <SpaceBetween size="l" direction="vertical">
                        <ColumnLayout columns={numColumns()}>
                            {this.props.useContainers ? (
                                this.props.containerGroups && this.props.containerGroups.map((containerGroup, index) => {
                                    return(
                                        <Container key={`${containerGroup.name}-${index}`} header={<Header variant="h3">{containerGroup.title}</Header>}>
                                            {
                                                this.props.params.filter((param) => param.container_group_name === containerGroup.name).map((param) => {
                                                    return (
                                                        this.isVisible(param.name!) && (
                                                            <IdeaFormField
                                                                key={`${containerGroup.name}-${param.name}-${index}`}
                                                                module={this.props.name}
                                                                param={param}
                                                                onLifecycleEvent={this.onLifecycleEvent}
                                                                onStateChange={this.onStateChange}
                                                                value={getValue(param)}
                                                                onFetchOptions={this.props.onFetchOptions}
                                                                stretch={this.props.stretch}
                                                                onKeyEnter={() => {
                                                                    this.handleOnSubmit();
                                                                }}
                                                                toolsOpen={this.props.toolsOpen} 
                                                                tools={this.props.tools}
                                                                onToolsChange={this.props.onToolsChange}
                                                            />
                                                        )
                                                    )
                                                })
                                            }
                                        </Container>
                                    )
                                })
                                ) : (
                                this.props.params.map((param, index) => {
                                            return (
                                                this.isVisible(param.name!) && (
                                                    <IdeaFormField
                                                        key={`${param.name}-${index}`}
                                                        module={this.props.name}
                                                        param={param}
                                                        onLifecycleEvent={this.onLifecycleEvent}
                                                        onStateChange={this.onStateChange}
                                                        value={getValue(param)}
                                                        onFetchOptions={this.props.onFetchOptions}
                                                        stretch={this.props.stretch}
                                                        onKeyEnter={() => {
                                                            this.handleOnSubmit();
                                                        }}
                                                        toolsOpen={this.props.toolsOpen} 
                                                        tools={this.props.tools}
                                                        onToolsChange={this.props.onToolsChange}
                                                    />
                                                )
                                            );
                                    })
                                )
                            }
                        </ColumnLayout>
                    </SpaceBetween>
                </Form>
            </form>
        );
    }

    render() {
        if (this.isModal()) {
            return (
                <Modal
                    visible={this.state.showModal}
                    size={this.getModalSize()}
                    onDismiss={() => {
                        this.reset().then(() => {
                            this.setState(
                                {
                                    showModal: false,
                                },
                                () => {
                                    if (this.props.onCancel) {
                                        this.props.onCancel({
                                            form: this,
                                        });
                                    }
                                }
                            );
                        });
                    }}
                    header={<Header variant="h3">{this.props.title}</Header>}
                    footer={<Box float="right">{this.buildFormActions()}</Box>}
                >
                    {this.buildForm()}
                </Modal>
            );
        } else {
            return this.buildForm();
        }
    }
}

export default IdeaForm;
