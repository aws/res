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
import { Snapshot } from "../../client/data-model";
import Utils from "../../common/utils";
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import { IdeaAppLayoutProps } from "../../components/app-layout";
import { withRouter } from "../../navigation/navigation-utils";
import SnapshotsClient from "../../client/snapshots-client";
import { StatusIndicator } from "@cloudscape-design/components";
import { TableProps } from "@cloudscape-design/components/table/interfaces";

export interface SnapshotsProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {}

export interface SnapshotsState {
    snapshotSelected: boolean;
}

export const SNAPSHOT_TABLE_COLUMN_DEFINITIONS: TableProps.ColumnDefinition<Snapshot>[] = [
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
    },
];

class Snapshots extends Component<SnapshotsProps, SnapshotsState> {
    createSnapshotForm: RefObject<IdeaForm>;
    listing: RefObject<IdeaListView>;

    constructor(props: SnapshotsProps) {
        super(props);
        this.createSnapshotForm = React.createRef();
        this.listing = React.createRef();
        this.state = {
            snapshotSelected: false,
        };
    }

    snapshotsClient(): SnapshotsClient {
        return AppContext.get().client().snapshots();
    }

    getCreateSnapshotForm(): IdeaForm {
        return this.createSnapshotForm.current!;
    }

    getListing(): IdeaListView {
        return this.listing.current!;
    }

    buildCreateSnapshotForm() {
        return (
            <IdeaForm
                ref={this.createSnapshotForm}
                name="create-snapshot"
                modal={true}
                title="Create New Snapshot"
                onSubmit={() => {
                    if (!this.getCreateSnapshotForm().validate()) {
                        return;
                    }
                    const values = this.getCreateSnapshotForm().getValues();

                    this.snapshotsClient()
                        .createSnapshot({
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
                                        content: "Snapshot creation initiated. It takes 5-10 minutes to create a snapshot. Please refresh this page after that time to check the status of the snapshot.",
                                        dismissible: true,
                                    },
                                ],
                            });
                            this.getListing().fetchRecords();
                            this.getCreateSnapshotForm().hideModal();
                        })
                        .catch((error) => {
                            this.props.onFlashbarChange({
                                items: [
                                    {
                                        type: "error",
                                        content: `Failed to create Snapshot: ${error.message}`,
                                        dismissible: true,
                                    },
                                ],
                            });
                            this.getListing().fetchRecords();
                            this.getCreateSnapshotForm().hideModal();
                        });
                }}
                onCancel={() => {
                    this.getCreateSnapshotForm().hideModal();
                }}
                params={[
                    {
                        name: "s3_bucket_name",
                        title: "S3 Bucket Name",
                        description: "Enter the name of an existing S3 bucket where the snapshot should be stored.",
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
                        description: "Enter a path at which the snapshot should be stored in the provided S3 bucket.",
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

    isSelected(): boolean {
        return this.state.snapshotSelected;
    }

    buildListing() {
        return (
            <IdeaListView
                ref={this.listing}
                preferencesKey={"snapshots"}
                showPreferences={false}
                title="Created Snapshots"
                variant="container"
                description="Snapshots created from the environment"
                primaryAction={{
                    id: "create-snapshot",
                    text: "Create Snapshot",
                    onClick: () => {
                        this.getCreateSnapshotForm().showModal();
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
                    const s3BucketToken = Utils.asString(filters[0].value).trim().toLowerCase();
                    if (Utils.isEmpty(s3BucketToken)) {
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
                        {
                            snapshotSelected: false,
                        },
                        () => {
                            this.getListing().fetchRecords();
                        }
                    );
                }}
                onSelectionChange={() => {
                    this.setState({
                        snapshotSelected: true,
                    });
                }}
                onFetchRecords={async () => {
                    let result = await this.snapshotsClient().listSnapshots({
                        filters: this.getListing().getFilters(),
                        paginator: this.getListing().getPaginator(),
                    });
                    result.listing?.sort((a,b) =>  new Date(b.created_on!).getTime() - new Date(a.created_on!).getTime())
                    return result
                }}
                columnDefinitions={SNAPSHOT_TABLE_COLUMN_DEFINITIONS}
            />
        );
    }

    render() {
        return (
            <React.Fragment>
                {this.buildCreateSnapshotForm()}
                {this.buildListing()}
            </React.Fragment>
        );
    }
}

export default withRouter(Snapshots);
