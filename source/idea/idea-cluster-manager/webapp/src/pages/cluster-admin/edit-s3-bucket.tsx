import React, { Component, RefObject } from "react";
import IdeaAppLayout, { IdeaAppLayoutProps } from "../../components/app-layout";
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import { Alert, Box, Button, Header, Link, Modal, SpaceBetween } from "@cloudscape-design/components";
import IdeaForm from "../../components/form";
import { withRouter } from "../../navigation/navigation-utils";
import { AppContext } from "../../common";
import { S3Bucket, Project, SocaUserInputChoice, SocaUserInputParamMetadata, UpdateFileSystemRequest } from "../../client/data-model";
import { ProjectsClient, FileSystemClient } from "../../client";

export interface EditS3BucketState {
  showAlertModal: boolean,
  s3Bucket?: S3Bucket,
  removeProjectNames: string[]
}
export interface EditS3BucketProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {}

class EditS3Bucket extends Component<EditS3BucketProps, EditS3BucketState> {
    editS3BucketForm: RefObject<IdeaForm>;

    constructor(props: EditS3BucketProps) {
        super(props);
        this.editS3BucketForm = React.createRef();
        const { state } = this.props.location;
        this.state = {
          showAlertModal: false,
          s3Bucket: state ? state?.s3Bucket : null,
          removeProjectNames: [],
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

    getEditS3BucketForm(): IdeaForm {
      return this.editS3BucketForm.current!;
    }

    buildBucketSetupBasicSettings(container_group_name: string): SocaUserInputParamMetadata[] {
      return [{
        name: "title",
        title: "Bucket display name",
        description: "Type a user friendly name to display.",
        data_type: "str",
        param_type: "text",
        default: this.state.s3Bucket?.storage?.title,
        validate: {
          required: true,
          regex: "^[a-zA-Z0-9\\s_-]{3,48}$",
          message: "Only use valid alphanumeric, hyphens (-), underscores (_), and spaces ( ) characters for the file system title. Must be between 3 and 48 characters long.",
        },
        container_group_name: container_group_name,
        readonly: !this.isAdmin() || this.state.s3Bucket === null,
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
        default: this.state.s3Bucket?.storage?.projects,
        dynamic_choices: true,
        container_group_name: container_group_name,
        readonly: !this.isAdmin() || this.state.s3Bucket === null,
      }]
    }

    buildEditS3BucketForm() {
        return (
            <IdeaForm
                name="edit-s3-bucket"
                ref={this.editS3BucketForm}
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
                  ...this.buildProjectAssociationSettings("project_association"),
                ]}
            />
        )
    }

    canSubmit(): boolean {
      return this.isAdmin() && this.editS3BucketForm.current!.validate() && this.state.s3Bucket !== null;
    }

    isProjectRemoval(): boolean {
      return Array.isArray(this.state.s3Bucket!.storage.projects) && this.state.s3Bucket!.storage.projects?.length !== 0 && this.state.s3Bucket!.storage.projects!.filter(x => !this.editS3BucketForm.current!.getValues().associate_projects.includes(x)).length > 0;
    }

    submitForm() {
      if (!this.canSubmit()) {
        this.getEditS3BucketForm().setError("GENERAL_ERROR", "Request cannot be submitted.");
        return;
      }
      const values = this.editS3BucketForm.current!.getValues();
      const editS3BucketRequest: UpdateFileSystemRequest = {
        filesystem_name: this.state.s3Bucket!.name,
        filesystem_title: values.title,
        projects: values.associate_projects,
      }
      this.filesystems().updateFileSystem(editS3BucketRequest).then(() => {
        this.props.navigate("/cluster/s3-bucket", { state: { flashbarItems: [
          {
            type: "success",
            content: `${values.title} updated successfully.`,
            dismissible: true,
          },
        ]}});
      }).catch((error) => {
        this.getEditS3BucketForm().setError(error.errorCode, error.message);
      })
    }

    buildAlertModal(): JSX.Element {
      return (
        <Modal
            visible={this.state.showAlertModal}
            size="medium"
            onDismiss={() => this.hideAlertModal()}
            header={<Header variant="h3">Save bucket setup</Header>}
            footer={
              <Box float="right">
                <SpaceBetween size="m" direction="horizontal">
                  <Button variant="normal" onClick={() => {
                    this.editS3BucketForm.current!.reset();
                    this.hideAlertModal();
                  }}>Cancel</Button>
                  <Button variant="primary" onClick={() => {
                    this.hideAlertModal();
                    this.submitForm();
                  }}>Save</Button>
                </SpaceBetween>
              </Box>
            }
        >
          <Alert>
            <SpaceBetween direction="vertical" size="xxxs">
              <Box variant="p">
                Proceeding with this action will not impact the data
                in the S3 bucket, but will result in desktop users losing
                access to that data in the following projects:
              </Box>
              {this.state.removeProjectNames.sort().map((projectName, index) => { 
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
          </Alert>
        </Modal>
      )
    }

    buildMainContent(): JSX.Element {
      return (
        <SpaceBetween size="m">
          {this.buildEditS3BucketForm()}
          <SpaceBetween size="m" direction="vertical" alignItems="end">
            <SpaceBetween size="m" direction="horizontal">
                <Button variant="normal" onClick={() => this.props.navigate("/cluster/s3-bucket")}>Cancel</Button>
                <Button variant="primary" onClick={() => {
                  if (!this.canSubmit()) {
                    this.getEditS3BucketForm().setError("GENERAL_ERROR", "Request cannot be submitted.");
                  }else if(this.isProjectRemoval()){
                    this.setState({ removeProjectNames: this.state.s3Bucket!.storage.projects!.filter(x => !this.editS3BucketForm.current!.getValues().associate_projects.includes(x)) });
                    this.showAlertModal();
                  }else{
                    this.submitForm();
                  }
                }}>Save bucket setup</Button>
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
                    text: "Edit bucket",
                    href: "",
                },
                ]}
                header={
                    <Header
                      variant={"h1"}
                    >
                      Edit {this.state.s3Bucket ? this.state.s3Bucket?.storage?.title : "bucket"}
                    </Header>
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

export default withRouter(EditS3Bucket);
