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
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import IdeaAppLayout, { IdeaAppLayoutProps } from "../../components/app-layout";
import IdeaListView from "../../components/list-view";
import IdeaForm from "../../components/form";
import { EmailTemplate } from "../../client/data-model";
import { EmailTemplatesClient } from "../../client";
import { AppContext } from "../../common";
import { ClusterSettingsService } from "../../service";
import Utils from "../../common/utils";
import { TableProps } from "@cloudscape-design/components/table/interfaces";
import { withRouter } from "../../navigation/navigation-utils";

export interface EmailTemplatesProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {}

export interface EmailTemplatesState {
    emailTemplateSelected: boolean;
    createModalType: string;
    showCreateForm: boolean;
}

const EMAIL_TEMPLATES_TABLE_COLUMN_DEFINITIONS: TableProps.ColumnDefinition<EmailTemplate>[] = [
    {
        id: "title",
        header: "Title",
        cell: (template) => template.title,
    },
    {
        id: "name",
        header: "Name",
        cell: (template) => template.name,
    },
    {
        id: "type",
        header: "Template Type",
        cell: (template) => template.template_type,
    },
    {
        id: "updated_on",
        header: "Updated On",
        cell: (template) => new Date(template.updated_on!).toLocaleString(),
    },
];

class EmailTemplates extends Component<EmailTemplatesProps, EmailTemplatesState> {
    listing: RefObject<IdeaListView>;
    createForm: RefObject<IdeaForm>;

    constructor(props: EmailTemplatesProps) {
        super(props);
        this.listing = React.createRef();
        this.createForm = React.createRef();
        this.state = {
            emailTemplateSelected: false,
            createModalType: "",
            showCreateForm: false,
        };
    }

    emailTemplates(): EmailTemplatesClient {
        return AppContext.get().client().emailTemplates();
    }

    isSelected(): boolean {
        return this.state.emailTemplateSelected;
    }

    getSelected(): EmailTemplate | null {
        if (this.getListing() == null) {
            return null;
        }
        return this.getListing().getSelectedItem();
    }

    getListing(): IdeaListView {
        return this.listing.current!;
    }

    getCreateForm(): IdeaForm {
        return this.createForm.current!;
    }

    clusterSettings(): ClusterSettingsService {
        return AppContext.get().getClusterSettingsService();
    }

    showCreateForm(type: string) {
        this.setState(
            {
                showCreateForm: true,
                createModalType: type,
            },
            () => {
                this.getCreateForm().showModal();
            }
        );
    }

    hideCreateForm() {
        this.setState({
            showCreateForm: false,
            createModalType: "",
        });
    }

    buildCreateEmailTemplateForm() {
        let values = undefined;
        const isUpdate = this.state.createModalType === "update";

        if (isUpdate) {
            const selected = this.getSelected();
            if (selected != null) {
                values = {
                    ...selected,
                };
            }
        }
        return (
            this.state.showCreateForm && (
                <IdeaForm
                    ref={this.createForm}
                    name="create-update-email-template"
                    modal={true}
                    modalSize="medium"
                    title={isUpdate ? "Update Email Template" : "Create new Email Template"}
                    values={values}
                    onSubmit={() => {
                        if (!this.getCreateForm().validate()) {
                            return;
                        }
                        const values = this.getCreateForm().getValues();
                        let createOrUpdate;
                        if (isUpdate) {
                            createOrUpdate = (request: any) => this.emailTemplates().updateEmailTemplate(request);
                            values.name = this.getSelected()?.name;
                        } else {
                            createOrUpdate = (request: any) => this.emailTemplates().createEmailTemplate(request);
                        }
                        createOrUpdate({
                            template: values,
                        })
                            .then(() => {
                                this.setState(
                                    {
                                        emailTemplateSelected: false,
                                    },
                                    () => {
                                        this.hideCreateForm();
                                        this.getListing().fetchRecords();
                                    }
                                );
                            })
                            .catch((error) => {
                                this.getCreateForm().setError(error.errorCode, error.message);
                            });
                    }}
                    onCancel={() => {
                        this.hideCreateForm();
                    }}
                    params={[
                        {
                            name: "title",
                            title: "Title",
                            description: "Enter a user friendly email template title",
                            data_type: "str",
                            param_type: "text",
                            validate: {
                                required: true,
                            },
                        },
                        {
                            name: "name",
                            title: "Template Name",
                            description: "Enter name for the email template",
                            help_text: "Name can only use lowercase alphabets, numbers, hyphens (-), underscores, and periods. Must be between 3 and 32 characters long.",
                            data_type: "str",
                            param_type: "text",
                            readonly: isUpdate,
                            validate: {
                                required: true,
                                regex: "^([a-z0-9-._]+){3,32}$",
                                message: "Only use lowercase alphabets, numbers, hyphens (-), underscores, and periods. Must be between 3 and 32 characters long.",
                            },
                        },
                        {
                            name: "template_type",
                            title: "Type",
                            description: "Select a template type",
                            data_type: "str",
                            param_type: "select",
                            choices: [
                                {
                                    title: "Jinja2",
                                    value: "jinja2",
                                },
                            ],
                            default: "jinja2",
                            validate: {
                                required: true,
                            },
                        },
                        {
                            name: "subject",
                            title: "Email Subject",
                            description: "Enter the email subject",
                            data_type: "str",
                            param_type: "text",
                            validate: {
                                required: true,
                            },
                        },
                        {
                            name: "body",
                            title: "Email Body",
                            description: "Enter email template body",
                            data_type: "str",
                            param_type: "text",
                            multiline: true,
                            validate: {
                                required: true,
                            },
                        },
                    ]}
                />
            )
        );
    }

    buildListing() {
        return (
            <IdeaListView
                ref={this.listing}
                title="Email Templates"
                description="Email Templates Management"
                selectionType="single"
                preferencesKey={"email-templates"}
                showPreferences={false}
                primaryAction={{
                    id: "create-email-template",
                    text: "Create Email Template",
                    onClick: () => {
                        this.showCreateForm("create");
                    },
                }}
                secondaryActionsDisabled={!this.isSelected()}
                secondaryActions={[
                    {
                        id: "edit-license-resource",
                        text: "Edit Email Template",
                        onClick: () => {
                            this.showCreateForm("update");
                        },
                    },
                ]}
                showPaginator={true}
                showFilters={true}
                filters={[
                    {
                        key: "name",
                    },
                ]}
                onFilter={(filters) => {
                    const emailTemplateNameToken = Utils.asString(filters[0].value).trim().toLowerCase();
                    if (Utils.isEmpty(emailTemplateNameToken)) {
                        return [];
                    } else {
                        return [
                            {
                                key: "name",
                                like: emailTemplateNameToken,
                            },
                        ];
                    }
                }}
                onRefresh={() => {
                    this.setState(
                        {
                            emailTemplateSelected: false,
                        },
                        () => {
                            this.getListing().fetchRecords();
                        }
                    );
                }}
                onSelectionChange={() => {
                    this.setState(
                        {
                            emailTemplateSelected: true,
                        },
                        () => {}
                    );
                }}
                onFetchRecords={() => {
                    return this.emailTemplates().listEmailTemplates({
                        filters: this.getListing().getFilters(),
                        paginator: this.getListing().getPaginator(),
                        date_range: this.getListing().getDateRange(),
                    });
                }}
                columnDefinitions={EMAIL_TEMPLATES_TABLE_COLUMN_DEFINITIONS}
            />
        );
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
                        text: "Cluster Management",
                        href: "#/cluster/status",
                    },
                    {
                        text: "Email Templates",
                        href: "",
                    },
                ]}
                content={
                    <div>
                        {this.buildCreateEmailTemplateForm()}
                        {this.buildListing()}
                    </div>
                }
            />
        );
    }
}

export default withRouter(EmailTemplates);
