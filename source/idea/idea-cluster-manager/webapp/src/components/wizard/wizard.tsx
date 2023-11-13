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

import { SocaUserInputGroupMetadata, SocaUserInputParamMetadata, SocaUserInputSectionMetadata } from "../../client/data-model";

import Utils from "../../common/utils";

import { IdeaFormField, IdeaFormFieldRegistry, IdeaFormFieldStateChangeEvent, IdeaFormFieldLifecycleEvent } from "../form-field";

import React, { Component } from "react";
import Container from "@cloudscape-design/components/container";
import Header from "@cloudscape-design/components/header";
import Button from "@cloudscape-design/components/button";
import ColumnLayout from "@cloudscape-design/components/column-layout";
import Box from "@cloudscape-design/components/box";
import { WizardProps } from "@cloudscape-design/components/wizard/interfaces";
import Wizard from "@cloudscape-design/components/wizard";
import IdeaFormReviewField from "../form-review-field";
import { v4 as uuid } from "uuid";
import dot from "dot-object";

import { SpaceBetween } from "@cloudscape-design/components";

import { GetParamChoicesRequest, GetParamChoicesResult, SocaUserInputModuleMetadata } from "../../client/data-model";
import { IdeaFormFieldStateChangeEventHandler, IdeaFormFieldLifecycleEventHandler, IdeaFormFieldSyncAPI } from "../form-field";
import { IdeaFormFieldCustomActionProvider } from "../form-field/form-field";

export interface IdeaWizardProps {
    module: SocaUserInputModuleMetadata;
    wizard: WizardProps;
    reviewStep?: IdeaWizardReviewStep;
    lifecycleCallback?: IdeaFormFieldLifecycleEventHandler;
    onStateChange?: IdeaFormFieldStateChangeEventHandler;
    onNavigate?: IdeaWizardNavigateEventHandler;
    onSubmit?: IdeaWizardSubmitEventHandler;
    onCancel?: IdeaWizardCancelEventHandler;
    updateTools?: any;
    syncApi?: IdeaFormFieldSyncAPI;
    customActionProvider?: IdeaFormFieldCustomActionProvider;
    onReview?: () => void;
    values?: any;
    onFetchOptions?: (req: GetParamChoicesRequest) => Promise<GetParamChoicesResult>;
}

interface IdeaWizardReviewStep {
    title?: string;
    description?: string;
}

export interface IdeaWizardNavigateEvent {
    currentStep: number;
    requestedStep: number;
    reason: WizardProps.NavigationReason;
}

export interface IdeaWizardOnNavigateResult {
    nextStep: number;
    errorMessage?: string;
    errorCode?: string;
    ref?: any;
}

export declare type IdeaWizardNavigateEventHandler = (event: IdeaWizardNavigateEvent) => Promise<IdeaWizardOnNavigateResult>;
export declare type IdeaWizardSubmitEventHandler = () => Promise<boolean>;
export declare type IdeaWizardCancelEventHandler = () => any;

export interface IdeaWizardState {
    params: any;
    activeStep: number;
    isLoadingNextStep: boolean;

    values: {
        [k: string]: any;
    };
    visibility: {
        [k: string]: boolean;
    };

    errorCode?: string;
    errorMessage?: string | React.ReactNode;

    isVisible(param: string): boolean;
}

class IdeaWizard extends Component<IdeaWizardProps, IdeaWizardState> {
    fieldRegistry: IdeaFormFieldRegistry;

    constructor(props: IdeaWizardProps) {
        super(props);
        this.state = {
            params: {},
            activeStep: 0,
            isLoadingNextStep: false,
            values: this.props.values ? this.props.values : {},
            visibility: {},
            isVisible(param: string): boolean {
                if (param in this.visibility) {
                    return this.visibility[param];
                } else {
                    return true;
                }
            },
        };
        this.fieldRegistry = new IdeaFormFieldRegistry();
    }

    sectionKey(section: SocaUserInputSectionMetadata, type: string = "step"): string {
        return `s-${section.name}-${type}`;
    }

    groupKey(group: SocaUserInputGroupMetadata, type: string = "step"): string {
        return `s-${group.section}-g-${group.name}-${type}`;
    }

    paramKey(section: SocaUserInputSectionMetadata, param: SocaUserInputParamMetadata, type: string = "param", group?: SocaUserInputGroupMetadata): string {
        if (group) {
            return `s-${section.name}-${group.name}-p-${param.name}-${type}`;
        } else {
            return `s-${section.name}-p-${param.name}-${type}`;
        }
    }

    getParamMeta(param: string): SocaUserInputParamMetadata | null {
        let result = null;
        this.props.module.sections?.forEach((section) => {
            section.params?.forEach((paramMeta) => {
                if (paramMeta.name === param) {
                    result = paramMeta;
                    return false;
                }
            });
            section.groups?.forEach((group) => {
                group.params?.forEach((paramMeta) => {
                    if (paramMeta.name === param) {
                        result = paramMeta;
                        return false;
                    }
                });
            });
        });
        return result;
    }

    getAllParamMeta(section_index?: number): SocaUserInputParamMetadata[] {
        let result: SocaUserInputParamMetadata[] = [];
        this.props.module.sections?.forEach((section, index) => {
            if (section_index != null && section_index !== index) {
                return false;
            }
            section.params?.forEach((paramMeta) => {
                result.push(paramMeta);
            });
            section.groups?.forEach((group) => {
                group.params?.forEach((paramMeta) => {
                    result.push(paramMeta);
                });
            });
        });
        return result;
    }

    setValue(name: string, value: any, callback?: () => void) {
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

    getValue(name: string): any {
        return dot.pick(name, this.state.values);
    }

    getValues(): any {
        // return deep copy
        return JSON.parse(JSON.stringify(this.state.values));
    }

    onFormFieldStateChange = (event: IdeaFormFieldStateChangeEvent) => {
        this.fieldRegistry.add(event.ref);
        this.setValue(event.ref.getParamName(), event.ref.getTypedValue(), () => {
            this.triggerVisibility();
            if (this.props.onStateChange) {
                this.props.onStateChange(event);
            }
        });
    };

    onFormFieldLifecycleEvent = (event: IdeaFormFieldLifecycleEvent) => {
        if (event.type === "mounted") {
            this.fieldRegistry.add(event.ref);
        } else if (event.type === "unmounted") {
            this.fieldRegistry.delete(event.ref.props.param.name!);
        }
    };

    /**
     * reset will reset all values to default values
     * this also makes calls to reset choices
     * @param params
     */
    triggerReset(params: string[]) {
        const fetchOptions: Promise<IdeaFormField>[] = [];
        const setDefaults: Promise<any>[] = [];

        params.forEach((param) => {
            const field = this.fieldRegistry.getFormField(param);
            if (field == null) {
                return true;
            }
            fetchOptions.push(field.fetchOptions());
        });

        Promise.all(fetchOptions).then(
            (fields: IdeaFormField[]) => {
                fields.forEach((field_) => {
                    setDefaults.push(field_.reset());
                });
            },
            (error) => {
                console.error(error);
            }
        );

        Promise.all(setDefaults).catch((error) => console.error(error));
    }

    /**
     * refresh default values from server
     */
    triggerRefresh(includeParams?: string[], excludeParams?: string[]) {
        const fetchDefaults: Promise<any>[] = [];
        this.fieldRegistry.list().forEach((field) => {
            if (field == null) {
                return true;
            }
            if (includeParams != null && !includeParams.includes(field.props.param.name!)) {
                return true;
            }
            if (excludeParams != null && excludeParams.includes(field.props.param.name!)) {
                return true;
            }
            fetchDefaults.push(field.reset());
        });
        Promise.all(fetchDefaults).catch((error) => console.error(error));
    }

    triggerVisibility() {
        const visibility = this.state.visibility;
        this.getAllParamMeta().forEach((param) => {
            visibility[param.name!] = Utils.canShowFormField(this.fieldRegistry, this.state.values, param.when);
        });
        this.setState({
            visibility: visibility,
        });
    }

    isVisible(param: string): boolean {
        const visible = this.state.visibility[param];
        if (typeof visible !== "undefined" || visible != null) {
            return visible;
        }
        return false;
    }

    hideFormField(...params: string[]) {
        const visibility = this.state.visibility;
        params.forEach((param) => {
            visibility[param] = false;
        });
        this.setState({
            visibility: visibility,
        });
    }

    showFormField(...params: string[]) {
        const visibility = this.state.visibility;
        params.forEach((param) => {
            visibility[param] = true;
        });
        this.setState({
            visibility: visibility,
        });
    }

    setActiveStep(index: number) {
        if (this.isReviewStep(index) && this.props.syncApi) {
            this.props.syncApi
                .getParams({
                    module: this.props.module.name,
                    format: "key-value",
                })
                .then(
                    (result) => {
                        const params = result?.params!;
                        this.setState({
                            activeStep: index,
                            values: params,
                        });
                    },
                    (error) => {
                        console.log(error);
                    }
                );
        } else {
            this.setState(
                {
                    activeStep: index,
                },
                () => {
                    this.triggerVisibility();
                }
            );
        }
    }

    isReviewStep(index: number): boolean {
        const sections = this.props.module.sections;
        const numSections = sections ? sections.length : 0;
        return index === numSections;
    }

    getState(): IdeaWizardState {
        return this.state.params;
    }

    buildReviewParams(section: SocaUserInputSectionMetadata, group?: SocaUserInputGroupMetadata) {
        let params, key;
        if (group != null) {
            params = group.params;
            key = this.groupKey(group, "review");
        } else {
            key = this.sectionKey(section, "review");
            params = section.params;
        }

        const getReviewFieldValue = (name: string): any => {
            let value = this.getValue(name);
            if (typeof value === "undefined") {
                return;
            }

            let state = this.fieldRegistry.getLastKnownState(name);
            if (!state) {
                return value;
            }

            let meta = this.getParamMeta(name);
            if (meta?.param_type === "select") {
                let options = state.options;
                if (meta.multiple) {
                    let values = state.stringArrayVal();
                    let labels: string[] = [];
                    options.forEach((option: any) => {
                        if (values.includes(option.value)) {
                            labels.push(option.label);
                        }
                    });
                    return labels;
                } else {
                    return state.selectedOption.label;
                }
            }

            return value;
        };

        if (group) {
            return (
                <Container
                    key={key}
                    variant={"stacked"}
                    header={
                        <Header variant={"h3"} description={group.description}>
                            {group.title}
                        </Header>
                    }
                >
                    <ColumnLayout columns={3} variant="text-grid">
                        {params
                            ?.filter((param) => {
                                return this.state.isVisible(param.name!);
                            })
                            .map((param) => {
                                return <IdeaFormReviewField key={this.paramKey(section, param, "review", group)} param={param} value={getReviewFieldValue(param.name!)} />;
                            })}
                    </ColumnLayout>
                </Container>
            );
        } else {
            return (
                <Box margin={{ bottom: "l" }} key={key}>
                    <ColumnLayout columns={3} variant="text-grid">
                        {params
                            ?.filter((param) => {
                                return this.state.isVisible(param.name!);
                            })
                            .map((param) => {
                                return <IdeaFormReviewField key={this.paramKey(section, param, "review", group)} param={param} value={getReviewFieldValue(param.name!)} />;
                            })}
                    </ColumnLayout>
                </Box>
            );
        }
    }

    buildReviewSection(section: SocaUserInputSectionMetadata, index: number) {
        if (section.groups) {
            return (
                <Box padding={{ bottom: "xl" }}>
                    <SpaceBetween size={"l"}>
                        <Header variant="h2" actions={<Button onClick={() => this.setActiveStep(index)}>Edit</Button>} key={uuid()}>
                            {section.title}
                        </Header>
                        <Box>
                            {section.groups?.map((group) => {
                                return this.buildReviewParams(section, group);
                            })}
                        </Box>
                    </SpaceBetween>
                </Box>
            );
        } else {
            return (
                <Container
                    header={
                        <Header variant="h2" actions={<Button onClick={() => this.setActiveStep(index)}>Edit</Button>} key={uuid()}>
                            {section.title}
                        </Header>
                    }
                >
                    {this.buildReviewParams(section)}
                </Container>
            );
        }
    }

    buildReviewStep(): WizardProps.Step {
        return {
            title: this.props.reviewStep?.title!,
            description: this.props.reviewStep?.description,
            content: (
                <SpaceBetween size="s">
                    {this.props.onReview && (
                        <Box textAlign="right">
                            <Button onClick={this.props.onReview}>Review Configuration</Button>
                        </Box>
                    )}
                    {this.props.module.sections?.map((section, index) => {
                        return (
                            <ColumnLayout columns={1} key={this.sectionKey(section, "review")}>
                                {this.buildReviewSection(section, index)}
                            </ColumnLayout>
                        );
                    })}
                </SpaceBetween>
            ),
        };
    }

    buildParams(section: SocaUserInputSectionMetadata, group?: SocaUserInputGroupMetadata) {
        let params, title, description, key: string | null;
        if (group != null) {
            params = group.params;
            title = group.title;
            description = group.description;
            key = this.groupKey(group);
        } else {
            params = section.params;
            title = section.title;
            key = this.sectionKey(section);
        }
        if (params == null || params.length === 0) {
            return null;
        }
        return (
            <Container
                key={key}
                header={
                    <Header variant="h2" description={description}>
                        {title}
                    </Header>
                }
            >
                <ColumnLayout columns={1}>
                    {params
                        ?.filter((param) => {
                            if (param.prompt != null) {
                                return param.prompt;
                            }
                            return true;
                        })
                        .map((param) => {
                            return (
                                this.state.isVisible(param.name!) && (
                                    <IdeaFormField
                                        param={param}
                                        module={this.props.module.name!}
                                        section={section}
                                        group={group}
                                        onStateChange={this.onFormFieldStateChange}
                                        onLifecycleEvent={this.onFormFieldLifecycleEvent}
                                        key={this.paramKey(section, param, "param", group)}
                                        updateTools={this.props.updateTools}
                                        syncApi={this.props.syncApi}
                                        customActionProvider={this.props.customActionProvider}
                                        value={this.getValue(param.name!)}
                                        onFetchOptions={this.props.onFetchOptions}
                                    />
                                )
                            );
                        })}
                </ColumnLayout>
            </Container>
        );
    }

    buildSection(section: SocaUserInputSectionMetadata) {
        return (
            <ColumnLayout variant="default" columns={1} key={this.sectionKey(section)}>
                {section.groups?.map((group) => {
                    return this.buildParams(section, group);
                })}
                {this.buildParams(section)}
            </ColumnLayout>
        );
    }

    buildSteps(): WizardProps.Step[] {
        const sections = this.props.module.sections;
        if (!sections) {
            return [];
        }
        const steps: WizardProps.Step[] = [];
        for (let i = 0; i < sections.length; i++) {
            const section = sections[i];
            let errorText;
            if (this.state.activeStep === i && this.state.errorCode) {
                errorText = this.state.errorMessage;
            }
            steps.push({
                title: section.title!,
                description: section.description,
                isOptional: !section.required,
                content: this.buildSection(section),
                errorText: errorText,
            });
        }
        if (this.props.reviewStep) {
            steps.push({
                ...this.buildReviewStep(),
                errorText: this.state.errorMessage,
            });
        }
        return steps;
    }

    validateStep(): boolean {
        if (this.isReviewStep(this.state.activeStep)) {
            return true;
        }
        let result = true;
        this.getAllParamMeta(this.state.activeStep).forEach((param) => {
            const field = this.fieldRegistry.getFormField(param.name!);
            if (field == null) {
                return true;
            }
            const isValid = field.triggerValidate();
            if (result && !isValid) {
                result = isValid;
            }
        });
        return result;
    }

    onNavigate(detail: WizardProps.NavigateDetail) {
        if (detail.requestedStepIndex > this.state.activeStep && !this.validateStep()) {
            return;
        }

        if (this.props.onNavigate) {
            this.setState({
                isLoadingNextStep: true,
            });
            this.props
                .onNavigate({
                    requestedStep: detail.requestedStepIndex,
                    currentStep: this.state.activeStep,
                    reason: detail.reason,
                })
                .then((result) => {
                    if (result.errorCode) {
                        this.setState({
                            errorCode: result.errorCode,
                            errorMessage: result.errorMessage,
                            isLoadingNextStep: false,
                        });
                    } else {
                        this.setState({
                            errorCode: undefined,
                            errorMessage: undefined,
                            isLoadingNextStep: false,
                        });
                        this.setActiveStep(result.nextStep);
                    }
                })
                .catch((error) => {
                    console.error(error);
                    this.setState({
                        errorCode: error.error_code,
                        errorMessage: error.message,
                        isLoadingNextStep: false,
                    });
                });
        } else {
            this.setActiveStep(detail.requestedStepIndex);
        }
    }

    onSubmit() {
        this.setState(
            {
                isLoadingNextStep: true,
            },
            () => {
                if (this.props.onSubmit) {
                    this.props.onSubmit().then(() => {
                        this.setState({
                            isLoadingNextStep: false,
                        });
                    });
                }
            }
        );
    }

    onCancel() {
        if (this.props.onCancel) {
            this.props.onCancel();
        }
    }

    setError(errorCode: string, message: string | React.ReactNode) {
        this.setState({
            errorCode: errorCode,
            errorMessage: message,
        });
    }

    clearError() {
        this.setState({
            errorCode: undefined,
            errorMessage: undefined,
        });
    }

    render() {
        return (
            <Wizard
                i18nStrings={{
                    stepNumberLabel: this.props.wizard.i18nStrings.stepNumberLabel,
                    collapsedStepsLabel: this.props.wizard.i18nStrings.collapsedStepsLabel,
                    cancelButton: this.props.wizard.i18nStrings.cancelButton,
                    previousButton: this.props.wizard.i18nStrings.previousButton,
                    nextButton: this.props.wizard.i18nStrings.nextButton,
                    submitButton: this.props.wizard.i18nStrings.submitButton,
                    optional: this.props.wizard.i18nStrings.optional,
                }}
                onNavigate={({ detail }) => this.onNavigate(detail)}
                onSubmit={() => this.onSubmit()}
                onCancel={() => this.onCancel()}
                activeStepIndex={this.state.activeStep}
                isLoadingNextStep={this.state.isLoadingNextStep}
                steps={this.buildSteps()}
            />
        );
    }
}

export default IdeaWizard;
