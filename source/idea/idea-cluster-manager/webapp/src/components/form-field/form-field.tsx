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
import { GetParamChoicesRequest, GetParamChoicesResult, GetParamDefaultRequest, GetParamDefaultResult, GetParamsRequest, GetParamsResult, SetParamRequest, SetParamResult, SocaUserInputGroupMetadata, SocaUserInputParamMetadata, SocaUserInputSectionMetadata } from "../../client/data-model";

import Utils from "../../common/utils";
import Input, { InputProps } from "@cloudscape-design/components/input";
import FormField, { FormFieldProps } from "@cloudscape-design/components/form-field";
import {AttributeEditor, Autosuggest, Button, ColumnLayout, DatePicker, ExpandableSection, FileUpload, Grid, Link, Multiselect, RadioGroup, Select, SelectProps, SpaceBetween, Textarea, Tiles, Toggle} from "@cloudscape-design/components";
import { BaseKeyDetail } from "@cloudscape-design/components/internal/events";
import { faAdd, faRemove } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { OnToolsChangeEvent } from "../../App";

export interface IdeaFormFieldSyncAPI {
    getParamDefault(req: GetParamDefaultRequest): Promise<GetParamDefaultResult>;

    setParam(req: SetParamRequest): Promise<SetParamResult>;

    getParamChoices(req: GetParamChoicesRequest): Promise<GetParamChoicesResult>;

    getParams(req: GetParamsRequest): Promise<GetParamsResult>;
}

export interface IdeaFormFieldCustomActionProvider {
    onCustomActionClick(customTypeName: string, formField: IdeaFormField, onSubmit: (value: any) => void): void;

    getCustomActionLabel(customTypeName: string): string | null;
}

export interface IdeaFormFieldProps {
    module: string;
    param: SocaUserInputParamMetadata;
    section?: SocaUserInputSectionMetadata;
    group?: SocaUserInputGroupMetadata;
    onLifecycleEvent?: IdeaFormFieldLifecycleEventHandler;
    onStateChange?: IdeaFormFieldStateChangeEventHandler;
    visible?: boolean;
    updateTools?: any;
    syncApi?: IdeaFormFieldSyncAPI;
    value?: any;
    onKeyEnter?: IdeaFormFieldOnKeyEnterEventHandler;
    onFetchOptions?: (req: GetParamChoicesRequest) => Promise<GetParamChoicesResult>;
    customActionProvider?: IdeaFormFieldCustomActionProvider;
    stretch?: boolean;
    toolsOpen?: boolean | null;
    tools?: React.ReactNode| null;
    onToolsChange?: (event: OnToolsChangeEvent) => void | null;
}

export interface IdeaFormFieldState {
    value?: any;
    value2?: any;

    default?: any;

    errorCode?: string | null;
    errorMessage?: string | null;

    selectedOption?: any;
    selectedOptions?: any;
    options: any[];

    dynamicOptions: boolean;
    dynamicOptionsLoading: boolean;

    defaultValueLoading: boolean;

    visibility: boolean;

    disabled: boolean;

    stringVal(): string;

    stringVal2(): string;

    booleanVal(): boolean;

    numberVal(): number;

    stringArrayVal(): string[];

    booleanArrayVal(): boolean[];

    numberArrayVal(): number[];

    amountVal(): string;

    memoryVal(): string

    fileVal(): File[];

    listOfRecordsVal(): Record<any, any>[]

    listOfAttributeEditorRecords(): {key: string, value: string, error?: string}[]
}

export interface IdeaFormFieldStateChangeEvent {
    param: SocaUserInputParamMetadata;
    value?: any | any[];
    errorCode?: string | null;
    errorMessage?: string | null;
    refresh?: boolean;
    ref: IdeaFormField;
}

export interface IdeaFormFieldLifecycleEvent {
    type: LifecycleEventType;
    ref: IdeaFormField;
}

export interface IdeaFormFieldKeyEnterEvent {
    ref: IdeaFormField;
}

type LifecycleEventType = "mounted" | "unmounted";
export type IdeaFormFieldLifecycleEventHandler = (event: IdeaFormFieldLifecycleEvent) => void;
export type IdeaFormFieldStateChangeEventHandler = (event: IdeaFormFieldStateChangeEvent) => void;
export type IdeaFormFieldOnKeyEnterEventHandler = (event: IdeaFormFieldKeyEnterEvent) => void;

export interface IdeaFormFieldRegistryEntry {
    field: IdeaFormField | null;
    lastKnownState: IdeaFormFieldState | null;
}

export class IdeaFormFieldRegistry {
    fields: {
        [k: string]: IdeaFormFieldRegistryEntry;
    };

    constructor() {
        this.fields = {};
    }

    add(field: IdeaFormField) {
        this.fields[field.getParamName()] = {
            field: field,
            lastKnownState: field.getState(),
        };
    }

    delete(param: string) {
        if (param in this.fields) {
            this.fields[param].field = null;
        }
    }

    getFormField(param: string): IdeaFormField | null {
        if (!(param in this.fields)) {
            return null;
        }
        const entry = this.fields[param];
        return entry.field;
    }

    getLastKnownState(param: string): IdeaFormFieldState | null {
        if (!(param in this.fields)) {
            return null;
        }
        const entry = this.fields[param];
        return entry.lastKnownState;
    }

    list(): IdeaFormField[] {
        const fields: IdeaFormField[] = [];
        for (const param in this.fields) {
            const field = this.getFormField(param);
            if (field == null) {
                continue;
            }
            fields.push(field);
        }
        return fields;
    }
}

class IdeaFormField extends Component<IdeaFormFieldProps, IdeaFormFieldState> {
    constructor(props: IdeaFormFieldProps) {
        super(props);
        this.state = {
            value: this.props.value ? this.props.value : this.props.param.default,
            value2: undefined,
            default: this.props.param.default,

            options: [],
            selectedOption: {},
            selectedOptions: [],

            dynamicOptions: false,
            dynamicOptionsLoading: false,

            defaultValueLoading: false,

            errorCode: null,
            errorMessage: null,

            visibility: true,
            disabled: this.props.param.readonly ? this.props.param.readonly : false,

            stringVal(): string {
                if (Utils.isNotEmpty(this.value)) {
                    return Utils.asString(this.value);
                }
                return "";
            },
            stringVal2(): string {
                if (this.value2 != null) {
                    return Utils.asString(this.value2);
                }
                return "";
            },
            stringArrayVal(): string[] {
                if (this.value != null) {
                    return Utils.asStringArray(this.value);
                }
                return [];
            },
            booleanVal(): boolean {
                if (this.value != null) {
                    return Utils.asBoolean(this.value);
                }
                return false;
            },
            booleanArrayVal(): boolean[] {
                if (this.value != null) {
                    return Utils.asBooleanArray(this.value);
                }
                return [];
            },
            numberVal(decimal: boolean = false): number {
                if (this.value != null) {
                    return Utils.asNumber(this.value, 0, decimal);
                }
                return 0;
            },
            numberArrayVal(): number[] {
                if (this.value != null) {
                    return Utils.asNumberArray(this.value);
                }
                return [];
            },
            amountVal(): string {
                if (typeof this.value === "object") {
                    return Utils.asString(this.value.amount);
                }
                return "0.00";
            },
            memoryVal(): string {
                if (typeof this.value === "object") {
                    return Utils.asString(this.value.value);
                }
                return "0";
            },
            fileVal(): File[] {
                if (this.value != null) {
                    return this.value2;
                }
                return [];
            },
            listOfRecordsVal(): Record<any, any>[] {
                if (this.value != null) {
                    return this.value
                }
                return []
            },
            listOfAttributeEditorRecords(): { key: string; value: string; error?: string }[] {
                if (this.value != null) {
                    return this.value
                }
                return []
            }
        };
    }

    getParamName(): string {
        return this.props.param.name!;
    }

    getParamMeta(): SocaUserInputParamMetadata {
        return this.props.param;
    }

    isAutoComplete(): boolean {
        return this.props.param.param_type === "autocomplete";
    }

    getState(): IdeaFormFieldState {
        // shallow copy
        return Object.assign({}, this.state);
    }

    getValueAsString(): string {
        if (this.isMultiple()) {
            return this.state.stringArrayVal().join(", ");
        } else {
            return this.state.stringVal();
        }
    }

    getValueAsStringArray(): string[] {
        return this.state.stringArrayVal();
    }

    getSelectedOptionLabel(): string {
        if (this.state.selectedOption && this.state.selectedOption.label) {
            return this.state.selectedOption.label;
        }
        return "";
    }

    getSelectOptions(): any {
        return this.state.options;
    }

    getDataType(): string {
        if (this.props.param.data_type) {
            return this.props.param.data_type;
        }
        return "str";
    }

    getAnyValue(): any {
        return this.state.value;
    }

    getListOfStringRecords(): Record<string,string>[] {
        if (Utils.isListOfRecordStrings(this.state.listOfRecordsVal())) {
            return this.state.listOfRecordsVal()
        }
        return []
    }

    getListOfAttributeEditorRecords() {
        if(Utils.isListOfAttributeEditorRecords(this.state.listOfAttributeEditorRecords())) {
            return this.state.listOfAttributeEditorRecords()
        }
        return []
    }

    getTypedValue(): any {
        if (this.isMultiple()) {
            const dataType = this.getDataType();
            switch (dataType) {
                case "int":
                case "float":
                    return this.state.numberArrayVal();
                case "bool":
                    return this.state.booleanArrayVal();
                case "record":
                    return this.state.listOfRecordsVal();
                case "attributes":
                    return this.state.listOfAttributeEditorRecords()
                default:
                    return this.state.stringArrayVal();
            }
        } else {
            const dataType = this.getDataType();
            switch (dataType) {
                case "int":
                case "float":
                    return this.state.numberVal();
                case "bool":
                    return this.state.booleanVal();
                case "amount":
                    if (typeof this.state.value === "object") {
                        return this.state.value;
                    } else {
                        return {
                            amount: 0.0,
                            unit: "USD",
                        };
                    }
                case "memory":
                    if (typeof this.state.value === "object") {
                        return this.state.value;
                    } else {
                        return {
                            value: 0,
                            unit: "bytes",
                        };
                    }
                default:
                    return this.state.stringVal();
            }
        }
    }

    async getFileAsBase64String(file: File): Promise<string | ArrayBuffer | null> {
        const reader = new FileReader()
        return new Promise((resolve, reject) => {
            reader.onerror = error => reject(error);
            reader.onloadend = () => {
            // Use a regex to remove data url part
            return resolve((reader.result as string)
                .replace('data:', '')
                .replace(/^.+,/, '')
        )};
            reader.readAsDataURL(file);
        })
    }

    getErrorCode(): string | null {
        if (Utils.isEmpty(this.state.errorCode)) {
            return null;
        }
        return this.state.errorCode!;
    }

    getErrorMessage(): string | null {
        if (Utils.isEmpty(this.state.errorMessage)) {
            return null;
        }
        return this.state.errorMessage!;
    }

    fetchDefault(reset: boolean = false) {
        if (!this.props.syncApi) {
            return Promise.resolve(this.state);
        }
        return this.props.syncApi
            .getParamDefault({
                module: this.props.module,
                param: this.props.param.name,
                reset: reset,
            })
            .then((result) => {
                return new Promise((resolve) => {
                    const state = {
                        default: result?.default,
                    };
                    this.setState(state, () => {
                        resolve(state);
                    });
                });
            });
    }

    updateSelectedOptions(): boolean {
        if (this.state.options == null || this.state.options.length === 0) {
            return false;
        }

        const selectedOptions: any[] = [];
        if (this.isMultiple()) {
            const arrayVal = this.state.stringArrayVal();
            this.state.options.forEach((option) => {
                if (arrayVal.find((value) => value === option.value)) {
                    selectedOptions.push(option);
                }
            });
        } else {
            const stringVal = this.state.stringVal();
            this.state.options.forEach((option) => {
                if (stringVal === option.value) {
                    selectedOptions.push(option);
                }
            });
        }
        if (this.isMultiple()) {
            this.setState({
                selectedOptions: selectedOptions,
            });
        } else {
            this.setState({
                selectedOption: selectedOptions[0],
            });
        }
        return true;
    }

    setValue(value: any) {
        this.setState(
            {
                value: value,
            },
            this.setStateCallback
        );
    }

    setNull(): Promise<any> {
        const syncApi = this.props.syncApi;
        if (syncApi == null) {
            return Promise.resolve({});
        }
        return new Promise((resolve, reject) => {
            syncApi
                .setParam({
                    module: this.props.module,
                    param: this.getParamName(),
                    value: "",
                })
                .then(
                    (result) => {
                        resolve(result);
                    },
                    (error) => {
                        reject(error);
                    }
                );
        });
    }

    reset(): Promise<boolean> {
        const setStateCallback = () => {
            this.updateSelectedOptions();
            this.setStateCallback();
        };
        return this.fetchDefault().then((_) => {
            if (this.isMultiple()) {
                this.setState(
                    {
                        value: this.state.default,
                        errorCode: null,
                        errorMessage: null,
                    },
                    setStateCallback
                );
            } else {
                this.setState(
                    {
                        value: this.state.default,
                        errorCode: null,
                        errorMessage: null,
                    },
                    setStateCallback
                );
            }
            return Promise.resolve(true);
        });
    }

    public setOptions(result: GetParamChoicesResult, dynamicOptions: boolean = false) {
        const choices = result?.listing!;
        const options = [];

        for (let i = 0; i < choices.length; i++) {
            const choice = choices[i];
            if (choice.options && choice.options.length > 0) {
                const level2Options: any[] = [];
                const option = {
                    label: choice.title,
                    options: level2Options,
                };
                options.push(option);
                const choicesLevel2 = choice.options;
                for (let j = 0; j < choicesLevel2.length; j++) {
                    const choiceLevel2 = choicesLevel2[j];
                    const value = Utils.asString(choiceLevel2.value);
                    level2Options.push({
                        value: value,
                        label: choiceLevel2.title,
                        description: choiceLevel2.description,
                        disabled: choiceLevel2.disabled,
                    });
                }
            } else {
                const value = Utils.asString(choice.value);
                options.push({
                    value: value,
                    label: choice.title,
                    description: choice.description,
                    disabled: choice.disabled,
                });
            }
        }
        const state = {
            dynamicOptions: dynamicOptions,
            options: options,
        };
        this.setState(state, () => {
            this.updateSelectedOptions();
        });
    }

    fetchOptions(refresh: boolean = false): Promise<IdeaFormField> {
        const paramType = this.props.param.param_type;
        const applicableParamTypes = ["select", "raw_select", "select_or_text", "checkbox", "autocomplete", "tiles", "radio-group"];
        const found = applicableParamTypes.find((value) => value === paramType);

        if (Utils.isEmpty(found)) {
            return Promise.resolve(this);
        }

        let dynamicOptions = false;
        if (this.props.param.dynamic_choices != null) {
            dynamicOptions = this.props.param.dynamic_choices;
        } else {
            dynamicOptions = this.props.param.choices == null || this.props.param.choices.length === 0;
        }
        const syncApi = this.props.syncApi;

        if (dynamicOptions) {
            let onFetchOptions;
            if (syncApi != null) {
                onFetchOptions = syncApi.getParamChoices;
            } else if (this.props.onFetchOptions != null) {
                onFetchOptions = this.props.onFetchOptions;
            }
            if (onFetchOptions == null) {
                return Promise.resolve(this);
            }

            return onFetchOptions({
                module: this.props.module,
                param: this.props.param.name,
                refresh: refresh,
            }).then(
                (result) => {
                    this.setOptions(result, dynamicOptions);
                    this.updateSelectedOptions();
                    return this;
                },
                (error) => {
                    this.setState({
                        options: [],
                    });
                    throw error;
                }
            );
        } else {
            this.setOptions(
                {
                    listing: this.props.param.choices!,
                },
                dynamicOptions
            );
            return Promise.resolve(this);
        }
    }

    componentDidMount() {
        if (this.props.onLifecycleEvent) {
            this.props.onLifecycleEvent({
                type: "mounted",
                ref: this,
            });
        }
        this.initialize();
    }

    initialize() {
        Promise.all([this.fetchDefault(), this.fetchOptions()]).then(
            (_) => {
                const value = this.getTypedValue();
                this.setState(
                    {
                        value: value,
                        value2: value,
                    },
                    () => {
                        if (Utils.isNotEmpty(this.state.value)) {
                            this.setStateCallback();
                        }
                    }
                );
            },
            (error) => {
                console.error(error);
                this.setState(
                    {
                        value: undefined,
                    },
                    this.setStateCallback
                );
            }
        );
    }

    componentWillUnmount() {
        if (this.props.onLifecycleEvent) {
            this.props.onLifecycleEvent({
                type: "unmounted",
                ref: this,
            });
        }
    }

    publishStateChange(refresh: boolean = false) {
        if (this.props.onStateChange != null) {
            this.props.onStateChange({
                param: this.props.param,
                ref: this,
                value: this.getTypedValue(),
                errorCode: this.state.errorCode,
                errorMessage: this.state.errorMessage,
                refresh: refresh,
            });
        }
    }

    setStateCallback() {
        const syncApi = this.props.syncApi;
        if (syncApi == null) {
            this.publishStateChange(false);
            return;
        }
        syncApi
            .setParam({
                module: this.props.module,
                param: this.props.param.name,
                value: this.state.value,
            })
            .then(
                (result) => {
                    // do not publish state change here
                    if (this.isMultiple()) {
                        const serverVal = Utils.asStringArray(result?.value);
                        const localVal = this.state.stringArrayVal();
                        if (!Utils.isArrayEqual(serverVal, localVal)) {
                            this.setState({
                                value: serverVal,
                            });
                        }
                    } else {
                        const serverVal = Utils.asString(result?.value);
                        const localVal = this.state.stringVal();
                        if (serverVal !== localVal) {
                            this.setState({
                                value: serverVal,
                            });
                        }
                    }
                    this.setState({
                        errorCode: null,
                        errorMessage: null,
                    });
                    this.updateSelectedOptions();
                    this.publishStateChange(result?.refresh);
                },
                (error) => {
                    console.error(error);
                    this.setState({
                        errorCode: error.error_code,
                        errorMessage: error.message,
                    });
                }
            );
    }

    disable(should_disable: boolean) {
        this.setState({ disabled: should_disable }, this.setStateCallback);
    }

    validate_empty_record(record: Record<any,any>, container_items: SocaUserInputParamMetadata[]): boolean {
        if (Utils.isEmpty(record)) {
            return true;
        }
        for (let column of container_items) {
            if (column.name && Utils.isEmpty(record[column.name])) {
                return true;
            }
        }
        return false;
    }

    validate(): string {
        const validate = this.props.param.validate;
        if (validate == null) {
            return "OK";
        }

        if (!this.validateRegex()) {
            return "REGEX";
        }

        if (validate.min != null || validate.max != null) {
            const dataType = this.props.param.data_type!;
            const decimal = dataType === "float";
            const numberVal = this.state.numberVal();
            const min = Utils.asNumber(validate.min, 0, decimal);
            const max = Utils.asNumber(validate.max, 0, decimal);
            if (validate.min != null && validate.max != null) {
                if (numberVal < min || numberVal > max) {
                    return "NUMBER_RANGE";
                }
            } else if (validate.min != null) {
                if (numberVal < min) {
                    return "MIN_VALUE";
                }
            } else if (validate.max != null) {
                if (numberVal > max) {
                    return "MAX_VALUE";
                }
            }
        }

        if (validate.required == null || Utils.isFalse(validate.required)) {
            return "OK";
        }

        if (this.isMultiple()) {
            if (this.props.param.param_type === "container") {
                if (this.getListOfStringRecords().length === 0) {
                    return "OK";
                } else {
                    for (let record of this.getListOfStringRecords()) {
                        if (this.props.param.container_items && this.validate_empty_record(record, this.props.param.container_items)) {
                            return "CUSTOM_FAILED"
                        }
                    }
                    return "OK";
                }
            }
            if (this.state.stringArrayVal().length === 0) {
                return "REQUIRED";
            } else {
                let isEmpty = false;
                let values = this.state.stringArrayVal();
                for (let i = 0; i < values.length; i++) {
                    if (Utils.isEmpty(values[i])) {
                        isEmpty = true;
                        break;
                    }
                }
                if (isEmpty) {
                    return "REQUIRED";
                }
                return "OK";
            }
        } else if (Utils.isEmpty(this.state.stringVal())) {
            return "REQUIRED";
        }

        if (this.props.param.param_type === "new-password") {
            if (Utils.isEmpty(this.state.value2)) {
                return "REQUIRED";
            }
        }

        return "OK";
    }

    triggerValidate(): boolean {
        const result = this.validate();
        if (result === "OK") {
            this.setState({
                errorCode: null,
                errorMessage: null,
            });
            return true;
        } else {
            const errorCode = "VALIDATION_FAILED";
            let errorMessage;
            let displayTitle = this.props.param.title;
            if (displayTitle === undefined || displayTitle === null || displayTitle?.length === 0) {
                displayTitle = this.props.param.name;
            }
            switch (result) {
                case "REQUIRED":
                    errorMessage = `${displayTitle} is required.`;
                    break;
                case "NUMBER_RANGE":
                    errorMessage = `${displayTitle} must be between ${this.props.param.validate?.min}
                    and ${this.props.param.validate?.max}.`;
                    break;
                case "MIN_VALUE":
                    errorMessage = `${displayTitle} must be greater than or equal to ${this.props.param.validate?.min}`;
                    break;
                case "MAX_VALUE":
                    errorMessage = `${displayTitle} must be less than or equal to ${this.props.param.validate?.max}`;
                    break;
                case "REGEX":
                    errorMessage = this.props.param.validate?.message ?? `${displayTitle} must satisfy regex: ${this.props.param.validate?.regex}`;
                    break;
                case 'CUSTOM_FAILED':
                    errorMessage = this.props.param.custom_error_message
                    break
                default:
                    errorMessage = `${displayTitle} validation failed.`;
            }
            this.setState({
                errorCode: errorCode,
                errorMessage: errorMessage,
            });
            return false;
        }
    }

    getNativeType(): string {
        const dataType = this.props.param.data_type!;
        let result;
        if (dataType === "int" || dataType === "float") {
            result = "number";
        } else if (dataType === "str") {
            result = "string";
        } else if (dataType === "bool") {
            result = "boolean";
        } else if (dataType === "memory") {
            result = "memory";
        } else if (dataType === "amount") {
            result = "amount";
        } else {
            result = "string";
        }
        return result;
    }

    getCustomType(): string | null {
        if (this.props.param.custom_type) {
            return this.props.param.custom_type;
        }
        return null;
    }

    getInputMode(): InputProps.InputMode {
        const type = this.getNativeType();
        const dataType = this.props.param.data_type!;
        if (type === "string") {
            return "text";
        } else if (type === "number") {
            if (dataType === "int") {
                return "numeric";
            } else {
                return "decimal";
            }
        }
        return "text";
    }

    isMultiple(): boolean {
        if (this.props.param.multiple != null) {
            return this.props.param.multiple;
        }
        return false;
    }

    isReadOnly(): boolean {
        if (this.props.param.readonly != null) {
            return this.props.param.readonly;
        }
        return false;
    }

    isAutoFocus(): boolean {
        if (this.props.param.auto_focus != null) {
            return this.props.param.auto_focus;
        }
        return false;
    }

    isRefreshable(): boolean {
        if (this.props.param.refreshable != null) {
            return this.props.param.refreshable;
        }
        return false;
    }

    getInputType(): InputProps.Type {
        const type = this.getNativeType();
        const paramType = this.props.param.param_type;
        if (type === "string") {
            if (paramType === "password") {
                return "password";
            } else {
                return "text";
            }
        } else if (type === "number") {
            return "number";
        }
        return "text";
    }

    getContainerInputType(param: SocaUserInputParamMetadata): InputProps.Type {
        const dataType = param.data_type!;
        if ( dataType === "url" ) {
            return "url"
        }
        return "text";
    }

    isMarkDownAvailable(): boolean {
        return Utils.isNotEmpty(this.props.param.markdown);
    }

    handleToolsOpen(markdown?: string) {
        if (this.props.onToolsChange && markdown) {
            this.props.onToolsChange({
                open: true,
                pageId: markdown,
            })
        }
    }

    buildFormField(field: React.ReactNode, props?: FormFieldProps, key?: string): React.ReactNode {
        let label: React.ReactNode = this.props.param.optional ?  <span>{this.props.param.title} <i>- optional</i></span> : this.props.param.title;
        let description: React.ReactNode = this.props.param.description;
        let constraintText: React.ReactNode = this.props.param.help_text;
        let stretch = false;
        let secondaryControl = null;
        if (props != null) {
            if (props.label != null) {
                label = this.props.param.optional ?  <span>{props.label} <i>- optional</i></span> : props.label;
            }
            if (props.description != null) {
                description = props.description;
            }
            if (props.constraintText != null) {
                constraintText = props.constraintText;
            }
            if (props.stretch != null) {
                stretch = props.stretch;
            }
            if (props.secondaryControl != null) {
                secondaryControl = props.secondaryControl;
            }
        }

        if (!key) {
            key = `f-${this.getParamName()}`;
        }

        return (
            <FormField
                key={key}
                label={label}
                description={description}
                constraintText={constraintText}
                stretch={stretch}
                info={
                    this.isMarkDownAvailable() && (
                        <Link
                            variant="info"
                            onFollow={() => {
                                this.handleToolsOpen(this.props.param.markdown)
                            }}
                        >
                            Info
                        </Link>
                    )
                }
                errorText={this.getErrorMessage()}
                secondaryControl={secondaryControl}
            >
                {field}
            </FormField>
        );
    }

    validateRegex(value?: string): boolean {
        if (this.props.param.validate == null) {
            return true;
        }
        const regex = this.props.param.validate.regex;
        if (regex == null || Utils.isEmpty(regex)) {
            return true;
        }
        const re = RegExp(regex);
        let token = value;
        if (token == null) {
            token = this.state.stringVal();
        }

        return re.test(token);
    }

    triggerDynamicOptionsLoading(): Promise<any> {
        return new Promise((resolve, reject) => {
            this.setState(
                {
                    dynamicOptionsLoading: true,
                    options: [],
                    selectedOption: {},
                    selectedOptions: [],
                },
                () => {
                    this.fetchOptions(true)
                        .catch((error) => reject(error))
                        .finally(() => {
                            this.setState(
                                {
                                    dynamicOptionsLoading: false,
                                },
                                () => {
                                    resolve("OK");
                                }
                            );
                        });
                }
            );
        });
    }

    buildOptionsRefresh() {
        if (this.isAutoComplete()) {
            return;
        }
        const loadDynamicOptions = (_: any) => {
            this.triggerDynamicOptionsLoading().catch((error) => {
                console.error(error);
            });
        };
        return <Button loading={this.state.dynamicOptionsLoading} iconName="refresh" onClick={(event) => loadDynamicOptions(event)} />;
    }

    buildDefaultValueRefresh() {
        const fetchDefaultValue = (_: any) => {
            this.setState(
                {
                    defaultValueLoading: true,
                },
                () => {
                    this.fetchDefault(true)
                        .catch((error) => console.error(error))
                        .finally(() => {
                            this.setState(
                                {
                                    value: this.state.default,
                                    defaultValueLoading: false,
                                },
                                this.setStateCallback
                            );
                        });
                }
            );
        };
        return <Button loading={this.state.defaultValueLoading} iconName="refresh" onClick={(event) => fetchDefaultValue(event)} />;
    }

    buildFormFieldSecondaryControl() {
        const customType = this.getCustomType();
        let customControl;
        if (customType && this.props.customActionProvider) {
            const customControlStateCallback = () => {
                this.triggerDynamicOptionsLoading().finally(() => {
                    this.setStateCallback();
                });
            };
            const customActionLabel = this.props.customActionProvider.getCustomActionLabel(customType);
            if (customActionLabel != null) {
                customControl = (
                    <Button
                        onClick={() => {
                            this.props.customActionProvider?.onCustomActionClick(customType, this, (value) => {
                                this.setState(
                                    {
                                        value: value,
                                    },
                                    customControlStateCallback
                                );
                            });
                        }}
                    >
                        {customActionLabel}
                    </Button>
                );
            }
        }
        if (this.state.dynamicOptions) {
            const optionsRefresh = this.buildOptionsRefresh();
            if (customControl) {
                return (
                    <SpaceBetween size="xxxs" direction="horizontal">
                        {optionsRefresh}
                        {customControl}
                    </SpaceBetween>
                );
            } else {
                return optionsRefresh;
            }
        } else {
            return customControl;
        }
    }

    onKeyDown = (event: CustomEvent<BaseKeyDetail>) => {
        if (event.detail.key === "Enter" && this.props.onKeyEnter) {
            this.props.onKeyEnter({
                ref: this,
            });
        }
    };

    onInputStateChange(value: string) {
        this.setState(
            {
                value: value,
            },
            () => {
                if (this.triggerValidate()) {
                    this.setState({}, this.setStateCallback);
                }
            }
        );
    }

    buildInput(props: FormFieldProps) {
        let secondaryControl = null;
        if (this.isRefreshable()) {
            secondaryControl = this.buildDefaultValueRefresh();
        }

        return this.buildFormField(
            <Input
                name={this.props.param.name}
                value={this.state.stringVal()}
                type={this.getInputType()}
                readOnly={this.isReadOnly()}
                autoComplete={false}
                disabled={this.state.disabled}
                onKeyDown={this.onKeyDown}
                autoFocus={this.isAutoFocus()}
                onChange={(event) => {
                    this.onInputStateChange(event.detail.value);
                }}
            />,
            {
                ...props,
                secondaryControl: secondaryControl,
            }
        );
    }

    buildInputArray(props: FormFieldProps) {
        return this.buildFormField(
            <ColumnLayout columns={1}>
                {this.getValueAsStringArray().length === 0 && (
                    <Button
                        variant="normal"
                        onClick={() => {
                            this.setState(
                                {
                                    value: [""],
                                },
                                this.setStateCallback
                            );
                        }}
                    >
                        <FontAwesomeIcon icon={faAdd} />
                    </Button>
                )}
                {this.getValueAsStringArray().length > 0 &&
                    this.getValueAsStringArray().map((value, index) => {
                        return (
                            <ColumnLayout columns={2} key={`${this.props.param.name}-${index}`}>
                                <Input
                                    name={this.props.param.name}
                                    value={value}
                                    type={this.getInputType()}
                                    readOnly={this.isReadOnly()}
                                    autoComplete={false}
                                    disabled={this.state.disabled}
                                    onKeyDown={this.onKeyDown}
                                    autoFocus={index === 0 && this.isAutoFocus()}
                                    onChange={(event) => {
                                        const values: string[] = this.state.value;
                                        values[index] = event.detail.value;
                                        this.setState(
                                            {
                                                value: values,
                                            },
                                            this.setStateCallback
                                        );
                                    }}
                                />
                                <SpaceBetween size="xs" direction="horizontal">
                                    <Button
                                        variant="normal"
                                        onClick={() => {
                                            const values: string[] = this.state.value;
                                            values.push("");
                                            this.setState(
                                                {
                                                    value: values,
                                                },
                                                this.setStateCallback
                                            );
                                        }}
                                    >
                                        <FontAwesomeIcon icon={faAdd} />
                                    </Button>
                                    <Button
                                        variant="normal"
                                        onClick={() => {
                                            const values: string[] = this.state.value;
                                            values.splice(index, 1);
                                            this.setState(
                                                {
                                                    value: values,
                                                },
                                                this.setStateCallback
                                            );
                                        }}
                                    >
                                        <FontAwesomeIcon icon={faRemove} />
                                    </Button>
                                </SpaceBetween>
                            </ColumnLayout>
                        );
                    })}
            </ColumnLayout>,
            props
        );
    }

    onPasswordStateChange(value: string, value2: boolean = false) {
        const stateCallback = () => {
            if (this.props.param.param_type === "new-password") {
                const val1 = this.state.stringVal();
                const val2 = this.state.stringVal2();
                if (!Utils.isEmpty(val1) && !Utils.isEmpty(val2) && val1 === val2) {
                    this.setState({
                        errorCode: null,
                        errorMessage: null,
                    });
                    this.setStateCallback();
                } else if (!Utils.isEmpty(val2)) {
                    this.setState({
                        errorCode: "VERIFY_PASSWORD_DOES_NOT_MATCH",
                        errorMessage: "Passwords do not match",
                    });
                }
            } else if (this.props.param.param_type === "password") {
                this.setStateCallback();
            }
        };

        if (value2) {
            this.setState(
                {
                    value2: value,
                },
                stateCallback
            );
        } else {
            this.setState(
                {
                    value: value,
                },
                stateCallback
            );
        }
    }

    buildPassword(value2: boolean = false, props: FormFieldProps) {
        let label = this.props.param.title;
        let description = this.props.param.description;
        let value = () => this.state.stringVal();
        if (value2) {
            label = `Verify ${label}`;
            description = `Re-${description}`;
            value = () => this.state.stringVal2();
        }
        let key;
        if (value2) {
            key = `f-${this.getParamName()}-2`;
        } else {
            key = `f-${this.getParamName()}-1`;
        }
        return this.buildFormField(
            <Input
                name={this.props.param.name}
                value={value()}
                type="password"
                autoComplete={false}
                disabled={this.state.disabled}
                onKeyDown={this.onKeyDown}
                autoFocus={this.isAutoFocus() && !value2}
                readOnly={this.isReadOnly()}
                onChange={(event) => {
                    this.onPasswordStateChange(event.detail.value, value2);
                }}
            />,
            {
                ...props,
                label: label,
                description: description,
            },
            key
        );
    }

    onAutoSuggestStateChange(value: string) {
        this.setState(
            {
                value: value,
            },
            () => {
                if (this.triggerValidate()) {
                    this.setState({}, this.setStateCallback);
                }
            }
        );
    }

    /**
     * AutoSuggest will preload all options and filtering is performed locally.
     */
    buildAutoSuggest(props: FormFieldProps) {
        let secondaryControl = this.buildFormFieldSecondaryControl();
        return this.buildFormField(
            <Autosuggest
                enteredTextLabel={(value) => `Use: ${value}`}
                value={this.state.stringVal()}
                options={this.state.options}
                disabled={this.state.disabled}
                autoFocus={this.isAutoFocus()}
                onKeyDown={(event) => {
                    if (event.detail.key === "Escape") {
                        // this prevents the modal getting dismissed
                        event.stopPropagation();
                    }
                }}
                onChange={(event) => this.onAutoSuggestStateChange(event.detail.value)}
            />,
            {
                ...props,
                secondaryControl: secondaryControl,
            }
        );
    }

    onAutoCompleteStateChange(value: string) {
        this.setState(
            {
                value: value,
            },
            () => {
                if (this.triggerValidate()) {
                    this.setState({}, this.setStateCallback);
                }
            }
        );
    }

    /**
     * AutoComplete loads options based on text entered by user.
     * onFetchOptions is called as user types the input
     */
    buildAutoComplete(props: FormFieldProps) {
        let secondaryControl = this.buildFormFieldSecondaryControl();
        return this.buildFormField(
            <Autosuggest
                enteredTextLabel={(value) => `Use: ${value}`}
                value={this.state.stringVal()}
                options={this.state.options}
                statusType={this.state.dynamicOptionsLoading ? "loading" : "finished"}
                filteringType="none"
                disabled={this.state.disabled}
                autoFocus={this.isAutoFocus()}
                onKeyDown={(event) => {
                    // prevent the modal getting dismissed on Escape
                    if (event.detail.key === "Escape") {
                        event.stopPropagation();
                    }
                }}
                onLoadItems={(event) => {
                    if (this.props.onFetchOptions) {
                        this.setState(
                            {
                                options: [],
                                dynamicOptionsLoading: true,
                            },
                            () => {
                                this.props.onFetchOptions!({
                                    param: this.getParamName(),
                                    filters: [
                                        {
                                            key: this.getParamName(),
                                            value: event.detail.filteringText,
                                        },
                                    ],
                                })
                                    .then((result) => {
                                        this.setOptions(result);
                                    })
                                    .finally(() => {
                                        this.setState({
                                            dynamicOptionsLoading: false,
                                        });
                                    });
                            }
                        );
                    }
                }}
                onChange={(event) => this.onAutoCompleteStateChange(event.detail.value)}
            />,
            {
                ...props,
                secondaryControl: secondaryControl,
            }
        );
    }

    onDatePickerStateChange(selectedDate: string) {
        this.setState(
            {
                value: selectedDate,
            },
            () => {
                if (this.triggerValidate()) {
                    this.setState({}, this.setStateCallback);
                }
            }
        );
    }

    buildDatePicker(props: FormFieldProps) {
        return this.buildFormField(
            <DatePicker
                onChange={({ detail }) => this.onDatePickerStateChange(detail.value)}
                readOnly={this.isReadOnly()}
                autoFocus={this.isAutoFocus()}
                value={this.state.stringVal()}
                disabled={this.state.disabled}
                openCalendarAriaLabel={(selectedDate) => "Choose Date" + (selectedDate ? `, selected date is ${selectedDate}` : "")}
                placeholder="YYYY/MM/DD"
                nextMonthAriaLabel="Next month"
                previousMonthAriaLabel="Previous month"
                todayAriaLabel="Today"
            />,
            props
        );
    }

    onTextAreaStateChange(value: string) {
        this.setState(
            {
                value: value,
            },
            () => {
                if (this.triggerValidate()) {
                    this.setState({}, this.setStateCallback);
                }
            }
        );
    }

    buildTextArea(props: FormFieldProps) {
        return this.buildFormField(<Textarea onChange={({ detail }) => this.onTextAreaStateChange(detail.value)} readOnly={this.isReadOnly()} autoFocus={this.isAutoFocus()} value={this.state.stringVal()} disabled={this.state.disabled} placeholder={`Enter ${this.props.param.title} ...`} />, props);
    }

    buildTextAreaArray(props: FormFieldProps) {
        return this.buildFormField(<Textarea disabled={this.state.disabled} onChange={({ detail }) => this.onTextAreaStateChange(detail.value)} readOnly={this.isReadOnly()} autoFocus={this.isAutoFocus()} value={this.state.stringVal()} placeholder={`Enter ${this.props.param.title} ...`} />, props);
    }

    onToggleStateChange(value: boolean) {
        this.setState(
            {
                value: value,
            },
            () => {
                if (this.triggerValidate()) {
                    this.setState({}, this.setStateCallback);
                }
            }
        );
    }

    buildToggle(props: FormFieldProps) {
        return this.buildFormField(
            <Toggle
                checked={this.state.booleanVal()}
                disabled={this.state.disabled}
                onChange={(event) => {
                    this.onToggleStateChange(event.detail.checked);
                }}
            ></Toggle>,
            props
        );
    }

    buildExpandable(props: FormFieldProps) {
        return (
            <ExpandableSection
                headerText={this.props.param.optional ?  <span>{this.props.param.title} <i>- optional</i></span> : this.props.param.title}
                expanded={this.state.booleanVal()}
                onChange={(event) => {
                    this.onToggleStateChange(event.detail.expanded);
                }}
            ></ExpandableSection>
        )
    }

    onRadioGroupStateChange(value: string) {
        this.setState(
            {
                value: value,
            },
            () => {
                if (this.triggerValidate()) {
                    this.setState({}, this.setStateCallback);
                }
            }
        );
    }

    onFileUploadStateChange(value: File[]) {
        this.getFileAsBase64String(value[0]).then((result) => {
            this.setState(
                {
                    value: result,
                    value2: value

                },
                () => {
                    if (this.triggerValidate()) {
                        this.setState({}, this.setStateCallback);
                    }
                }
            )
        })
    }

    buildRadioGroup(props: FormFieldProps) {
        return this.buildFormField(<RadioGroup name={this.props.param.name} value={this.state.value} items={this.state.options} onChange={(event) => this.onRadioGroupStateChange(event.detail.value)} />, props);
    }

    buildTilesGroup(props: FormFieldProps) {
        return this.buildFormField(<Tiles name={this.props.param.name} value={this.state.value} items={this.state.options} onChange={(event) => this.onRadioGroupStateChange(event.detail.value)} />, props);
    }

    onSelectStateChange(selectedOption: SelectProps.Option) {
        this.setState(
            {
                value: selectedOption.value,
            },
            () => {
                if (this.triggerValidate()) {
                    this.setState(
                        {
                            selectedOption: selectedOption,
                        },
                        this.setStateCallback
                    );
                }
            }
        );
    }

    getEmptyOptionsLabel(): string {
        if (this.props.param.choices_empty_label) {
            return this.props.param.choices_empty_label;
        }
        return "No Options";
    }

    buildSelect(props: FormFieldProps) {
        let secondaryControl = this.buildFormFieldSecondaryControl();
        return this.buildFormField(<Select selectedOption={this.state.selectedOption} options={this.state.options} empty={this.getEmptyOptionsLabel()} disabled={this.isReadOnly() || this.state.disabled} onChange={(event) => this.onSelectStateChange(event.detail.selectedOption)} />, {
            ...props,
            secondaryControl: secondaryControl,
        });
    }

    onMultiSelectStateChange(selectedOptions: ReadonlyArray<SelectProps.Option>) {
        const values: any[] = [];
        const selectedOptions_: any[] = [];
        selectedOptions.forEach((option) => {
            values.push(option.value);
            selectedOptions_.push(option);
        });
        this.setState(
            {
                value: values,
            },
            () => {
                if (this.triggerValidate()) {
                    this.setState(
                        {
                            selectedOptions: selectedOptions_,
                        },
                        this.setStateCallback
                    );
                }
            }
        );
    }

    buildMultiSelect(props: FormFieldProps) {
        let secondaryControl = this.buildFormFieldSecondaryControl();
        return this.buildFormField(<Multiselect selectedOptions={this.state.selectedOptions} options={this.state.options} filteringType="auto" disabled={this.state.disabled} onChange={(event) => this.onMultiSelectStateChange(event.detail.selectedOptions)} />, {
            ...props,
            secondaryControl: secondaryControl,
        });
    }

    getMemoryUnit(): string {
        const defaultVal: any = this.props.param.default;
        if (defaultVal && defaultVal.unit) {
            return defaultVal.unit;
        }
        return "bytes";
    }

    onMemoryValueStateChange(value: string) {
        this.setState(
            {
                value: {
                    value: Utils.asNumber(value, 0),
                    unit: this.getMemoryUnit(),
                },
            },
            () => {
                if (this.triggerValidate()) {
                    this.setStateCallback();
                }
            }
        );
    }

    buildMemory(props: FormFieldProps) {
        // todo - support multiple units
        return this.buildFormField(
            <Grid gridDefinition={[{ colspan: 10 }, { colspan: 2 }]}>
                <Input
                    name={this.props.param.name}
                    value={this.state.memoryVal()}
                    type="number"
                    inputMode="numeric"
                    readOnly={this.isReadOnly()}
                    autoFocus={this.isAutoFocus()}
                    disabled={this.state.disabled}
                    autoComplete={false}
                    onKeyDown={this.onKeyDown}
                    onChange={(event) => {
                        this.onMemoryValueStateChange(event.detail.value);
                    }}
                />
                <span>{this.getMemoryUnit()}</span>
            </Grid>,
            props
        );
    }

    onAmountStateChange(value: string) {
        // todo remove hardcoding for currency.
        this.setState(
            {
                value: {
                    amount: Utils.asNumber(value, 0.0, true),
                    unit: "USD",
                },
            },
            () => {
                if (this.triggerValidate()) {
                    this.setState({}, this.setStateCallback);
                }
            }
        );
    }

    buildAmount(props: FormFieldProps) {
        return this.buildFormField(
            <Grid gridDefinition={[{ colspan: 10 }, { colspan: 2 }]}>
                <Input
                    name={this.props.param.name}
                    value={this.state.amountVal()}
                    type="number"
                    inputMode="decimal"
                    disabled={this.state.disabled}
                    readOnly={this.isReadOnly()}
                    autoFocus={this.isAutoFocus()}
                    autoComplete={false}
                    onKeyDown={this.onKeyDown}
                    onChange={(event) => {
                        this.onAmountStateChange(event.detail.value);
                    }}
                />
                <span>USD</span>
            </Grid>,
            props
        );
    }

    buildStaticText() {
        let textBlock;
        const paramType = this.props.param.param_type;
        if (paramType === "heading1") {
            textBlock = <h1>{this.getParamMeta().title}</h1>;
        } else if (paramType === "heading2") {
            textBlock = <h2>{this.getParamMeta().title}</h2>;
        } else if (paramType === "heading3") {
            textBlock = <h3>{this.getParamMeta().title}</h3>;
        } else if (paramType === "heading4") {
            textBlock = <h4>{this.getParamMeta().title}</h4>;
        } else if (paramType === "heading5") {
            textBlock = <h5>{this.getParamMeta().title}</h5>;
        } else if (paramType === "heading6") {
            textBlock = <h6>{this.getParamMeta().title}</h6>;
        } else if (paramType === "paragraph") {
            textBlock = <p>{this.getParamMeta().title}</p>;
        }
        return (
            <div>
                {textBlock}
                {Utils.isNotEmpty(this.getParamMeta().description) && <p>{this.getParamMeta().description}</p>}
            </div>
        );
    }

    buildFileUpload(props: FormFieldProps) {
        return this.buildFormField(
            <FileUpload
                onChange={({ detail }) => this.onFileUploadStateChange(detail.value)}
                value={this.state.fileVal()}
                i18nStrings={{
                    uploadButtonText: e =>
                      e ? "Choose files" : "Choose file",
                    dropzoneText: e =>
                      e
                        ? "Drop files to upload"
                        : "Drop file to upload",
                    removeFileAriaLabel: e =>
                      `Remove file ${e + 1}`,
                    limitShowFewer: "Show fewer files",
                    limitShowMore: "Show more files",
                    errorIconAriaLabel: "Error"
                  }}
                  showFileSize
            />,
            props
        )
    }

    onContainerArrayStateChange(event: IdeaFormFieldStateChangeEvent, index: number) {
        const values: Record<string, string>[] = this.getListOfStringRecords();
        if (!event.param.name || !values[index]) {
            this.setState({
                errorMessage: "Unable to map container state change."
            })
        } else {
            values[index][event.param.name] = event.value
            this.setState(
                {
                    value: values,
                },
                () => {
                    if (this.triggerValidate()) {
                        this.setState({}, this.setStateCallback);
                    }
                }
            );
        }
    }

    buildContainerArray(props: FormFieldProps): React.ReactNode {
        return this.buildFormField(
            <ColumnLayout columns={1}>
                {this.getListOfStringRecords().length === 0 && (
                    <Button
                        variant="normal"
                        onClick={() => {
                            this.setState(
                                {
                                    value: [{}],
                                },
                                this.setStateCallback
                            );
                        }}
                    >
                        <FontAwesomeIcon icon={faAdd} />
                    </Button>
                )}
                {
                    this.getListOfStringRecords().length > 0 && this.getListOfStringRecords().map((value, index) => {
                        const numOfColumns = this.props.param.container_items?.length ? this.props.param.container_items.length : 0
                        return (
                            <ColumnLayout columns={numOfColumns} key={`${this.props.param.name}-${index}`}>
                                {
                                    (() => {
                                        let container: JSX.Element[] = [];
                                        this.props.param.container_items?.map((form) => (
                                            container.push(<IdeaFormField
                                                key={`${form.name}`}
                                                module={`${form.name}`}
                                                param={form}
                                                onStateChange={(event) => {
                                                    this.onContainerArrayStateChange(event, index)
                                                }}
                                                onFetchOptions={this.props.onFetchOptions}
                                                stretch={props.stretch}
                                                toolsOpen={this.props.toolsOpen} 
                                                tools={this.props.tools}
                                                onToolsChange={this.props.onToolsChange}
                                            />)
                                        ))
                                        return container;
                                    })()
                                }
                            </ColumnLayout>

                        );
                    })
                }
                {
                    this.getListOfStringRecords().length > 0 && (
                        <SpaceBetween size="xs" direction="horizontal">
                            <Button
                                variant="normal"
                                onClick={() => {
                                    const values = this.getListOfStringRecords();
                                    values.push({});
                                    this.setState(
                                        {
                                            value: values,
                                        },
                                        this.setStateCallback
                                    );
                                }}
                            >
                                <FontAwesomeIcon icon={faAdd} />
                            </Button>
                            <Button
                                variant="normal"
                                onClick={() => {
                                    const values = this.getListOfStringRecords();
                                    values.pop();
                                    this.setState(
                                        {
                                            value: values,
                                        },
                                        this.setStateCallback
                                    );
                                }}
                            >
                                <FontAwesomeIcon icon={faRemove} />
                            </Button>
                        </SpaceBetween>
                    )
                }
            </ColumnLayout>,
            props
        )
    }


    buildAttributeEditor(props: FormFieldProps) {
        const container_items = this.props.param.container_items
        return this.buildFormField(<AttributeEditor
                onAddButtonClick={() => this.setState({
                        value: [...this.getListOfAttributeEditorRecords(), {key: "", value: ""}],
                    }, this.setStateCallback
                )}
                onRemoveButtonClick={(changeEvent) => {
                    const tmpItems = [...this.getListOfAttributeEditorRecords()];
                    tmpItems.splice(changeEvent.detail.itemIndex, 1);
                    this.setState({
                        value: tmpItems
                    }, this.setStateCallback)
                }}
                addButtonText={`Add ${this.props.param.attributes_editor_type}`}
                removeButtonText={`Remove ${this.props.param.attributes_editor_type}`}
                items={this.getListOfAttributeEditorRecords()}
                empty={`There are no ${this.props.param.attributes_editor_type} that have been added`}
                definition={(() => {
                    if (container_items?.length === 2) {
                        const key = container_items[0]
                        const value = container_items[1]
  
                        return [
                            {
                                label: <FormField label={<span>{key.title}{key.description ? <i> - {key.description}</i> : ""}</span>} info={key.markdown && <Link variant="info" onFollow={() => this.handleToolsOpen(key.markdown)}>Info</Link>}></FormField>,
                                control: (item: { key: string, value: string, error?: string }, itemIndex: number) => (
                                    <Input
                                        value={item.key}
                                        type={this.getContainerInputType(key)}
                                        onChange={(e) => {
                                            const tmpItems = [...this.getListOfAttributeEditorRecords()];
                                            tmpItems[itemIndex].key = e.detail.value;
                                            this.setState({
                                                value: tmpItems
                                            }, this.setStateCallback)
                                        }}
                                    ></Input>
                                ),
                                errorText: (item: {key: string, value: string, error?: string}) => { return item.error }
                            },
                            {
                                label: <FormField label={<span>{value.title}{value.description ? <i> - {value.description}</i> : ""}</span>} info={value.markdown && <Link variant="info" onFollow={() => this.handleToolsOpen(value.markdown)}>Info</Link>}></FormField>,
                                control: (item: { key: string, value: string, error?: string }, itemIndex: number) => (
                                    <Input
                                        value={item.value}
                                        type={this.getContainerInputType(value)}
                                        onChange={(e) => {
                                            const tmpItems = [...this.getListOfAttributeEditorRecords()];
                                            tmpItems[itemIndex].value = e.detail.value;
                                            this.setState({
                                                value: tmpItems
                                            }, this.setStateCallback)
                                        }}
                                    ></Input>
                                ),
                                errorText: (item: {key: string, value: string, error?: string}) => { return item.error }
                            }
                        ]

                    }
                    return [];
                })()
                }/>,
            props
        )
    }

    getRenderType(): string {
        const type = this.getNativeType();
        const param_type = this.props.param.param_type;
        const multiple = this.props.param.multiple != null ? this.props.param.multiple : false;
        const multiline = this.props.param.multiline != null ? this.props.param.multiline : false;

        if (param_type && ["heading1", "heading2", "heading3", "heading4", "heading5", "heading6", "paragraph", "code"].includes(param_type)) {
            return "static-text";
        } else if (param_type === "file-upload") {
            return "file-upload";
        }
        if (multiple) {
            if (param_type === "select") {
                return "multi-select";
            } else if (param_type === "select_or_text") {
                return "auto-suggest";
            } else if (param_type === "container"){
                return "parent_parameter_array"
            } else if (param_type === "attribute_editor") {
                return "attribute_editor"
            }
                else {
                if (multiline) {
                    return "textarea-array";
                } else {
                    return "input-array";
                }
            }
        } else {
            if (type === "string" || type === "number") {
                if (multiline) {
                    return "textarea";
                } else if (param_type === "select") {
                    return "select";
                } else if (param_type === "select_or_text") {
                    return "auto-suggest";
                } else if (param_type === "autocomplete") {
                    return "auto-complete";
                } else if (param_type === "password") {
                    return "password";
                } else if (param_type === "new-password") {
                    return "new-password";
                } else if (param_type === "datepicker") {
                    return "datepicker";
                } else if (param_type === "tiles") {
                    return "tiles";
                } else if (param_type === "radio-group") {
                    return "radio-group";
                }
                return "input";
            } else if (type === "boolean") {
                if (param_type === "expandable") {
                    return "expandable"
                }
                return "toggle";
            } else if (type === "amount") {
                return "amount";
            } else if (type === "memory") {
                return "memory";
            } else {
                return "input";
            }
        }
    }

    isVisible(): boolean {
        if (this.props.visible != null) {
            return this.props.visible;
        }
        return true;
    }

    render() {
        const type = this.getRenderType();

        const stretch = this.props.stretch != null ? this.props.stretch : false;

        const formFields: React.ReactNode[] = [];
        if (type === "input") {
            formFields.push(this.buildInput({ stretch: stretch }));
        } else if (type === "input-array") {
            formFields.push(this.buildInputArray({ stretch: stretch }));
        } else if (type === "password") {
            formFields.push(this.buildPassword(false, { stretch: stretch }));
        } else if (type === "new-password") {
            formFields.push(this.buildPassword(false, { stretch: stretch }));
            formFields.push(this.buildPassword(true, { stretch: stretch }));
        } else if (type === "auto-suggest") {
            formFields.push(this.buildAutoSuggest({ stretch: stretch }));
        } else if (type === "auto-complete") {
            formFields.push(this.buildAutoComplete({ stretch: stretch }));
        } else if (type === "textarea") {
            formFields.push(this.buildTextArea({ stretch: stretch }));
        } else if (type === "textarea-array") {
            formFields.push(this.buildTextAreaArray({ stretch: stretch }));
        } else if (type === "toggle") {
            formFields.push(this.buildToggle({ stretch: stretch }));
        } else if (type === "expandable") {
            formFields.push(this.buildExpandable({stretch: stretch}));
        } else if (type === "radio-group") {
            formFields.push(this.buildRadioGroup({ stretch: stretch }));
        } else if (type === "select") {
            formFields.push(this.buildSelect({ stretch: stretch }));
        } else if (type === "multi-select") {
            formFields.push(this.buildMultiSelect({ stretch: stretch }));
        } else if (type === "memory") {
            formFields.push(this.buildMemory({ stretch: stretch }));
        } else if (type === "amount") {
            formFields.push(this.buildAmount({ stretch: stretch }));
        } else if (type === "static-text") {
            formFields.push(this.buildStaticText());
        } else if (type === "datepicker") {
            formFields.push(this.buildDatePicker({ stretch: stretch }));
        } else if (type === "file-upload") {
            formFields.push(this.buildFileUpload({ stretch: stretch }));
        } else if (type === "tiles") {
            formFields.push(this.buildTilesGroup({ stretch: stretch }));
        } else if ( type === "attribute_editor") {
            formFields.push(this.buildAttributeEditor({ stretch: stretch}));
        } else if (type === "parent_parameter_array") {
            formFields.push(this.buildContainerArray({ stretch: stretch }));
        } else {
            formFields.push(this.buildInput({ stretch: stretch }));
        }

        if (formFields.length === 1) {
            return <ColumnLayout columns={1}>{formFields[0]}</ColumnLayout>;
        } else {
            return (
                <ColumnLayout columns={1}>
                    {formFields.map((formField, index) => {
                        return <div key={index}>{formField}</div>;
                    })}
                </ColumnLayout>
            );
        }
    }
}

export default IdeaFormField;
