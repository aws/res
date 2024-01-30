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

import { AppContext } from "../../common";
import IdeaForm from "../../components/form";
import IdeaListView from "../../components/list-view";
import { ApplySnapshot } from "../../client/data-model";
import SnapshotsClient from "../../client/snapshots-client";
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import { IdeaAppLayoutProps } from "../../components/app-layout";
import { withRouter } from "../../navigation/navigation-utils";
import { StatusIndicator } from "@cloudscape-design/components";
import { TableProps } from "@cloudscape-design/components/table/interfaces";

export interface ApplySnapshotsProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {}

export const APPLY_SNAPSHOT_TABLE_COLUMN_DEFINITIONS: TableProps.ColumnDefinition<ApplySnapshot>[] = [
    {
        id: "s3_bucket_name",
        header: "S3 Bucket Name",
        cell: (e) => e.s3_bucket_name,
    },
    {
        id: "snapshot_path",
        header: "Snapshot Path",
        cell: (e) => e.snapshot_path,
    },
    {
        id: "status",
        header: "Status",
        cell: (e) => {
            switch (e.status) {
                case "COMPLETED":
                    return (
                        <StatusIndicator type="success" aria-label="Completed">
                            {e.status}
                        </StatusIndicator>
                    );
                case "FAILED":
                case "ROLLBACK_IN_PROGRESS":
                case "ROLLBACK_COMPLETE":
                case "ROLLBACK_FAILED":
                    return (
                        <StatusIndicator type="error" aria-label="Failed">
                            {e.status}
                        </StatusIndicator>
                    );
                default:
                    return (
                        <StatusIndicator type="in-progress" aria-label="In Progress">
                            {e.status}
                        </StatusIndicator>
                    );
            }
        },
    },
    {
        id: "created_on",
        header: "Created On",
        cell: (e) => new Date(e.created_on!).toLocaleString(),
    }
];


class ApplySnapshots extends Component<ApplySnapshotsProps> {
    applySnapshotForm: RefObject<IdeaForm>;
    listing: RefObject<IdeaListView>;

    constructor(props: ApplySnapshotsProps) {
        super(props);
        this.applySnapshotForm = React.createRef();
        this.listing = React.createRef();
    }

    snapshotsClient(): SnapshotsClient {
        return AppContext.get().client().snapshots();
    }

    getApplySnapshotForm(): IdeaForm {
        return this.applySnapshotForm.current!;
    }

    getListing(): IdeaListView {
        return this.listing.current!;
    }

    buildApplySnapshotForm() {
        return (
            <IdeaForm
                ref={this.applySnapshotForm}
                name="apply-snapshot"
                modal={true}
                title="Apply a Snapshot"
                onSubmit={() => {
                    if (!this.getApplySnapshotForm().validate()) {
                        return;
                    }
                    const values = this.getApplySnapshotForm().getValues();

                    this.snapshotsClient()
                        .applySnapshot({
                            snapshot: {
                                s3_bucket_name: values.s3_bucket_name,
                                snapshot_path: values.snapshot_path,
                            },
                        })
                        .then((_) => {
                            this.props.onFlashbarChange({
                                items: [
                                    {
                                        type: "success",
                                        content: "Apply Snapshot initiated. It takes about 5 minutes for the process to complete. Please refresh this page after some time to check the status.",
                                        dismissible: true,
                                    },
                                ],
                            });
                            this.getListing().fetchRecords();
                            this.getApplySnapshotForm().hideModal();
                        })
                        .catch((error) => {
                            this.props.onFlashbarChange({
                                items: [
                                    {
                                        type: "error",
                                        content: `Failed to apply Snapshot: ${error.message}`,
                                        dismissible: true,
                                    },
                                ],
                            });
                            this.getListing().fetchRecords();
                            this.getApplySnapshotForm().hideModal();
                        });
                }}
                onCancel={() => {
                    this.getApplySnapshotForm().hideModal();
                }}
                params={[
                    {
                        name: "s3_bucket_name",
                        title: "S3 Bucket Name",
                        description: "Enter the name of the S3 bucket where the snapshot to be applied is stored.",
                        help_text: "S3 bucket name can only contain lowercase alphabets, numbers, dots (.), and hyphens (-).",
                        data_type: "str",
                        param_type: "text",
                        validate: {
                            required: true,
                            regex: "^[a-z0-9]+[\\.\\-\\w]*[a-z0-9]+$",
                            message: "S3 bucket name can only contain lowercase alphabets, numbers, dots (.), and hyphens (-).",
                        },
                    },
                    {
                        name: "snapshot_path",
                        title: "Snapshot Path",
                        description: "Enter the path at which the snapshot to be applied is stored in the provided S3 bucket.",
                        help_text: "Snapshot path can only contain forward slashes, dots (.), exclamations (!), asterisks (*), single quotes ('), parentheses (), and hyphens (-).",
                        data_type: "str",
                        param_type: "text",
                        validate: {
                            required: true,
                            regex: "^([\\w\\.\\-\\!\\*\\'\\(\\)]+[\\/]*)+$",
                            message: "Snapshot path can only contain forward slashes, dots (.), exclamations (!), asterisks (*), single quotes ('), parentheses (), and hyphens (-).",
                        },
                    },
                ]}
            />
        );
    }

    buildListing() {
        return (
            <IdeaListView
                ref={this.listing}
                preferencesKey={"apply-snapshots"}
                showPreferences={false}
                title="Applied Snapshots"
                variant="container"
                description="Snapshots applied to the environment"
                primaryAction={{
                    id: "apply-snapshot",
                    text: "Apply Snapshot",
                    onClick: () => {
                        this.getApplySnapshotForm().showModal();
                    },
                }}
                showPaginator={true}
                showFilters={true}
                filters={[
                    {
                        key: "s3_bucket_name",
                    },
                ]}
                onFilter={(filters) => {
                    const s3BucketToken = String(filters[0].value).toString().trim().toLowerCase();
                    if (s3BucketToken == null) {
                        return [];
                    } else {
                        return [
                            {
                                key: "s3_bucket_name",
                                like: s3BucketToken,
                            },
                        ];
                    }
                }}
                onRefresh={() => {
                    this.setState(
                        {},
                        () => {
                            this.getListing().fetchRecords();
                        }
                    );
                }}
                onFetchRecords={async () => {
                    let result = await this.snapshotsClient().listAppliedSnapshots({
                        filters: this.getListing().getFilters(),
                        paginator: this.getListing().getPaginator(),
                    });
                    result.listing?.sort((a,b) =>  new Date(b.created_on!).getTime() - new Date(a.created_on!).getTime())
                    return result
                }}
                columnDefinitions={APPLY_SNAPSHOT_TABLE_COLUMN_DEFINITIONS}
            />
        );
    }

    render() {
        return (
            <React.Fragment>
                {this.buildApplySnapshotForm()}
                {this.buildListing()}
            </React.Fragment>
        );
    }
}

export default withRouter(ApplySnapshots);