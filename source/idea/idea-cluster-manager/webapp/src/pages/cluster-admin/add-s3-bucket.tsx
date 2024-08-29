import React, { Component, RefObject } from "react";
import IdeaAppLayout, { IdeaAppLayoutProps } from "../../components/app-layout";
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import { Alert, Box, Button, Header, Link, Modal, SpaceBetween } from "@cloudscape-design/components";
import IdeaForm from "../../components/form";
import { withRouter } from "../../navigation/navigation-utils";
import { AppContext } from "../../common";
import { Constants } from "../../common/constants";
import { Project, SocaUserInputChoice, SocaUserInputParamMetadata, OnboardS3BucketRequest } from "../../client/data-model";
import { ProjectsClient, FileSystemClient } from "../../client";

export interface AddS3BucketState {
  showAlertModal: boolean;
}

export interface AddS3BucketProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {}

class AddS3Bucket extends Component<AddS3BucketProps, AddS3BucketState> {
    addS3BucketForm: RefObject<IdeaForm>;

    constructor(props: AddS3BucketProps) {
        super(props);
        this.addS3BucketForm = React.createRef()
        this.state = {
          showAlertModal: false,
      };
    }

    isAdmin(): boolean {
      return AppContext.get().auth().isAdmin();
    }

    projects(): ProjectsClient {
        return AppContext.get().client().projects()
    }

    filesystems(): FileSystemClient {
      return AppContext.get().client().filesystem()
    }

    showAlertModal() {
      this.setState({ showAlertModal: true });
    }

    hideAlertModal() {
      this.setState({ showAlertModal: false });
    }

    getAddS3BucketForm(): IdeaForm {
      return this.addS3BucketForm.current!;
    }

    buildBucketSetupBasicSettings(container_group_name: string): SocaUserInputParamMetadata[] {
      return [{
        name: "title",
        title: "Bucket display name",
        description: "Type a user friendly name to display.",
        data_type: "str",
        param_type: "text",
        validate: {
          required: true,
          regex: "^[a-zA-Z0-9\\s_-]{3,48}$",
          message: "Only use valid alphanumeric, hyphens (-), underscores (_), and spaces ( ) characters for the bucket display title. Must be between 3 and 48 characters long.",
        },
        container_group_name: container_group_name,
        readonly: !this.isAdmin(),
      },
      {
        name: "bucket_arn",
        title: "Bucket ARN",
        description: "Paste the copied Amazon Resource Name (ARN) from AWS S3 even across different accounts. Make sure to update the IAM role ARN under advanced settings for cross account buckets or mounting will fail.",
        data_type: "str",
        param_type: "text",
        validate: {
          required: true,
          regex: "^(?:arn:(?:aws(?:-cn|-us-gov)?)):s3:::([a-z0-9][a-z0-9-.]{1,61}[a-z0-9])(?:/[a-z0-9-.]+)*/?$",
          message: "The ARN is not valid.",
        },
        container_group_name: container_group_name,
        readonly: !this.isAdmin(),
      },
      {
        name: "mount_point",
        title: "Mount point",
        description: "Type the directory path where the bucket will be mounted.",
        data_type: "str",
        param_type: "text",
        validate: {
          required: true,
          regex: "^/[a-z0-9-]{3,18}$",
          message: "Only use lowercase alphabets, numbers, and hyphens (-) for mount directory. Must start with / and be between 3 and 18 characters long.",
        },
        container_group_name: container_group_name,
        readonly: !this.isAdmin(),
      },
      {
        name: "mode",
        title: "Mode",
        data_type: "str",
        param_type: "radio-group",
        default: Constants.SHARED_STORAGE_MODE_READ_ONLY,
        validate: {
          required: true,
        },
        choices: [
          {
            title: "Read only (R)",
            value: Constants.SHARED_STORAGE_MODE_READ_ONLY,
            description: "Allow user only to read or copy stored data."
          },
          {
            title: "Read and write (R/W)",
            value: Constants.SHARED_STORAGE_MODE_READ_WRITE,
            description: "Allow users to read or copy stored data and write or edit."
          }
        ],
        container_group_name: container_group_name,
        readonly: !this.isAdmin(),
      },
      {
        name: "custom_prefix",
        title: "Custom prefix",
        description: "Enable the system to create a prefix automatically.",
        data_type: "str",
        param_type: "select",
        default: Constants.SHARED_STORAGE_NO_CUSTOM_PREFIX,
        multiple: false,
        validate: {
          required: true,
        },
        when: {
          param: "mode",
          eq: Constants.SHARED_STORAGE_MODE_READ_WRITE,
        },
        container_group_name: container_group_name,
        choices: [
          {
            title: "No custom prefix",
            value: Constants.SHARED_STORAGE_NO_CUSTOM_PREFIX,
            description: "Will not create a dedicated directory.",
          },
          {
            title: "/%p",
            value: Constants.SHARED_STORAGE_CUSTOM_PROJECT_NAME_PREFIX,
            description: "Create a dedicated directory by project.",
          },
          {
            title: "/%p/%u",
            value: Constants.SHARED_STORAGE_CUSTOM_PROJECT_NAME_AND_USERNAME_PREFIX,
            description: "Create a dedicated directory by project name and user name.",
          }
        ],
        readonly: !this.isAdmin(),
      }]
    }

    buildBucketSetupAdvancedSettings(container_group_name: string): SocaUserInputParamMetadata[] {
      return [{
          name: "advanced_settings",
          title: "Advanced settings",
          optional: true,
          data_type: "bool",
          param_type: "expandable",
          default: false,
          container_group_name: container_group_name,
          readonly: !this.isAdmin(),
        },
        {
        name: "iam_role",
        title: "IAM role ARN",
        description: "To access the bucket, paste the IAM role Amazon Resource Name (ARN) copied in Identity and Access Management (IAM).",
        data_type: "str",
        param_type: "text",
        validate: {
          regex: "^(?:arn:(?:aws(?:-cn|-us-gov)?)):iam::\\d{12}:role/[/a-zA-Z0-9+=,.@_-]{0,511}[a-zA-Z0-9+=,.@_-]{1,64}$|^$",
          message: "The ARN is not valid.",
        },
        when: {
          param: "advanced_settings",
          eq: true,
        },
        container_group_name: container_group_name,
        readonly: !this.isAdmin(),
      }]
    }

    buildProjectAssociationSettings(container_group_name: string): SocaUserInputParamMetadata[] {
      return [{
        name: "associate_projects",
        title: "Projects",
        optional: true,
        description: (
          <Box variant="small" color="inherit">
            Associate the bucket with the following projects. You can create new projects on the <Link variant="info" href="#/cluster/projects">Projects page</Link>.
            <br/>Note that buckets will not automatically mount to already provisioned VDI sessions. Associate a bucket with a project prior to launching VDIs in that project.
          </Box>
        ),
        param_type: "select",
        multiple: true,
        data_type: "str",
        dynamic_choices: true,
        container_group_name: container_group_name,
        readonly: !this.isAdmin(),
      }]
    }

    buildAddS3BucketForm() {
        return (
            <IdeaForm
                name="add-s3-bucket"
                ref={this.addS3BucketForm}
                modal={false}
                showHeader={false}
                showActions={false}
                useContainers={true}
                onFetchOptions={async (request) => {
                  if (request.param === "associate_projects") {
                    if (!this.isAdmin()) {
                      return Promise.resolve({ listing: [] });
                    }
                    return this.projects().listProjects({}).then((result) => {
                      const projects = result.listing
                      if (!projects || projects?.length === 0) {
                        return {
                            listing: [],
                        }
                      }else{
                        const choices: SocaUserInputChoice[] = []
                        projects.forEach((project) => {
                            choices.push({
                                title: project.title,
                                description: project.name,
                                value: project.name,
                            })
                        })
                        choices.sort((a: Project, b: Project) => a.title!.localeCompare(b.title!))
                        return {
                            listing: choices
                        }
                      }
                    })
                  }else{
                    return Promise.resolve({
                        listing: [],
                    });
                  }
                }}
                containerGroups={[
                  {
                    title: "Bucket setup",
                    name: "bucket_setup",
                  },
                  {
                    title: "Project association",
                    name: "project_association",
                  },
                ]}
                params={[
                  ...this.buildBucketSetupBasicSettings("bucket_setup"),
                  ...this.buildBucketSetupAdvancedSettings("bucket_setup"),
                  ...this.buildProjectAssociationSettings("project_association"),
                ]}
            />
        )
    }

    canSubmit(): boolean {
      return this.isAdmin() && this.addS3BucketForm.current!.validate();
    }

    isNoCustomPrefix(): boolean {
      return this.addS3BucketForm.current!.getValues().custom_prefix === Constants.SHARED_STORAGE_NO_CUSTOM_PREFIX;
    }

    submitForm() {
      const values = this.addS3BucketForm.current!.getValues();
      const addS3BucketRequest: OnboardS3BucketRequest = {
          object_storage_title: values.title,
          bucket_arn: values.bucket_arn,
          mount_directory: values.mount_point,
          read_only: values.mode === Constants.SHARED_STORAGE_MODE_READ_ONLY,
          custom_bucket_prefix: values.custom_prefix,
          iam_role_arn: values.iam_role,
          projects: values.associate_projects
      }
      this.filesystems().onboardS3Bucket(addS3BucketRequest).then(() => {
        this.props.navigate("/cluster/s3-bucket", { state: { flashbarItems: [
          {
            type: "success",
            content: `${values.title} added successfully.`,
            dismissible: true,
          },
        ]}});
      }).catch((error) => {
        this.getAddS3BucketForm().setError(error.errorCode, error.message);
      })
    }

    buildAlertModal(): JSX.Element {
      return (
        <Modal
            visible={this.state.showAlertModal}
            size="medium"
            onDismiss={() => this.hideAlertModal()}
            header={<Header variant="h3">Warning: No Custom Prefix Selected</Header>}
            footer={
              <Box float="right">
                <SpaceBetween size="m" direction="horizontal">
                  <Button variant="normal" onClick={() => this.hideAlertModal()}>Cancel</Button>
                  <Button variant="primary" onClick={() => {
                    this.hideAlertModal();
                    this.submitForm();
                  }}>Confirm</Button>
                </SpaceBetween>
              </Box>
            }
        >
          <Alert type="warning">
            Without specifying a project name %p or user %u, the data in this bucket could be accessible to users in other projects.
          </Alert>
        </Modal>
      )
    }

    buildMainContent(): JSX.Element {
      return (
        <SpaceBetween size="m">
          {this.buildAddS3BucketForm()}
          <SpaceBetween size="m" direction="vertical" alignItems="end">
            <SpaceBetween size="m" direction="horizontal">
                <Button variant="normal" onClick={() => this.props.navigate("/cluster/s3-bucket")}>Cancel</Button>
                <Button variant="primary" onClick={() => {
                  if (!this.canSubmit()) {
                    this.getAddS3BucketForm().setError("GENERAL_ERROR", "Request cannot be submitted.");
                  }else if(this.isNoCustomPrefix()){
                    this.showAlertModal();
                  }else{
                    this.submitForm();
                  }
                }}>Add bucket</Button>
            </SpaceBetween>
          </SpaceBetween>
        </SpaceBetween>
      )
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
                      href: "#/cluster/s3-bucket",
                  },
                  {
                    text: "Add bucket",
                    href: "",
                },
                ]}
                header={
                  <SpaceBetween size="m" direction="vertical">
                    <Header
                      variant={"h1"}
                    >
                      Add bucket
                    </Header>
                    <Alert>
                      Currently only available for Linux desktops. Mounting S3 buckets on Windows desktops is not supported.
                    </Alert>
                  </SpaceBetween>
                }
                contentType={"default"}
                content={
                    <>
                      {this.buildAlertModal()}
                      {this.buildMainContent()}
                    </>
                }
            />
        );
    }
}

export default withRouter(AddS3Bucket);
