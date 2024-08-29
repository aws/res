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

import React, { Component, RefObject } from "react";
import { AttributeEditor, Box, Button, CodeEditor, ColumnLayout, Container, Grid, Icon, Input, SpaceBetween, Tabs } from "@cloudscape-design/components";
import { SocaUserInputChoice, SocaUserInputParamMetadata } from "../../client/data-model";
import IdeaForm from "../../components/form";
import { IdeaFormField } from "../../components/form-field";
import Utils from "../../common/utils";
import { DragDropContext, Droppable, Draggable } from "react-beautiful-dnd";
import { faCheck, faCopy, faEdit, faTrash, faWindowClose } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { CodeEditorProps } from "@cloudscape-design/components/code-editor/interfaces";
import "ace-builds/css/ace.css";
import "ace-builds/css/theme/dawn.css";

const DragDropContextAlt: any = DragDropContext;
const DroppableAlt: any = Droppable;
const DraggableAlt: any = Draggable;

export interface IdeaFormBuilderProps {
    params: SocaUserInputParamMetadata[];
    infoSection?: React.ReactNode;
}

export interface IdeaFormBuilderState {
    metadata: IdeaFormBuilderFieldProps[];
    output: SocaUserInputParamMetadata[];
    ace: any;
    preferences: any;
    language: CodeEditorProps.Language;
    content: string;
    values: any;
}

export interface IdeaFormBuilderFieldProps {
    id: string;
    param: SocaUserInputParamMetadata;
    onCreate?: (field: IdeaFormBuilderField) => void;
    onDelete?: (field: IdeaFormBuilderField) => void;
    onCopy?: (field: IdeaFormBuilderField) => void;
    onUpdate?: (field: IdeaFormBuilderField) => void;
    onInsertBefore?: (field: IdeaFormBuilderField) => void;
    onInsertAfter?: (field: IdeaFormBuilderField) => void;
}

export interface IdeaFormBuilderFieldState {
    debugMode: boolean;
    edit: boolean;
    param: SocaUserInputParamMetadata;
    choices: SocaUserInputChoice[];
    showPreview: boolean;
    buildParams: SocaUserInputParamMetadata[];
}

class IdeaFormBuilderField extends Component<IdeaFormBuilderFieldProps, IdeaFormBuilderFieldState> {
    form: RefObject<IdeaForm>;
    preview: RefObject<IdeaFormField>;

    constructor(props: IdeaFormBuilderFieldProps) {
        super(props);
        this.form = React.createRef();
        this.preview = React.createRef();

        this.state = {
            debugMode: false,
            edit: false,
            param: this.props.param,
            choices: this.props.param.choices ? this.props.param.choices : [],
            showPreview: true,
            buildParams: [
                {
                    name: "field_type",
                    title: "Field Type",
                    description: "Form Field Type",
                    data_type: "str",
                    param_type: "select",
                    default: this.getFieldType(),
                    choices: [
                        {
                            title: "Text",
                            value: "text",
                        },
                        {
                            title: "Number",
                            value: "number",
                        },
                        {
                            title: "Select",
                            value: "select",
                        },
                        {
                            title: "Text Area",
                            value: "textarea",
                        },
                        {
                            title: "Toggle",
                            value: "toggle",
                        },
                        {
                            title: "Password",
                            value: "password",
                        },
                        {
                            title: "Heading 1",
                            value: "heading1",
                        },
                        {
                            title: "Heading 2",
                            value: "heading2",
                        },
                        {
                            title: "Heading 3",
                            value: "heading3",
                        },
                        {
                            title: "Heading 4",
                            value: "heading4",
                        },
                        {
                            title: "Heading 5",
                            value: "heading5",
                        },
                    ],
                },
                {
                    name: "name",
                    title: "Name",
                    description: "Name of the form field",
                    data_type: "str",
                    param_type: "text",
                    default: this.props.param.name,
                },
                {
                    name: "title",
                    title: "Title",
                    description: "Title of the form field",
                    data_type: "str",
                    param_type: "text",
                    default: this.props.param.title,
                },
                {
                    name: "description",
                    title: "Description",
                    description: "Description for the form field",
                    data_type: "str",
                    param_type: "text",
                    default: this.props.param.description,
                    when: {
                        param: "field_type",
                        not_in: ["heading1", "heading2", "heading3", "heading4", "heading5"],
                    },
                },
                {
                    name: "help_text",
                    title: "Help Text",
                    description: "Help text for the form field.",
                    data_type: "str",
                    param_type: "text",
                    default: this.props.param.help_text,
                    when: {
                        param: "field_type",
                        not_in: ["heading1", "heading2", "heading3", "heading4", "heading5"],
                    },
                },
                {
                    name: "readonly",
                    title: "Is Readonly?",
                    description: "User will not be able to edit this value.",
                    data_type: "bool",
                    param_type: "confirm",
                    default: this.props.param.readonly,
                    when: {
                        param: "field_type",
                        not_in: ["heading1", "heading2", "heading3", "heading4", "heading5"],
                    },
                },
                {
                    name: "required",
                    title: "Is Required?",
                    description: "User must enter this value.",
                    data_type: "bool",
                    param_type: "confirm",
                    default: this.props.param.validate?.required,
                    when: {
                        param: "field_type",
                        not_in: ["heading1", "heading2", "heading3", "heading4", "heading5"],
                    },
                },
            ],
        };
    }

    componentDidMount() {
        this.onCreate();
    }

    getId(): string {
        return this.props.id;
    }

    getPreview(): IdeaFormField {
        return this.preview.current!;
    }

    getFieldTypeToParam(name: string): any {
        if (name === "text") {
            return {
                data_type: "str",
                param_type: "text",
            };
        } else if (name === "textarea") {
            return {
                data_type: "str",
                param_type: "text",
                multiline: true,
            };
        } else if (name === "toggle") {
            return {
                data_type: "bool",
                param_type: "confirm",
            };
        } else if (name === "select") {
            return {
                data_type: "str",
                param_type: "select",
            };
        } else if (name === "number") {
            return {
                data_type: "int",
                param_type: "text",
            };
        } else if (name === "password") {
            return {
                data_type: "str",
                param_type: "password",
            };
        } else if (name.startsWith("heading")) {
            return {
                data_type: "str",
                param_type: name,
            };
        } else {
            return {
                data_type: "str",
                param_type: "text",
            };
        }
    }

    getFieldType(): string {
        const dataType = this.props.param.data_type!;
        const paramType = this.props.param.param_type!;
        const multiline = Utils.asBoolean(this.props.param.multiline);
        let result = "text";
        if (["heading1", "heading2", "heading3", "heading4", "heading5", "heading6"].includes(paramType)) {
            result = paramType;
        } else if (paramType === "password") {
            result = "password";
        } else if (paramType === "select") {
            result = "select";
        } else if (paramType === "text" && multiline) {
            result = "textarea";
        } else if (dataType === "int" || dataType === "float") {
            result = "number";
        } else if (dataType === "bool") {
            result = "toggle";
        }
        return result;
    }

    build(): any {
        if (this.form.current) {
            let param = this.form.current!.getValues();

            if (this.getFieldType() === "heading") {
                return {
                    title: Utils.asString(param.title),
                    param_type: "heading3",
                };
            }

            param.optional = Utils.asBoolean(param.optional);
            param.multiple = Utils.asBoolean(param.multiple);
            param.multiline = Utils.asBoolean(param.multiline);
            param.readonly = Utils.asBoolean(param.readonly);
            param.validate = {
                required: Utils.asBoolean(param.required),
            };
            param.choices = this.state.choices;
            param.default = this.getPreview().getAnyValue();

            const fieldTypeValue = param.field_type!;
            const paramType = this.getFieldTypeToParam(fieldTypeValue);

            return {
                ...param,
                ...paramType,
            };
        } else {
            return this.state.param;
        }
    }

    getParam(): SocaUserInputParamMetadata {
        let param: any = this.state.param;
        // clean up properties in un expected places.
        // properties are appropriately set by build() in the right place and name
        delete param["required"];
        delete param["field_type"];
        return param;
    }

    getBuildParam(name: string): SocaUserInputParamMetadata {
        const found = this.state.buildParams.find((param) => param.name! === name);
        return found!;
    }

    onEdit = () => {
        if (this.state.edit) {
            const param = this.build();
            const buildParams = this.state.buildParams;
            buildParams.forEach((buildParam) => {
                buildParam.default = param[buildParam.name!];
            });
            this.setState(
                {
                    param,
                    buildParams,
                },
                () => {
                    this.setState({
                        edit: false,
                    });
                    if (this.props.onUpdate) {
                        this.props.onUpdate(this);
                    }
                }
            );
        } else {
            this.setState({
                edit: true,
            });
        }
    };

    onClose = () => {
        this.setState({
            edit: false,
        });
    };

    onCreate = () => {
        if (this.props.onCreate) {
            this.props.onCreate(this);
        }
    };

    onDelete = () => {
        if (this.props.onDelete) {
            this.props.onDelete(this);
        }
    };

    onCopy = () => {
        if (this.props.onCopy) {
            this.props.onCopy(this);
        }
    };

    setChoices(choices: SocaUserInputChoice[]) {
        this.setState(
            {
                param: {
                    ...this.state.param,
                    choices: choices,
                },
                choices: choices,
                showPreview: false,
            },
            () => {
                this.setState({
                    showPreview: true,
                });
            }
        );
    }

    render() {
        const editIcon = () => (this.state.edit ? faCheck : faEdit);
        return (
            <Grid gridDefinition={[{ colspan: 1 }, { colspan: 9 }, { colspan: 2 }]}>
                <div style={{ display: "flex", flexDirection: "row", alignItems: "center", justifyContent: "center", height: "100%" }}>
                    <Icon name="expand" />
                </div>
                {this.state.edit && (
                    <div>
                        {this.state.debugMode && <p>{this.props.id}</p>}
                        <Container variant="default">
                            <IdeaForm
                                ref={this.form}
                                name={this.props.id}
                                showHeader={false}
                                showActions={false}
                                params={this.state.buildParams}
                                columns={2}
                                values={this.props.param}
                                onStateChange={(event) => {
                                    const param = this.build();
                                    this.setState({
                                        param: param,
                                    });
                                }}
                            />

                            {this.state.param.param_type === "select" && (
                                <div>
                                    <Box margin={{ bottom: "xxxs", top: "l" }} color="text-label">
                                        Choices
                                    </Box>
                                    <AttributeEditor
                                        items={this.state.choices}
                                        addButtonText="Add"
                                        removeButtonText="Remove"
                                        onAddButtonClick={() => {
                                            const choices = this.state.choices;
                                            choices.push({});
                                            this.setChoices(choices);
                                        }}
                                        onRemoveButtonClick={(event) => {
                                            const choices = this.state.choices;
                                            choices.splice(event.detail.itemIndex, 1);
                                            this.setChoices(choices);
                                        }}
                                        definition={[
                                            {
                                                label: "Label",
                                                control: (item: SocaUserInputChoice) => (
                                                    <Input
                                                        value={Utils.asString(item.title)}
                                                        onChange={(event) => {
                                                            const choices = this.state.choices;
                                                            choices.forEach((choice) => {
                                                                if (item.value === choice.value) {
                                                                    choice.title = event.detail.value;
                                                                }
                                                            });
                                                            this.setChoices(choices);
                                                        }}
                                                    />
                                                ),
                                            },
                                            {
                                                label: "Value",
                                                control: (item: SocaUserInputChoice) => (
                                                    <Input
                                                        value={Utils.asString(item.value)}
                                                        onChange={(event) => {
                                                            const choices = this.state.choices;
                                                            choices.forEach((choice) => {
                                                                if (item.title === choice.title) {
                                                                    choice.value = event.detail.value;
                                                                }
                                                            });
                                                            this.setChoices(choices);
                                                        }}
                                                    />
                                                ),
                                            },
                                        ]}
                                    />
                                </div>
                            )}

                            <SpaceBetween direction="vertical" size="m">
                                <div>
                                    <h4>Preview</h4>
                                    <div style={{ backgroundColor: "#f1f1f1", boxSizing: "border-box", padding: "20px" }}>{this.state.showPreview && <IdeaFormField ref={this.preview} module={this.props.id} param={this.state.param} />}</div>
                                </div>

                                <Box float="right">
                                    <SpaceBetween size={"xs"} direction="horizontal">
                                        <Button onClick={this.onEdit} variant="primary">
                                            <FontAwesomeIcon icon={editIcon()} /> Save
                                        </Button>
                                    </SpaceBetween>
                                </Box>
                            </SpaceBetween>
                        </Container>
                    </div>
                )}
                {!this.state.edit && (
                    <div>
                        {this.state.debugMode && <p>{this.props.id}</p>}
                        <Container variant="default">
                            <IdeaFormField module={this.props.id} param={this.build()} value={this.state.param.default} />
                        </Container>
                    </div>
                )}
                <SpaceBetween size="xs" direction="vertical">
                    <SpaceBetween size="xxxs" direction="horizontal">
                        {!this.state.edit && (
                            <Button onClick={this.onEdit} variant="normal">
                                <FontAwesomeIcon icon={editIcon()} />
                            </Button>
                        )}
                        {this.state.edit && (
                            <Button onClick={this.onClose} variant="normal">
                                <FontAwesomeIcon icon={faWindowClose} />
                            </Button>
                        )}
                    </SpaceBetween>
                    <Button onClick={this.onCopy} variant="normal">
                        <FontAwesomeIcon icon={faCopy} />
                    </Button>
                    <Button onClick={this.onDelete} variant="normal">
                        <FontAwesomeIcon icon={faTrash} />
                    </Button>
                </SpaceBetween>
            </Grid>
        );
    }
}

class SocaFormBuilder extends Component<IdeaFormBuilderProps, IdeaFormBuilderState> {
    fields: {
        [k: string]: IdeaFormBuilderField;
    };

    previewForm: RefObject<IdeaForm>;

    constructor(props: IdeaFormBuilderProps) {
        super(props);
        this.fields = {};
        this.previewForm = React.createRef();
        this.state = {
            metadata: [],
            output: [],
            ace: undefined,
            preferences: undefined,
            content: "",
            language: "json",
            values: {},
        };
    }

    componentDidMount() {
        import("ace-builds").then((ace) => {
            import("ace-builds/webpack-resolver").then(() => {
                ace.config.set("useStrictCSP", true);
                ace.config.set("loadWorkerFromBlob", false);
                this.setState({
                    ace: ace,
                });
            });
        });
        this.props.params.forEach((param) => {
            this.addField(param);
        });
    }

    getExampleParam(): SocaUserInputParamMetadata {
        return {
            name: `example_name_${Utils.getRandomInt(10000, 99999)}`,
            title: "Example Title",
            description: "Example Description",
            help_text: "Example Help Text",
            data_type: "str",
            param_type: "text",
            validate: {
                required: true,
            },
        };
    }

    addField(param?: SocaUserInputParamMetadata, position?: number) {
        const metadata = this.state.metadata;
        const entry = {
            id: Utils.getUUID(),
            param: param ? param : this.getExampleParam(),
        };
        if (position == null || position < 0) {
            metadata.push(entry);
        } else {
            metadata.splice(position, 0, entry);
        }
        this.setState({
            metadata: metadata,
        });
    }

    getField(fieldId: string): IdeaFormBuilderField | null {
        if (fieldId in this.fields) {
            return this.fields[fieldId];
        }
        return null;
    }

    setFields(params: SocaUserInputParamMetadata[]) {
        const metadata: IdeaFormBuilderFieldProps[] = [];
        params.forEach((param) =>
            metadata.push({
                id: Utils.getUUID(),
                param: param,
            })
        );
        this.setState({
            metadata: metadata,
        });
    }

    moveField(fieldId: string, oldIndex: number, newIndex: number) {
        const formField = this.getField(fieldId);
        if (formField == null) {
            return;
        }
        const fields: any[] = this.state.metadata;
        if (newIndex >= fields.length) {
            let k = newIndex - fields.length + 1;
            while (k--) {
                fields.push(null);
            }
        }
        const fieldMetadata = this.state.metadata[oldIndex];
        fieldMetadata.param = formField.build();
        fields.splice(newIndex, 0, fields.splice(oldIndex, 1)[0]);
        this.setState({
            metadata: fields,
        });
    }

    getFieldIndex(fieldId: string): number {
        let found = -1;
        this.state.metadata.forEach((entry, index) => {
            if (entry.id === fieldId) {
                found = index;
                return false;
            }
        });
        if (found >= 0) {
            return found;
        }
        return -1;
    }

    buildFormBuilder() {
        return (
            <DragDropContextAlt
                onDragEnd={(event: any) => {
                    if (event.reason === "DROP") {
                        const sourceIndex = event.source.index;
                        const destIndex = event.destination!.index;
                        if (sourceIndex === destIndex) {
                            return;
                        }
                        this.moveField(event.draggableId, sourceIndex, destIndex);
                    }
                }}
            >
                <DroppableAlt droppableId="test">
                    {(provided: any) => (
                        <div ref={provided.innerRef}>
                            {this.state.metadata.map((entry, index) => {
                                return (
                                    <DraggableAlt key={entry.id} draggableId={entry.id} index={index}>
                                        {(provided: any) => (
                                            <div ref={provided.innerRef} {...provided.draggableProps} {...provided.dragHandleProps}>
                                                <IdeaFormBuilderField
                                                    key={entry.id}
                                                    id={entry.id}
                                                    param={entry.param}
                                                    onCreate={(field) => {
                                                        const metadata = this.state.metadata;
                                                        metadata.forEach((entry) => {
                                                            if (field.getId() === entry.id) {
                                                                entry.param = field.getParam();
                                                            }
                                                        });
                                                        this.setState({
                                                            metadata: metadata,
                                                        });
                                                        this.fields[field.getId()] = field;
                                                    }}
                                                    onDelete={(field) => {
                                                        let found: number = -1;
                                                        this.state.metadata.forEach((entry, index) => {
                                                            if (entry.id === field.getId()) {
                                                                found = index;
                                                            }
                                                        });
                                                        const metadata = this.state.metadata;
                                                        if (found >= 0) {
                                                            metadata.splice(found, 1);
                                                        }
                                                        this.setState({
                                                            metadata: metadata,
                                                        });
                                                        delete this.fields[field.getId()];
                                                    }}
                                                    onUpdate={(field) => {
                                                        const metadata = this.state.metadata;
                                                        metadata.forEach((entry) => {
                                                            if (field.getId() === entry.id) {
                                                                entry.param = field.getParam();
                                                            }
                                                        });
                                                        this.setState({
                                                            metadata: metadata,
                                                        });
                                                    }}
                                                    onCopy={(field) => {
                                                        const param = field.getParam();
                                                        this.addField(
                                                            {
                                                                ...param,
                                                                name: `${param.name}_${Utils.getRandomInt(10000, 99999)}`,
                                                            },
                                                            this.getFieldIndex(field.getId()) + 1
                                                        );
                                                    }}
                                                />
                                            </div>
                                        )}
                                    </DraggableAlt>
                                );
                            })}
                            {provided.placeholder}
                        </div>
                    )}
                </DroppableAlt>
            </DragDropContextAlt>
        );
    }

    getFormParams() {
        if (this.state.metadata.length === 0) {
            return [];
        }
        const params: any[] = [];
        this.state.metadata.forEach((entry) => {
            params.push(entry.param);
        });
        return params;
    }

    buildJsonEditor() {
        return (
            <CodeEditor
                id="param-metadata-json"
                ace={this.state.ace}
                language={this.state.language}
                value={this.state.content}
                preferences={this.state.preferences}
                onPreferencesChange={(e) =>
                    this.setState({
                        preferences: e.detail,
                    })
                }
                onChange={(e) => {
                    this.setState({
                        content: e.detail.value,
                    });
                    try {
                        this.setFields(JSON.parse(e.detail.value));
                    } catch (e) {
                        console.error(e);
                    }
                }}
                loading={false}
                i18nStrings={{
                    loadingState: "Loading code editor",
                    errorState: "There was an error loading the code editor.",
                    errorStateRecovery: "Retry",
                    editorGroupAriaLabel: "Code editor",
                    statusBarGroupAriaLabel: "Status bar",
                    cursorPosition: (row, column) => `Ln ${row}, Col ${column}`,
                    errorsTab: "Errors",
                    warningsTab: "Warnings",
                    preferencesButtonAriaLabel: "Preferences",
                    paneCloseButtonAriaLabel: "Close",
                    preferencesModalHeader: "Preferences",
                    preferencesModalCancel: "Cancel",
                    preferencesModalConfirm: "Confirm",
                    preferencesModalWrapLines: "Wrap lines",
                    preferencesModalTheme: "Theme",
                    preferencesModalLightThemes: "Light themes",
                    preferencesModalDarkThemes: "Dark themes",
                }}
            />
        );
    }

    buildInfoSection() {
        if (this.props.infoSection) {
            return this.props.infoSection;
        } else {
            return (
                <div>
                    <p>
                        Design your form using <strong>Form Builder</strong>. You can preview the generated form using the <strong>Preview Form</strong> tab.{" "}
                    </p>
                </div>
            );
        }
    }

    render() {
        return (
            <div className={"idea-form-builder"}>
                <ColumnLayout columns={2}>
                    {this.buildInfoSection()}
                    <div>
                        <Box float="right">
                            <SpaceBetween size="xs" direction="horizontal">
                                <Button variant="normal" onClick={() => this.setFields([])}>
                                    Reset Form
                                </Button>
                                <Button variant="primary" onClick={() => this.addField()}>
                                    Add Form Field
                                </Button>
                            </SpaceBetween>
                        </Box>
                    </div>
                </ColumnLayout>

                <Tabs
                    onChange={(event) => {
                        if (event.detail.activeTabId === "json-content") {
                            this.setState({
                                content: JSON.stringify(this.getFormParams(), null, 4),
                            });
                        }
                    }}
                    tabs={[
                        {
                            id: "preview-form",
                            label: "Preview Form",
                            content: (
                                <ColumnLayout columns={2}>
                                    <Container variant="default">
                                        <IdeaForm
                                            ref={this.previewForm}
                                            name="preview-form"
                                            params={this.getFormParams()}
                                            showHeader={false}
                                            primaryCtaTitle="Check Form Parameters"
                                            secondaryCtaTitle="Reset"
                                            onSubmit={() => {
                                                if (!this.previewForm.current!.validate()) {
                                                    return;
                                                }
                                                this.setState({
                                                    values: this.previewForm.current!.getValues(),
                                                });
                                            }}
                                        />
                                    </Container>
                                    <Container variant="default">
                                        <p>
                                            Click <strong>Check Form Parameters</strong> to verify the generated values below:
                                        </p>
                                        <div className={"form-parameters"}>
                                            <pre>{JSON.stringify(this.state.values, null, 4)}</pre>
                                        </div>
                                    </Container>
                                </ColumnLayout>
                            ),
                        },
                        {
                            id: "build-form",
                            label: "Form Builder",
                            content: this.buildFormBuilder(),
                        },
                        {
                            id: "json-content",
                            label: "Form Builder (Advanced Mode using JSON)",
                            content: this.buildJsonEditor(),
                        },
                    ]}
                />
            </div>
        );
    }
}

export default SocaFormBuilder;
