import IdeaAppLayout, { IdeaAppLayoutProps } from "../../components/app-layout";
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import { TableProps } from "@cloudscape-design/components/table/interfaces";
import { SocaUserInputChoice, SocaFilter, GetParamChoicesRequest, GetParamChoicesResult, CreateONTAPFileSystemRequest, CreateEFSFileSystemRequest, SocaUserInputParamMetadata, FileSystemsNotOnboarded, FSxONTAPFileSystem } from "../../client/data-model";
import React, { Component, RefObject } from "react";
import { withRouter } from "../../navigation/navigation-utils";
import IdeaListView from "../../components/list-view";
import IdeaForm from "../../components/form";
import { AppContext } from "../../common";
import FileSystemClient from "../../client/filesystem-client";
import { ClusterSettingsClient, ProjectsClient } from "../../client";
import Utils from "../../common/utils";
import { SharedStorageFileSystem } from "../../common/shared-storage-utils";
import dot from "dot-object";
import { Constants } from "../../common/constants";
import {IdeaFormFieldStateChangeEvent} from "../../components/form-field";
import IdeaSplitPanel from "../../components/split-panel";
import { ColumnLayout, Container, Header, SpaceBetween } from "@cloudscape-design/components";
import {KeyValue} from "../../components/key-value";

export interface FileSystemProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {}

export interface FileSystemState {
    filesystemSelected: boolean;
    selectedFileSystem: SharedStorageFileSystem[];
    showAddFileSystemToProjectForm: boolean;
    showRemoveFileSystemFromProjectForm: boolean;
    showOnboardFileSystemForm: boolean;
    filesystemsNotOnboarded: FileSystemsNotOnboarded;
    splitPanelOpen: boolean;
}

export const FILESYSTEM_TABLE_COLUMN_DEFINITIONS: TableProps.ColumnDefinition<SharedStorageFileSystem>[] = [
    {
        id: "title",
        header: "Title",
        cell: (filesystem) => filesystem.getTitle(),
    },
    {
        id: "name",
        header: "Name",
        cell: (filesystem) => filesystem.getName(),
    },
    {
        id: "filesystem_id",
        header: "File System ID",
        cell: (filesystem) => filesystem.getFileSystemId(),
    },
    {
        id: "scope",
        header: "Scope",
        cell: (filesystem) => filesystem.getScope(),
    },
    {
        id: "provider",
        header: "Provider",
        cell: (filesystem) => filesystem.getProvider(),
    }
];

class FileSystems extends Component<FileSystemProps, FileSystemState> {
    listing: RefObject<IdeaListView>;
    addFileSystemToProjectForm: RefObject<IdeaForm>;
    removeFileSystemFromProjectForm: RefObject<IdeaForm>;
    onboardFileSystemForm: RefObject<IdeaForm>
    constructor(props: FileSystemProps) {
        super(props);
        this.listing = React.createRef();
        this.addFileSystemToProjectForm = React.createRef();
        this.removeFileSystemFromProjectForm = React.createRef();
        this.onboardFileSystemForm = React.createRef();
        this.state = {
            filesystemSelected: false,
            showAddFileSystemToProjectForm: false,
            showRemoveFileSystemFromProjectForm: false,
            showOnboardFileSystemForm: false,
            filesystemsNotOnboarded: {},
            splitPanelOpen: false,
            selectedFileSystem: []
        };
    }

    getSharedFileSystemTableItems = (): Promise<{ listing: SharedStorageFileSystem[] }> => {
        let promises: Promise<any>[] = [];
        promises.push(this.clusterSettings().getModuleSettings({ module_id: Constants.MODULE_SHARED_STORAGE }));
        return Promise.all(promises).then((result) => {
            const sharedFileSystem = result[0].settings;
            let _result: SharedStorageFileSystem[] = [];
            Object.keys(sharedFileSystem).forEach((key) => {
                const storage = dot.pick(key, sharedFileSystem);
                const provider = dot.pick("provider", storage);
                if (Utils.isEmpty(provider) || provider === Constants.SHARED_STORAGE_PROVIDER_S3_BUCKET) {
                    return true;
                }
                const isInternal = key === "internal";
                if (!isInternal) {
                    _result.push(new SharedStorageFileSystem(key, storage));
                }
            });
            return { listing: _result };
        });
    };

    clusterSettings(): ClusterSettingsClient {
        return AppContext.get().client().clusterSettings();
    }

    filesystem(): FileSystemClient {
        return AppContext.get().client().filesystem();
    }

    projects(): ProjectsClient {
        return AppContext.get().client().projects();
    }

    private listProjectsAsChoices(filters: SocaFilter[]) {
        return this.projects()
            .listProjects({
                filters: filters,
            })
            .then((result) => {
                const listing = result.listing!;
                if (listing.length === 0) {
                    return {
                        listing: [],
                    };
                } else {
                    const choices: any = [];
                    listing.forEach((value) => {
                        choices.push({
                            title: `${value.title} (${value.name})`,
                            value: value.name,
                        });
                    });
                    return {
                        listing: choices,
                    };
                }
            });
    }

    buildAddFileSystemToProjectForm() {
        return (
            <IdeaForm
                ref={this.addFileSystemToProjectForm}
                name="add-filesystem-to-project"
                title="Add File System to Project"
                modal={true}
                onCancel={() => {
                    this.hideAddFileSystemToProjectForm();
                }}
                onSubmit={() => {
                    if (!this.getAddFileSystemToProjectForm().validate()) {
                        return;
                    }
                    const values = this.getAddFileSystemToProjectForm().getValues();
                    const filesystem_name = this.getSelectedFileSystem()?.name!;
                    this.filesystem()
                        .addFileSystemToProject({ filesystem_name: filesystem_name, project_name: values.project_name })
                        .then((_) => {
                            this.props.onFlashbarChange({
                                items: [
                                    {
                                        type: "success",
                                        content: `File System: ${filesystem_name} was successfully added to project: ${values.project_name}`,
                                        dismissible: true,
                                    },
                                ],
                            });
                            this.hideAddFileSystemToProjectForm();
                        })
                        .catch((error) => {
                            this.getAddFileSystemToProjectForm().setError(error.errorCode, error.message);
                        });
                }}
                onFetchOptions={(request: GetParamChoicesRequest): Promise<GetParamChoicesResult> => {
                    if (request.param === "project_name") {
                        return this.listProjectsAsChoices([{}]);
                    } else {
                        return Promise.resolve({
                            listing: [],
                        });
                    }
                }}
                params={[
                    {
                        name: "project_name",
                        title: "Project",
                        description: "Please select a project to add file system to",
                        data_type: "str",
                        param_type: "select",
                        multiple: false,
                        validate: {
                            required: true,
                        },
                    },
                ]}
            />
        );
    }

    getOnboardFileSystemForm(): IdeaForm {
        return this.onboardFileSystemForm.current!;
    }

    showOnboardFileSystemForm() {
        this.setState(
            {
                showOnboardFileSystemForm: true,
            },
            () => {
                this.getOnboardFileSystemForm().showModal();
            }
        );
    }

    hideOnboardFileSystemForm() {
        this.setState({
            showOnboardFileSystemForm: false,
        });
    }

    showAddFileSystemToProjectForm() {
        this.setState(
            {
                showAddFileSystemToProjectForm: true,
            },
            () => {
                this.getAddFileSystemToProjectForm().showModal();
            }
        );
    }

    hideAddFileSystemToProjectForm() {
        this.setState({
            showAddFileSystemToProjectForm: false,
        });
    }

    buildRemoveFileSystemFromProjectForm() {
        return (
            <IdeaForm
                ref={this.removeFileSystemFromProjectForm}
                name="remove-filesystem-from-project"
                title="Remove File System from Project"
                modal={true}
                onCancel={() => {
                    this.hideRemoveFileSystemFromProjectForm();
                }}
                onSubmit={() => {
                    if (!this.getRemoveFileSystemFromProjectForm().validate()) {
                        return;
                    }
                    const values = this.getRemoveFileSystemFromProjectForm().getValues();
                    const filesystem_name = this.getSelectedFileSystem()?.name!;
                    this.filesystem()
                        .removeFileSystemFromProject({ filesystem_name: filesystem_name, project_name: values.project_name })
                        .then((_) => {
                            this.props.onFlashbarChange({
                                items: [
                                    {
                                        type: "success",
                                        content: `File System: ${filesystem_name} was successfully removed from project: ${values.project_name}`,
                                        dismissible: true,
                                    },
                                ],
                            });
                            this.hideRemoveFileSystemFromProjectForm();
                        })
                        .catch((error) => {
                            this.getRemoveFileSystemFromProjectForm().setError(error.errorCode, error.message);
                        });
                }}
                onFetchOptions={(request: GetParamChoicesRequest): Promise<GetParamChoicesResult> => {
                    if (request.param === "project_name") {
                        const projects: string[] = dot.pick("projects", this.getSelectedFileSystem()?.sharedStorage);
                        const listing: SocaUserInputChoice[] = [];
                        projects?.forEach((project) => {
                            listing.push({
                                title: project,
                                value: project,
                            });
                        });
                        return Promise.resolve({
                            listing: listing,
                        });
                    } else {
                        return Promise.resolve({
                            listing: [],
                        });
                    }
                }}
                params={[
                    {
                        name: "project_name",
                        title: "Project",
                        description: "Please select a project to remove file system from",
                        data_type: "str",
                        param_type: "select",
                        multiple: false,
                        validate: {
                            required: true,
                        },
                    },
                ]}
            />
        );
    }

    showRemoveFileSystemFromProjectForm() {
        this.setState(
            {
                showRemoveFileSystemFromProjectForm: true,
            },
            () => {
                this.getRemoveFileSystemFromProjectForm().showModal();
            }
        );
    }

    hideRemoveFileSystemFromProjectForm() {
        this.setState({
            showRemoveFileSystemFromProjectForm: false,
        });
    }

    getAddFileSystemToProjectForm(): IdeaForm {
        return this.addFileSystemToProjectForm.current!;
    }

    getRemoveFileSystemFromProjectForm(): IdeaForm {
        return this.removeFileSystemFromProjectForm.current!;
    }

    getListing(): IdeaListView {
        return this.listing.current!;
    }

    isSelected(): boolean {
        return this.state.filesystemSelected;
    }

    buildCommonOnboardFileSystemParams(): SocaUserInputParamMetadata[] {
        const commonOnboardFileSystemParams: SocaUserInputParamMetadata[] = [
            {
                name: "filesystem.filesystem_title",
                title: "Title",
                description: "Enter a user friendly file system title",
                data_type: "str",
                param_type: "text",
                validate: {
                    required: true,
                    regex: "^[a-zA-Z0-9\\s_-]{3,48}$",
                    message: "Only use valid alphanumeric, hyphens (-), underscores (_), and spaces ( ) characters for the file system title. Must be between 3 and 48 characters long.",
                }
            },
            {
                name: "filesystem.filesystem_name",
                title: "File System Name",
                description: "Enter a file system name",
                help_text: "File System name cannot contain white spaces or special characters. Only use lowercase alphabets, numbers and underscore (_). Must be between 3 and 18 characters long.",
                data_type: "str",
                param_type: "text",
                validate: {
                    required: true,
                    regex: "^[a-z0-9_]{3,18}$",
                    message: "Only use lowercase alphabets, numbers and underscore (_). Must be between 3 and 18 characters long."
                }
            },
        ];
        commonOnboardFileSystemParams.forEach((param) => {
            param.when = {
                param: "onboard_filesystem",
                not_empty: true
            }
        });
        return commonOnboardFileSystemParams;
    }

    buildOnboardEFSParams(): SocaUserInputParamMetadata[]  {
        const efsParams: SocaUserInputParamMetadata[] = [
            {
                name: `${Constants.SHARED_STORAGE_PROVIDER_EFS}.mount_directory`,
                title: "Mount Directory",
                description: "Enter directory to mount the file system",
                help_text: "Mount directory cannot contain white spaces or special characters. Only use lowercase alphabets, numbers, and hyphens (-). Must be between 3 and 18 characters long starting with '/'. Eg. /efs-01",
                data_type: "str",
                param_type: "text",
                validate: {
                    required: true,
                    regex: "^/([a-z0-9-]+){3,18}$",
                    message: "Only use lowercase alphabets, numbers, and hyphens (-). Must be between 3 and 18 characters long starting with '/'."
                }
            }
        ];
        efsParams.forEach((param) => {
            param.when = {
                param: "onboard_filesystem",
                starts_with: Constants.SHARED_STORAGE_PROVIDER_EFS
            }
        })

        return efsParams;
    }

    buildOnboardFSxNetAppONTAPParams(): SocaUserInputParamMetadata[] {
        const fSxNetAppONTAPParams: SocaUserInputParamMetadata[] = [
            {
                name: `${Constants.SHARED_STORAGE_PROVIDER_FSX_NETAPP_ONTAP}.svm_id`,
                title: "Storage Virtual Machine",
                description: "Select an existing SVM to connect to ONTAP file system",
                data_type: "str",
                param_type: "select",
                validate: {
                    required: true,
                },
                dynamic_choices: true,
                when: {
                    param: "onboard_filesystem",
                    starts_with: Constants.SHARED_STORAGE_PROVIDER_FSX_NETAPP_ONTAP
                }
            },
            {
                name: `${Constants.SHARED_STORAGE_PROVIDER_FSX_NETAPP_ONTAP}.volume_id`,
                title: "Existing FSx for NetApp ONTAP Volume",
                description: "Select an existing NetApp ONTAP Volume",
                data_type: "str",
                param_type: "select",
                validate: {
                    required: true,
                },
                dynamic_choices: true,
                when: {
                    param: "onboard_filesystem",
                    starts_with: Constants.SHARED_STORAGE_PROVIDER_FSX_NETAPP_ONTAP
                }
            },
            {
                name: `${Constants.SHARED_STORAGE_PROVIDER_FSX_NETAPP_ONTAP}.mount_directory`,
                title: "Mount Directory",
                description: "Enter directory to mount the file system",
                help_text: "Mount directory cannot contain white spaces or special characters. Only use lowercase alphabets, numbers, and hyphens (-). Must be between 3 and 18 characters long starting with '/'. Eg. /ontap-01",
                data_type: "str",
                param_type: "text",
                validate: {
                    regex: "(^.{0}$)|(^/([a-z0-9-]+){3,18}$)",
                    message: "Only use lowercase alphabets, numbers, and hyphens (-). Must be between 3 and 18 characters long starting with '/'."
                },
                when: {
                    param: "onboard_filesystem",
                    starts_with: Constants.SHARED_STORAGE_PROVIDER_FSX_NETAPP_ONTAP
                }
            },
            {
                name: `${Constants.SHARED_STORAGE_PROVIDER_FSX_NETAPP_ONTAP}.mount_drive`,
                title: "Mount Drive",
                description: "Enter mount drive letter for Windows",
                help_text: "Mount drive cannot be C and cannot contain white spaces or special characters. Only use an uppercase alphabet. Do not include colon (:)",
                data_type: "str",
                param_type: "text",
                validate: {
                    regex: "(^.{0}$)|(^[ABD-Z]{1}$)",
                    message: "Only use an uppercase alphabet"
                },
                when: {
                    param: "onboard_filesystem",
                    starts_with: Constants.SHARED_STORAGE_PROVIDER_FSX_NETAPP_ONTAP
                }
            },
            {
                name: `${Constants.SHARED_STORAGE_PROVIDER_FSX_NETAPP_ONTAP}.file_share_name`,
                title: "Existing FSx for NetApp ONTAP CIFS share name",
                description: "Enter an existing NetApp ONTAP CIFS share name",
                help_text: "Use a valid NetApp ONTAP CIFS share name. Only use an uppercase, lowercase alphabet, numbers, hyphens (-) or underscore (_) Must be between 3 and 18 characters long.",
                data_type: "str",
                param_type: "text",
                validate: {
                    required: true,
                    regex: "^[a-zA-Z0-9-_]{3,18}$",
                    message: "Only use an uppercase, lowercase alphabet, numbers, hyphens (-) or underscore (_) Must be between 3 and 18 characters long."
                },
                when: {
                    param: `${Constants.SHARED_STORAGE_PROVIDER_FSX_NETAPP_ONTAP}.mount_drive`,
                    not_empty: true
                }
            }
        ];

        return fSxNetAppONTAPParams;
    }

    buildOnboardFSxLUSTREParams(): SocaUserInputParamMetadata[]  {
        const fsxLUSTREParams: SocaUserInputParamMetadata[] = [
            {
                name: `${Constants.SHARED_STORAGE_PROVIDER_FSX_LUSTRE}.mount_directory`,
                title: "Mount Directory",
                description: "Enter directory to mount the file system",
                help_text: "Mount directory cannot contain white spaces or special characters. Only use lowercase alphabets, numbers, and hyphens (-). Must be between 3 and 18 characters long starting with '/'. Eg. /lustre-01",
                data_type: "str",
                param_type: "text",
                validate: {
                    required: true,
                    regex: "^/([a-z0-9-]+){3,18}$",
                    message: "Only use lowercase alphabets, numbers, and hyphens (-). Must be between 3 and 18 characters long starting with '/'."
                }
            }
        ];
        fsxLUSTREParams.forEach((param) => {
            param.when = {
                param: "onboard_filesystem",
                starts_with: Constants.SHARED_STORAGE_PROVIDER_FSX_LUSTRE
            }
        })

        return fsxLUSTREParams;
    }

    getSelectedOnboardFileSystem() {
        return this.getOnboardFileSystemForm().getFormField("onboard_filesystem");
    }
    getSelectedSVM() {
        return this.getOnboardFileSystemForm().getFormField(`${Constants.SHARED_STORAGE_PROVIDER_FSX_NETAPP_ONTAP}.svm_id`);
    }
    buildOnboardFileSystemForm(){
        return (<IdeaForm
            ref={this.onboardFileSystemForm}
            name="onboard-filesystem"
            modal={true}
            modalSize="medium"
            title="Onboard New File System"
            onSubmit={() => {
                if(!this.getOnboardFileSystemForm().validate()) {
                    return;
                }
                const values = this.getOnboardFileSystemForm().getValues();
                if (
                    !dot.pick(`${Constants.SHARED_STORAGE_PROVIDER_EFS}.mount_directory`,values) &&
                    !dot.pick(`${Constants.SHARED_STORAGE_PROVIDER_FSX_NETAPP_ONTAP}.mount_directory`,values) &&
                    !dot.pick(`${Constants.SHARED_STORAGE_PROVIDER_FSX_NETAPP_ONTAP}.mount_drive`,values) &&
                    !dot.pick(`${Constants.SHARED_STORAGE_PROVIDER_FSX_LUSTRE}.mount_directory`,values)
                ) {
                    this.getOnboardFileSystemForm().setError('InvalidParams','one of mount directory or mount drive is required')
                    return;
                }

                //Extract filesystemId
                const addFilesystemValue = dot.pick("onboard_filesystem", values);
                const addFilesystemValueSplit = addFilesystemValue.split(".");
                const provider = addFilesystemValueSplit[0];
                const fileSystemId = addFilesystemValueSplit[1];

                //Extract common file system values
                const commonFileSystemValues = dot.pick("filesystem", values);

                //Extract specified provider values
                const providerValues = dot.pick(provider, values);
                let attachFileSystem;
                let volumeId;
                if(provider === Constants.SHARED_STORAGE_PROVIDER_EFS) {
                    attachFileSystem = (request: any) => this.filesystem().onboardEFSFileSystem(request);
                }
                else if (provider === Constants.SHARED_STORAGE_PROVIDER_FSX_LUSTRE) {
                    attachFileSystem = (request: any) => this.filesystem().onboardFSXLUSTREFileSystem(request);
                }
                else {
                    //Extract volume id
                    const volumeIdValue = dot.del("volume_id", providerValues);
                    volumeId = volumeIdValue.split(".")[1];
                    const svmId = volumeIdValue.split(".")[0]
                    if(svmId != dot.pick("svm_id", providerValues)) {
                        this.getOnboardFileSystemForm().setError('InvalidParams','the volume is not mapped to the svm, please refresh the volume list')
                        return;
                    }
                    attachFileSystem = (request: any) => this.filesystem().onboardFSXONTAPFileSystem(request);
                }
                attachFileSystem({
                    ...commonFileSystemValues,
                    ...providerValues,
                    filesystem_id: fileSystemId,
                    volume_id: volumeId
                })
                    .then(() => {
                        this.props.onFlashbarChange({
                            items: [
                                {
                                    type: "success",
                                    content: `File System: ${fileSystemId} was successfully onboarded`,
                                    dismissible: true,
                                },
                            ],
                        });
                        this.setState(
                            {
                                filesystemsNotOnboarded: {},
                            },
                            () => {
                                this.hideOnboardFileSystemForm();
                                this.getListing().fetchRecords();
                            }
                        );
                    })
                    .catch((error) => {
                        this.getOnboardFileSystemForm().setError(error.errorCode, error.message);
                    });
            }}
            onCancel={() => {
                this.hideOnboardFileSystemForm()
            }}
            onStateChange={(event: IdeaFormFieldStateChangeEvent) => {
                console.log(event.value);

            }}
            onFetchOptions={(request) => {
                if (request.param ===  "onboard_filesystem") {
                    return this.filesystem().listFileSystemsInVPC({}).then((result) => {
                        const efsFileSystems = result.efs;
                        const fsxONTAPFileSystems = result.fsx_ontap;
                        const fsxLUSTREFileSystems = result.fsx_lustre;
                        const filesystemsNotOnboarded:FileSystemsNotOnboarded = {};
                        const choices: SocaUserInputChoice[] = []
                        efsFileSystems?.forEach((efsFileSystem) => {
                                const fileSystemId = efsFileSystem.efs.FileSystemId;
                                const provider = Constants.SHARED_STORAGE_PROVIDER_EFS;
                                choices.push( {
                                    title: `${fileSystemId} [${provider}]`,
                                    value: `${provider}.${fileSystemId}`
                                });
                                dot.set(fileSystemId, efsFileSystem, filesystemsNotOnboarded);
                        });
                        fsxONTAPFileSystems?.forEach((fsxONTAPFileSystem) => {
                            const fileSystemId = fsxONTAPFileSystem.filesystem.FileSystemId;
                            const provider = Constants.SHARED_STORAGE_PROVIDER_FSX_NETAPP_ONTAP;
                            choices.push( {
                                title: `${fileSystemId} [${provider}]`,
                                value: `${provider}.${fileSystemId}`
                            });
                            dot.set(fileSystemId, fsxONTAPFileSystem, filesystemsNotOnboarded);
                        });
                        fsxLUSTREFileSystems?.forEach((fsxLUSTREFileSystem) => {
                            const fileSystemId = fsxLUSTREFileSystem.filesystem.FileSystemId;
                            const provider = Constants.SHARED_STORAGE_PROVIDER_FSX_LUSTRE;
                            choices.push( {
                                title: `${fileSystemId} [${provider}]`,
                                value: `${provider}.${fileSystemId}`
                            });
                            dot.set(fileSystemId, fsxLUSTREFileSystem, filesystemsNotOnboarded);
                        });
                        this.setState({
                            filesystemsNotOnboarded
                        });
                        return {
                            listing: choices
                        }
                    })
                }
                else if(request.param === `${Constants.SHARED_STORAGE_PROVIDER_FSX_NETAPP_ONTAP}.svm_id`) {
                    const filesystemsNotOnboarded = this.state.filesystemsNotOnboarded;
                    const selectedOnboardFileSystemValue = this.getSelectedOnboardFileSystem()!.getValueAsString();
                    const filesystemId = selectedOnboardFileSystemValue.split('.')[1];
                    const fsxFileSystem: FSxONTAPFileSystem = dot.pick(filesystemId, filesystemsNotOnboarded);
                    const fsxFileSystemSVMs = fsxFileSystem.svm || [];
                    const choices: SocaUserInputChoice[] = [];
                    fsxFileSystemSVMs.forEach((svm) => {
                        const svmId = dot.pick("StorageVirtualMachineId", svm.storage_virtual_machine);
                        choices.push({
                            title: svmId,
                            value: svmId
                        })
                    });
                    return Promise.resolve({
                        listing: choices
                    });
                }
                else if(request.param === `${Constants.SHARED_STORAGE_PROVIDER_FSX_NETAPP_ONTAP}.volume_id`) {
                    const filesystemsNotOnboarded = this.state.filesystemsNotOnboarded;
                    const selectedOnboardFileSystemValue = this.getSelectedOnboardFileSystem()!.getValueAsString();
                    const selectedSVM = this.getSelectedSVM()!.getValueAsString();
                    const filesystemId = selectedOnboardFileSystemValue.split('.')[1];
                    const fsxFileSystem: FSxONTAPFileSystem = dot.pick(filesystemId, filesystemsNotOnboarded);
                    const fsxFileSystemVolumes = fsxFileSystem.volume;
                    const choices: SocaUserInputChoice[] = [];
                    fsxFileSystemVolumes.forEach((volume) => {
                        if( dot.pick("OntapConfiguration.StorageVirtualMachineId", volume.volume) === selectedSVM) {
                            const volumeId = dot.pick("VolumeId", volume.volume);
                            const svmId = dot.pick("OntapConfiguration.StorageVirtualMachineId", volume.volume);
                            choices.push({
                                title: volumeId,
                                value: `${svmId}.${volumeId}`
                            })
                        }
                    });
                    return Promise.resolve({
                        listing: choices
                    })
                }
                else {
                    return Promise.resolve({
                        listing: [],
                    });
                }
            }}
            params={
                [
                    {
                        name: "onboard_filesystem",
                        title: "Onboard File System",
                        description: "Select applicable file system to onboard",
                        param_type: "select",
                        multiple: false,
                        data_type: "str",
                        dynamic_choices: true,
                    },
                    ...this.buildCommonOnboardFileSystemParams(),
                    ...this.buildOnboardEFSParams(),
                    ...this.buildOnboardFSxNetAppONTAPParams(),
                    ...this.buildOnboardFSxLUSTREParams()
                ]
            }
        />
        );
    }

    buildListing() {
        return (
            <IdeaListView
                ref={this.listing}
                preferencesKey={"filesystem"}
                showPreferences={false}
                title="File Systems"
                description="Create and manage file systems for Virtual Desktops"
                selectionType="single"
                primaryAction={{
                    id: "onboard-filesystem",
                    text: "Onboard File System",
                    onClick: () => {
                        this.showOnboardFileSystemForm();
                    }
                }}
                secondaryActionsDisabled={!this.isSelected()}
                secondaryActions={[
                    {
                        id: "add-filesystem-to-project",
                        text: "Add File System to Project",
                        onClick: () => {
                            this.showAddFileSystemToProjectForm();
                        },
                    },
                    {
                        id: "remove-filesystem-from-project",
                        text: "Remove File System from Project",
                        onClick: () => {
                            this.showRemoveFileSystemFromProjectForm();
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
                    const filesystemNameToken = Utils.asString(filters[0].value).trim().toLowerCase();
                    if (Utils.isEmpty(filesystemNameToken)) {
                        return [];
                    } else {
                        return [
                            {
                                key: "name",
                                like: filesystemNameToken,
                            },
                        ];
                    }
                }}
                onRefresh={() => {
                    this.setState(
                        {
                            filesystemSelected: false,
                        },
                        () => {
                            this.getListing().fetchRecords();
                        }
                    );
                }}
                selectedItems={this.state.selectedFileSystem}
                onSelectionChange={(event) => {
                    this.setState({
                        filesystemSelected: true,
                        selectedFileSystem: event.detail.selectedItems
                    })
                }}
                onFetchRecords={() => {
                    return this.getSharedFileSystemTableItems();
                }}
                columnDefinitions={FILESYSTEM_TABLE_COLUMN_DEFINITIONS}
            />
        );
    }

    getSelectedFileSystem = () => {
        if(this.state.selectedFileSystem.length === 0) {
            return null
        }
        return this.state.selectedFileSystem[0]
    }

    buildSplitPanelContent() {
        return (
            this.isSelected() && (
                <IdeaSplitPanel title={`Details for ${this.getSelectedFileSystem()?.getName()}`}>
                    <SpaceBetween size={"l"}>
                        <Container header={<Header variant={"h2"}>General</Header>}>
                            <ColumnLayout variant={"text-grid"} columns={3}>
                                <KeyValue title="Name" value={this.getSelectedFileSystem()?.getName()} clipboard={true}/>
                                <KeyValue title="Title" value={this.getSelectedFileSystem()?.getTitle()} clipboard={true}/>
                                <KeyValue title="Provider" value={this.getSelectedFileSystem()?.getProviderTitle()} clipboard={true}/>
                                <KeyValue title="Created through RES?" value={!this.getSelectedFileSystem()?.isExistingFileSystem()} type={"boolean"}/>
                                <KeyValue title="FileSystem ID" value={this.getSelectedFileSystem()?.getFileSystemId()} clipboard={true}/>
                                {!this.getSelectedFileSystem()?.isFsxNetAppOntap() && <KeyValue title="DNS Name " value={this.getSelectedFileSystem()?.getFileSystemDns()} clipboard={true}/>}
                            </ColumnLayout>
                        </Container>
                        <Container header={<Header variant={"h2"}>Mount Settings</Header>}>
                            <ColumnLayout variant={"text-grid"} columns={3}>
                                {this.getSelectedFileSystem()?.hasMountDirectory() && <KeyValue title="Mount Directory (Linux)" value={this.getSelectedFileSystem()?.getMountDirectory()}/>}
                                {this.getSelectedFileSystem()?.hasMountDrive() && <KeyValue title="Mount Drive (Windows)" value={this.getSelectedFileSystem()?.getMountDrive()}/>}
                                {this.getSelectedFileSystem()?.hasMountDrive() && <KeyValue title="File Share Name" value={this.getSelectedFileSystem()?.getFileShareName()}/>}
                                <KeyValue title="Scope" value={this.getSelectedFileSystem()?.getScope()}/>
                                {this.getSelectedFileSystem()?.isScopeProjects() && <KeyValue title="Projects" value={this.getSelectedFileSystem()?.getProjects()}/>}
                           </ColumnLayout>
                        </Container>
                        {this.getSelectedFileSystem()?.isFsxNetAppOntap() && <Container header={<Header variant={"h2"}>Storage Virtual Machine</Header>}>
                            <ColumnLayout variant={"text-grid"} columns={3}>
                                <KeyValue title="Storage Virtual Machine ID" value={this.getSelectedFileSystem()?.getSvmId()} clipboard={true}/>
                                <KeyValue title="SMB DNS" value={this.getSelectedFileSystem()?.getSvmSmbDns()} clipboard={true}/>
                                <KeyValue title="NFS DNS" value={this.getSelectedFileSystem()?.getSvmNfsDns()} clipboard={true}/>
                                <KeyValue title="Management DNS" value={this.getSelectedFileSystem()?.getSvmManagementDns()} clipboard={true}/>
                                <KeyValue title="iSCSI DNS" value={this.getSelectedFileSystem()?.getSvmIscsiDns()} clipboard={true}/>
                            </ColumnLayout>
                        </Container>
                        }
                        {this.getSelectedFileSystem()?.isVolumeApplicable() && <Container header={<Header variant={"h2"}>Volume</Header>}>
                            <ColumnLayout variant={"text-grid"} columns={3}>
                                <KeyValue title="Volume ID" value={this.getSelectedFileSystem()?.getVolumeId()} clipboard={true}/>
                                <KeyValue title="Volume Path" value={this.getSelectedFileSystem()?.getVolumePath()} clipboard={true}/>
                                {this.getSelectedFileSystem()?.isFsxNetAppOntap() && <KeyValue title="Security Style" value={this.getSelectedFileSystem()?.getVolumeSecurityStyle()} clipboard={true}/>}
                            </ColumnLayout>
                        </Container>
                        }
                        </SpaceBetween>
                </IdeaSplitPanel>
            )
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
                        text: "File System",
                        href: "",
                    },
                ]}
                content={
                    <div>
                        {this.state.showAddFileSystemToProjectForm && this.buildAddFileSystemToProjectForm()}
                        {this.state.showRemoveFileSystemFromProjectForm && this.buildRemoveFileSystemFromProjectForm()}
                        {this.state.showOnboardFileSystemForm && this.buildOnboardFileSystemForm()}
                        {this.buildListing()}
                    </div>
                }
                splitPanelOpen={this.state.splitPanelOpen}
                splitPanel={this.buildSplitPanelContent()}
                onSplitPanelToggle={(event: any) => {
                    this.setState({
                        splitPanelOpen: event.detail.open,
                    });
                }}
            />
        );
    }
}

export default withRouter(FileSystems);
