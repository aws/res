import IdeaAppLayout, { IdeaAppLayoutProps } from "../../components/app-layout";
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import { TableProps } from "@cloudscape-design/components/table/interfaces";
import React, { Component, RefObject } from "react";
import { withRouter } from "../../navigation/navigation-utils";
import IdeaListView from "../../components/list-view";
import { AppContext } from "../../common";
import ProjectsClient from "../../client/projects-client";
import FileSystemClient from "../../client/filesystem-client";
import { Constants } from "../../common/constants";
import { S3Bucket, RemoveFileSystemRequest, SocaListingPayload } from "../../client/data-model";
import { Box, Button, SpaceBetween, Link, FlashbarProps } from "@cloudscape-design/components";

export interface S3BucketProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {}

export interface S3BucketState {
    s3BucketSelected: boolean;
    selectedS3Bucket: S3Bucket[];
    flashbarItems?: FlashbarProps.MessageDefinition[]
}

class S3Buckets extends Component<S3BucketProps, S3BucketState> {
    listing: RefObject<IdeaListView>;
    constructor(props: S3BucketProps) {
        super(props);
        this.listing = React.createRef();
        const { state } = this.props.location
        this.state = {
            s3BucketSelected: false,
            selectedS3Bucket: [],
        };
        if (Array.isArray(state?.flashbarItems) && state?.flashbarItems?.length !== 0) {
            this.props.onFlashbarChange({ items: state.flashbarItems });
        }
    }

    fileSystemClient(): FileSystemClient {
        return AppContext.get().client().filesystem();
    }

    projectsClient(): ProjectsClient {
        return AppContext.get().client().projects();
    }

    getListing(): IdeaListView {
        return this.listing.current!;
    }

    isSelected(): boolean {
        return this.state.s3BucketSelected;
    }

    getSelectedS3Bucket = () => {
        if (this.state.selectedS3Bucket.length === 0) {
            return null
        }
        return this.state.selectedS3Bucket[0]
    }

    getS3BucketsTableColumnsDefinitions(): TableProps.ColumnDefinition<S3Bucket>[] {
        return [
            {
                id: "title",
                header: "Bucket name",
                cell: (e) => e.storage.title,
            },
            {
                id: "s3_bucket_arn",
                header: "Bucket ARN",
                cell: (e) => e.storage.s3_bucket.bucket_arn,
            },
            {
                id: "mount_dir",
                header: "Mount point",
                cell: (e) => e.storage.mount_dir,
            },
            {
                id: "read_only",
                header: "Mode",
                cell: (e) => (e.storage.s3_bucket.read_only ? Constants.SHARED_STORAGE_MODE_READ_ONLY : Constants.SHARED_STORAGE_MODE_READ_WRITE),
            },
            {
                id: "custom_bucket_prefix",
                header: "Custom prefix",
                cell: (e) => {
                    switch (e.storage.s3_bucket.custom_bucket_prefix) {
                        case Constants.SHARED_STORAGE_CUSTOM_PROJECT_NAME_PREFIX:
                            return "/%p";
                        case Constants.SHARED_STORAGE_CUSTOM_PROJECT_NAME_AND_USERNAME_PREFIX:
                            return "/%p/%u";
                        default:
                            return "-";
                    }
                },
            },
            {
                id: "projects",
                header: "Project codes",
                cell: (e) => {
                    if (e.storage.projects && e.storage.projects.length !== 0) {
                        return (
                            <SpaceBetween direction="vertical" size="xxs">
                                {e.storage.projects.sort().map((projectName, index) => { 
                                    return <Link key={index}
                                        onFollow={async () => {
                                                this.props.navigate("/cluster/projects", { state: { defaultFilteringText: projectName }});
                                            }
                                        }
                                    >
                                    {projectName}
                                  </Link>
                                })}
                            </SpaceBetween>
                        );
                    } else {
                        return "-";
                    }
                },
            }
        ];
    }

    onRefresh = () => {
        this.setState(
            {
                s3BucketSelected: false,
                selectedS3Bucket: [],
            },
            () => {
                this.getListing().fetchRecords();
            }
        );
    }

    setFlashbarMessage(type: "success" | "error", message: string) {
        this.props.onFlashbarChange({
            items: [
                {
                    type: type,
                    content: message,
                    dismissible: true,
                },
            ],
        });
    }

    getS3BucketTableItems = async (): Promise<SocaListingPayload> => {
        const filters = [...this.getListing().getFilters(), { 
            key: "provider", eq: Constants.SHARED_STORAGE_PROVIDER_S3_BUCKET 
        }];
        return this.fileSystemClient().listOnboardedFileSystems({ filters });
    }

    removeFileSystem = async (s3Bucket: S3Bucket) => {
        if(Array.isArray(s3Bucket.storage.projects) && s3Bucket.storage.projects.length !== 0){
            const projectsSingularPluralString = s3Bucket.storage.projects.length === 1 ? 'project is' : 'projects are';
            this.setFlashbarMessage("error", `Your request could not be processed because ${s3Bucket.storage.projects.length} ${projectsSingularPluralString} still associated with the bucket.
            Remove all bucket-project associations and try again.`);
            return;
        }
        const fileSystemTitle = s3Bucket.storage.title
        const removeFileSystemRequest: RemoveFileSystemRequest = {
            filesystem_name: s3Bucket.name
        }
        this.fileSystemClient().removeFileSystem(removeFileSystemRequest).then(() => {
            this.setFlashbarMessage("success", `${fileSystemTitle} removed successfully. The remove operation did not impact the data in the S3 bucket.`);
            this.onRefresh();
        }).catch((error) => {
            this.setFlashbarMessage("error", error.message);
        })
    }

    buildListing() {
        return (
            <IdeaListView
                ref={this.listing}
                title="S3 buckets"
                preferencesKey={"s3-bucket"}
                showPreferences={true}
                description="Onboard and manage S3 buckets for Virtual Desktops."
                selectionType="single"
                primaryAction={{
                    id: "add-bucket",
                    text: "Add bucket",
                    onClick: () => {
                        this.props.navigate("/cluster/s3-bucket/add-bucket")
                    },
                }}
                secondaryActionsDisabled={!this.isSelected()}
                secondaryActions={[
                    {
                        id: "edit-bucket",
                        text: "Edit",
                        onClick: () => {
                            this.props.navigate("/cluster/s3-bucket/edit-bucket", { state: { s3Bucket: this.getSelectedS3Bucket() }})
                        },
                    },
                    {
                        id: "remove-bucket",
                        text: "Remove",
                        onClick: () => {
                            this.removeFileSystem(this.getSelectedS3Bucket()!)
                        },
                    },
                ]}
                showFilters={true}
                filters={[
                    {
                        key: "title",
                    },
                ]}
                filteringPlaceholder="Find bucket by name."
                onFilter={(filters) => {
                    const s3BucketToken = String(filters[0]?.value)?.trim() || '';
                    return s3BucketToken ? [{ key: "title", starts_with: s3BucketToken }] : [];
                }}
                onRefresh={() => {
                    this.onRefresh()
                }}
                selectedItems={this.state.selectedS3Bucket}
                onSelectionChange={(event) => {
                    this.setState({
                        s3BucketSelected: true,
                        selectedS3Bucket: event.detail.selectedItems
                    })
                }}
                onFetchRecords={() => {
                    return this.getS3BucketTableItems();
                }}
                columnDefinitions={this.getS3BucketsTableColumnsDefinitions()}
                empty={
                    <SpaceBetween size="xs">
                        <Box variant="p" textAlign="center" color="inherit">
                            No buckets to display.
                            <br/>To add buckets, you need to create them first in <Link href="https://console.aws.amazon.com/s3" external>AWS S3</Link>
                            <br/>and then add those previously created buckets to the research environment.
                        </Box>
                        <Button onClick={() => {this.props.navigate("/cluster/s3-bucket/add-bucket")}}>Add bucket</Button>
                    </SpaceBetween>
                }
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
                        text: "Environment Management",
                        href: "#/cluster/status",
                    },
                    {
                        text: "S3 buckets",
                        href: "",
                    },
                ]}
                content={
                    <div>
                        {this.buildListing()}
                    </div>
                }
            />
        );
    }
}

export default withRouter(S3Buckets);
