import IdeaAppLayout, { IdeaAppLayoutProps } from "../../components/app-layout";
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import { TableProps } from "@cloudscape-design/components/table/interfaces";
import { FileSystemsNotOnboarded, FSxONTAPFileSystem, GetParamChoicesRequest, GetParamChoicesResult, SocaFilter, SocaUserInputChoice, SocaUserInputParamMetadata } from "../../client/data-model";
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
import IdeaSplitPanel from "../../components/split-panel";
import { ColumnLayout, Container, FormField, Header, Input, SpaceBetween } from "@cloudscape-design/components";
import { KeyValue } from "../../components/key-value";
import ProxyClient from "../../client/proxy-client";
import ProxyService from "../../service/proxy-service";
import IdeaConfirm from "../../components/modals";

export interface FileSystemProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {}

export interface FileSystemState {
    filesystemSelected: boolean;
    selectedFileSystem: SharedStorageFileSystem[];
    showAddFileSystemToProjectForm: boolean;
    showRemoveFileSystemFromProjectForm: boolean;
    showOnboardFileSystemForm: boolean;
    showRemoveFileSystemConfirmModal: boolean;
    filesystemsNotOnboarded: FileSystemsNotOnboarded;
    splitPanelOpen: boolean;
    fileSystemOnboardingOptionLoading: boolean;
    removeFileSystemConfirmText: string;
    currentSelectedSVM: string;
}

export const FILESYSTEM_TABLE_COLUMN_DEFINITIONS: TableProps.ColumnDefinition<SharedStorageFileSystem>[] = [
    {
        id: "title",
        header: "Title",
        cell: (filesystem) => filesystem.getTitle(),
        sortingComparator: (a, b) => a.getTitle().localeCompare(b.getTitle())
    },
    {
        id: "name",
        header: "Name",
        cell: (filesystem) => filesystem.getName(),
        sortingComparator: (a, b) => a.getName().localeCompare(b.getName())
    },
    {
        id: "filesystem_id",
        header: "File System ID",
        cell: (filesystem) => filesystem.getFileSystemId(),
        sortingComparator: (a, b) => a.getFileSystemId().localeCompare(b.getFileSystemId())
    },
    {
        id: "volume_id",
        header: "Volume ID",
        cell: (filesystem) => filesystem.getVolumeId() || "—",
        sortingComparator: (a, b) => {
            const volumeA = a.getVolumeId() || "";
            const volumeB = b.getVolumeId() || "";
            return volumeA.localeCompare(volumeB);
        }
    },
    {
        id: "scope",
        header: "Scope",
        cell: (filesystem) => filesystem.getScope(),
        sortingComparator: (a, b) => {
            const scopeA = a.getScope().join(',');
            const scopeB = b.getScope().join(',');
            return scopeA.localeCompare(scopeB);
        }
    },
    {
        id: "provider",
        header: "Provider",
        cell: (filesystem) => filesystem.getProvider(),
        sortingComparator: (a, b) => a.getProvider().localeCompare(b.getProvider())
    },
];

class FileSystems extends Component<FileSystemProps, FileSystemState> {
    listing: RefObject<IdeaListView>;
    addFileSystemToProjectForm: RefObject<IdeaForm>;
    removeFileSystemFromProjectForm: RefObject<IdeaForm>;
    onboardFileSystemForm: RefObject<IdeaForm>;
    removeFileSystemConfirmModal: RefObject<IdeaConfirm>;

    constructor(props: FileSystemProps) {
        super(props);
        this.listing = React.createRef();
        this.addFileSystemToProjectForm = React.createRef();
        this.removeFileSystemFromProjectForm = React.createRef();
        this.onboardFileSystemForm = React.createRef();
        this.removeFileSystemConfirmModal = React.createRef();
        this.state = {
            filesystemSelected: false,
            showAddFileSystemToProjectForm: false,
            showRemoveFileSystemFromProjectForm: false,
            showOnboardFileSystemForm: false,
            showRemoveFileSystemConfirmModal: false,
            filesystemsNotOnboarded: {},
            splitPanelOpen: false,
            selectedFileSystem: [],
            fileSystemOnboardingOptionLoading: false,
            removeFileSystemConfirmText: '',
            currentSelectedSVM: '',
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

    proxy(): ProxyClient {
        return AppContext.get().client().proxy();
    }

    proxyService(): ProxyService {
        return new ProxyService(this.proxy(), AppContext.get().getClusterSettingsService(), this.clusterSettings());
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

    buildRemoveFileSystemConfirmModal() {
        const selectedFileSystem = this.getSelectedFileSystem();
        const selectedFileSystemProjects = selectedFileSystem?.getProjects()!
        return (
                <IdeaConfirm
                    ref={this.removeFileSystemConfirmModal}
                    title={`Remove FileSystem: ${selectedFileSystem?.name!}`}
                    confirmButtonDisabled={(this.state.removeFileSystemConfirmText !== selectedFileSystem?.name!) || (selectedFileSystemProjects && selectedFileSystemProjects.length != 0)}
                    onConfirm={() => {
                        try {
                            this.setState({
                                removeFileSystemConfirmText: '',
                            });
                            this.filesystem().removeFileSystem({
                                filesystem_name: selectedFileSystem?.name!,
                            });
                            this.props.onFlashbarChange({
                                items: [{
                                    type: "success",
                                    content: `File System: ${selectedFileSystem?.name!} has been removed successfully`,
                                    dismissible: true,
                                }],
                            });
                        } catch (error: any) {
                            this.props.onFlashbarChange({
                                items: [{
                                    type: "error",
                                    content: error.message,
                                    dismissible: true,
                                }],
                            });
                        }
                    }}
                    onCancel={() => {
                        this.setState({
                            showRemoveFileSystemConfirmModal: false,
                            removeFileSystemConfirmText: '',
                        })
                    }}
                >
                    {selectedFileSystemProjects ? (
                        <div>
                            <p>Unable to remove file system. This file system has the following attached projects:</p>
                            <b><i>{selectedFileSystemProjects.join(', ')}</i></b>
                            <p> Please remove all associated projects before removing this file system.</p>
                        </div>
                    ) : (
                        <FormField
                            label="To confirm deletion, enter the name of the file system in the text input field."
                        >
                            <Input
                                value={this.state.removeFileSystemConfirmText}
                                onChange={({ detail }) =>
                                    this.setState({ removeFileSystemConfirmText: detail.value })
                                }
                                placeholder={selectedFileSystem?.name!}
                            />
                        </FormField>
                    )}
                </IdeaConfirm>
        );
    }

    showRemoveFileSystemConfirmModal() {
        this.setState(
            {
                showRemoveFileSystemConfirmModal: true,
            },
            () => {
                this.getRemoveFileSystemConfirmModal().show();
            }
        );
    }

    getRemoveFileSystemConfirmModal() {
        return this.removeFileSystemConfirmModal.current!;
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
                },
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
                    message: "Only use lowercase alphabets, numbers and underscore (_). Must be between 3 and 18 characters long.",
                },
            },
        ];
        commonOnboardFileSystemParams.forEach((param) => {
            param.when = {
                param: "onboard_filesystem",
                not_empty: true,
            };
        });
        return commonOnboardFileSystemParams;
    }

    buildOnboardEFSParams(): SocaUserInputParamMetadata[] {
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
                    message: "Only use lowercase alphabets, numbers, and hyphens (-). Must be between 3 and 18 characters long starting with '/'.",
                },
            },
        ];
        efsParams.forEach((param) => {
            param.when = {
                param: "onboard_filesystem",
                starts_with: Constants.SHARED_STORAGE_PROVIDER_EFS,
            };
        });

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
                    starts_with: Constants.SHARED_STORAGE_PROVIDER_FSX_NETAPP_ONTAP,
                },
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
                refresh_on_dependency_change: [`${Constants.SHARED_STORAGE_PROVIDER_FSX_NETAPP_ONTAP}.svm_id`],
                when: {
                    param: `${Constants.SHARED_STORAGE_PROVIDER_FSX_NETAPP_ONTAP}.svm_id`,
                    not_empty: true,
                },
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
                    message: "Only use lowercase alphabets, numbers, and hyphens (-). Must be between 3 and 18 characters long starting with '/'.",
                },
                when: {
                    param: "onboard_filesystem",
                    starts_with: Constants.SHARED_STORAGE_PROVIDER_FSX_NETAPP_ONTAP,
                },
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
                    message: "Only use an uppercase alphabet",
                },
                when: {
                    param: "onboard_filesystem",
                    starts_with: Constants.SHARED_STORAGE_PROVIDER_FSX_NETAPP_ONTAP,
                },
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
                    message: "Only use an uppercase, lowercase alphabet, numbers, hyphens (-) or underscore (_) Must be between 3 and 18 characters long.",
                },
                when: {
                    param: `${Constants.SHARED_STORAGE_PROVIDER_FSX_NETAPP_ONTAP}.mount_drive`,
                    not_empty: true,
                },
            },
        ];

        return fSxNetAppONTAPParams;
    }

    buildOnboardFSxLUSTREParams(): SocaUserInputParamMetadata[] {
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
                    message: "Only use lowercase alphabets, numbers, and hyphens (-). Must be between 3 and 18 characters long starting with '/'.",
                },
            },
        ];
        fsxLUSTREParams.forEach((param) => {
            param.when = {
                param: "onboard_filesystem",
                starts_with: Constants.SHARED_STORAGE_PROVIDER_FSX_LUSTRE,
            };
        });

        return fsxLUSTREParams;
    }

    getSelectedOnboardFileSystem() {
        return this.getOnboardFileSystemForm().getFormField("onboard_filesystem");
    }

    getSelectedSVM() {
        return this.getOnboardFileSystemForm().getFormField(`${Constants.SHARED_STORAGE_PROVIDER_FSX_NETAPP_ONTAP}.svm_id`);
    }

    saveFilesystemIdentifierToLocalStorage(identifier: string): void {
        const idsInLocalStorage = localStorage.getItem(Constants.NEWLY_ONBOARDED_FILE_SYSTEM_STORAGE_NAME);
        const projectIds = idsInLocalStorage ? JSON.parse(idsInLocalStorage) : [];
        // Cache is valid for 30 seconds
        projectIds.push({ id: identifier, exp: Date.now() + 30 * 1000 });
        localStorage.setItem(Constants.NEWLY_ONBOARDED_FILE_SYSTEM_STORAGE_NAME, JSON.stringify(projectIds));
    }

    removeFilesystemIdentifierFromLocalStorage(identifier: string): void {
        const idsInLocalStorage = localStorage.getItem(Constants.NEWLY_ONBOARDED_FILE_SYSTEM_STORAGE_NAME);
        if (idsInLocalStorage) {
            const projectIds = JSON.parse(idsInLocalStorage);
            const filteredIds = projectIds.filter((project: { id: string; exp: number }) => project.id !== identifier);
            localStorage.setItem(Constants.NEWLY_ONBOARDED_FILE_SYSTEM_STORAGE_NAME, JSON.stringify(filteredIds));
        }
    }

    getFilesystemIdsFromLocalStorage(): string[] {
        const idsInLocalStorage = localStorage.getItem(Constants.NEWLY_ONBOARDED_FILE_SYSTEM_STORAGE_NAME);
        if (idsInLocalStorage) {
            const projectIds = JSON.parse(idsInLocalStorage);
            const validProjectIds = projectIds.filter((project: { id: string; exp: number }) => project.exp > Date.now());
            localStorage.setItem(Constants.NEWLY_ONBOARDED_FILE_SYSTEM_STORAGE_NAME, JSON.stringify(validProjectIds));
            return validProjectIds.map((project: { id: string; exp: number }) => project.id);
        }
        return [];
    }

    buildOnboardFileSystemForm() {
        return (
            <IdeaForm
                ref={this.onboardFileSystemForm}
                name="onboard-filesystem"
                modal={true}
                modalSize="medium"
                title="Onboard New File System"
                onSubmit={() => {
                    if (!this.getOnboardFileSystemForm().validate()) {
                        return;
                    }
                    const values = this.getOnboardFileSystemForm().getValues();
                    if (
                        !dot.pick(`${Constants.SHARED_STORAGE_PROVIDER_EFS}.mount_directory`, values) &&
                        !dot.pick(`${Constants.SHARED_STORAGE_PROVIDER_FSX_NETAPP_ONTAP}.mount_directory`, values) &&
                        !dot.pick(`${Constants.SHARED_STORAGE_PROVIDER_FSX_NETAPP_ONTAP}.mount_drive`, values) &&
                        !dot.pick(`${Constants.SHARED_STORAGE_PROVIDER_FSX_LUSTRE}.mount_directory`, values)
                    ) {
                        this.getOnboardFileSystemForm().setError("InvalidParams", "one of mount directory or mount drive is required");
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
                    let attachFileSystem: (request: any) => Promise<any>;
                    let volumeId: string | undefined;
                    if (provider === Constants.SHARED_STORAGE_PROVIDER_EFS) {
                        attachFileSystem = (request: any) => this.filesystem().onboardEFSFileSystem(request);
                    } else if (provider === Constants.SHARED_STORAGE_PROVIDER_FSX_LUSTRE) {
                        attachFileSystem = (request: any) => this.filesystem().onboardFSXLUSTREFileSystem(request);
                    } else {
                        //Extract volume id
                        const volumeIdValue = dot.del("volume_id", providerValues);
                        volumeId = volumeIdValue.split(".")[1];
                        const svmId = volumeIdValue.split(".")[0];
                        if (svmId != dot.pick("svm_id", providerValues)) {
                            this.getOnboardFileSystemForm().setError("InvalidParams", "the volume is not mapped to the svm, please refresh the volume list");
                            return;
                        }
                        attachFileSystem = (request: any) => this.filesystem().onboardFSXONTAPFileSystem(request);
                    }

                    // Save to localStorage IMMEDIATELY to prevent timing issues
                    const identifier = provider === Constants.SHARED_STORAGE_PROVIDER_FSX_NETAPP_ONTAP
                        ? `${fileSystemId}:${volumeId}`
                        : fileSystemId;
                    this.saveFilesystemIdentifierToLocalStorage(identifier);

                    this.hideOnboardFileSystemForm();
                    this.props.onFlashbarChange({
                        items: [
                            {
                                type: "success",
                                content: `File System: ${fileSystemId} is being onboarded, it will be available once the onboarding process is complete.`,
                                dismissible: true,
                            },
                        ],
                    });

                    attachFileSystem({
                        ...commonFileSystemValues,
                        ...providerValues,
                        filesystem_id: fileSystemId,
                        volume_id: volumeId,
                    })
                        .then(() => {
                            this.setState(
                                {
                                    filesystemsNotOnboarded: {},
                                },
                                () => {
                                    this.getListing().fetchRecords();
                                }
                            );
                        })
                        .catch((error) => {
                            this.removeFilesystemIdentifierFromLocalStorage(identifier);

                            this.props.onFlashbarChange({
                                items: [
                                    {
                                        type: "error",
                                        content: `Failed to onboard File System: ${fileSystemId}. Error: ${error.message}`,
                                        dismissible: true,
                                    },
                                ],
                            });
                        });
                }}
                onCancel={() => {
                    this.hideOnboardFileSystemForm();
                }}
                onFetchOptions={(request) => {
                    if (request.param === "onboard_filesystem") {
                        this.setState({ fileSystemOnboardingOptionLoading: true });
                        return this.proxyService()
                            .listFileSystemsForOnboard(this.getFilesystemIdsFromLocalStorage())
                            .then((result) => {
                                const efsFileSystems = result.efs;
                                const fsxONTAPFileSystems = result.fsx_ontap;
                                const fsxLUSTREFileSystems = result.fsx_lustre;
                                const filesystemsNotOnboarded: FileSystemsNotOnboarded = {};
                                const choices: SocaUserInputChoice[] = [];
                                efsFileSystems?.forEach((efsFileSystem) => {
                                    const fileSystemId = efsFileSystem.efs.FileSystemId;
                                    const provider = Constants.SHARED_STORAGE_PROVIDER_EFS;
                                    choices.push({
                                        title: `${fileSystemId} [${provider}]`,
                                        value: `${provider}.${fileSystemId}`,
                                    });
                                    dot.set(fileSystemId, efsFileSystem, filesystemsNotOnboarded);
                                });
                                fsxONTAPFileSystems?.forEach((fsxONTAPFileSystem) => {
                                    const fileSystemId = fsxONTAPFileSystem.filesystem.FileSystemId;
                                    const provider = Constants.SHARED_STORAGE_PROVIDER_FSX_NETAPP_ONTAP;
                                    choices.push({
                                        title: `${fileSystemId} [${provider}]`,
                                        value: `${provider}.${fileSystemId}`,
                                    });
                                    dot.set(fileSystemId, fsxONTAPFileSystem, filesystemsNotOnboarded);
                                });
                                fsxLUSTREFileSystems?.forEach((fsxLUSTREFileSystem) => {
                                    const fileSystemId = fsxLUSTREFileSystem.filesystem.FileSystemId;
                                    const provider = Constants.SHARED_STORAGE_PROVIDER_FSX_LUSTRE;
                                    choices.push({
                                        title: `${fileSystemId} [${provider}]`,
                                        value: `${provider}.${fileSystemId}`,
                                    });
                                    dot.set(fileSystemId, fsxLUSTREFileSystem, filesystemsNotOnboarded);
                                });
                                this.setState({
                                    filesystemsNotOnboarded,
                                    fileSystemOnboardingOptionLoading: false,
                                });
                                return {
                                    listing: choices,
                                };
                            });
                    } else if (request.param === `${Constants.SHARED_STORAGE_PROVIDER_FSX_NETAPP_ONTAP}.svm_id`) {
                        const selectedOnboardFileSystemValue = this.getSelectedOnboardFileSystem()!.getValueAsString();
                        const filesystemId = selectedOnboardFileSystemValue.split(".")[1];

                        if (request.refresh) {
                            return Promise.resolve(this.forceRefreshSVMs(filesystemId));
                        }

                        const filesystemsNotOnboarded = this.state.filesystemsNotOnboarded;
                        const fsxFileSystem: FSxONTAPFileSystem = dot.pick(filesystemId, filesystemsNotOnboarded);
                        const fsxFileSystemSVMs = fsxFileSystem.svm || [];
                        const choices: SocaUserInputChoice[] = [];
                        fsxFileSystemSVMs.forEach((svm) => {
                            const svmId = dot.pick("StorageVirtualMachineId", svm.storage_virtual_machine);
                            choices.push({
                                title: svmId,
                                value: svmId,
                            });
                        });
                        return Promise.resolve({
                            listing: choices,
                        });
                    } else if (request.param === `${Constants.SHARED_STORAGE_PROVIDER_FSX_NETAPP_ONTAP}.volume_id`) {
                        const selectedOnboardFileSystemValue = this.getSelectedOnboardFileSystem()!.getValueAsString();
                        const selectedSVM = this.getSelectedSVM()!.getValueAsString();
                        const filesystemId = selectedOnboardFileSystemValue.split(".")[1];

                        if (request.refresh) {
                            return Promise.resolve(this.forceRefreshVolumes(filesystemId, selectedSVM));
                        }

                        if (this.state.currentSelectedSVM && this.state.currentSelectedSVM !== selectedSVM) {
                            const volumeField = this.getOnboardFileSystemForm().getFormField(`${Constants.SHARED_STORAGE_PROVIDER_FSX_NETAPP_ONTAP}.volume_id`);
                            if (volumeField) {
                                volumeField.setValue('');
                            }

                            this.setState({ currentSelectedSVM: selectedSVM });
                        }

                        const filesystemsNotOnboarded = this.state.filesystemsNotOnboarded;
                        const fsxFileSystem: FSxONTAPFileSystem = dot.pick(filesystemId, filesystemsNotOnboarded);

                        if (!fsxFileSystem || !fsxFileSystem.volume) {
                            return Promise.resolve({
                                listing: [],
                            });
                        }

                        const fsxFileSystemVolumes = fsxFileSystem.volume;
                        const choices: SocaUserInputChoice[] = [];
                        fsxFileSystemVolumes.forEach((volume) => {
                            if (dot.pick("OntapConfiguration.StorageVirtualMachineId", volume.volume) === selectedSVM) {
                                const volumeId = dot.pick("VolumeId", volume.volume);
                                const svmId = dot.pick("OntapConfiguration.StorageVirtualMachineId", volume.volume);
                                choices.push({
                                    title: volumeId,
                                    value: `${svmId}.${volumeId}`,
                                });
                            }
                        });

                        return Promise.resolve({
                            listing: choices,
                        });
                    } else {
                        return Promise.resolve({
                            listing: [],
                        });
                    }
                }}
                params={[
                    {
                        name: "onboard_filesystem",
                        title: "Onboard File System",
                        readonly: this.state.fileSystemOnboardingOptionLoading,
                        description: this.state.fileSystemOnboardingOptionLoading ? "Selections loading..." : "Select applicable file system to onboard",
                        param_type: "select",
                        multiple: false,
                        data_type: "str",
                        dynamic_choices: true,
                    },
                    ...this.buildCommonOnboardFileSystemParams(),
                    ...this.buildOnboardEFSParams(),
                    ...this.buildOnboardFSxNetAppONTAPParams(),
                    ...this.buildOnboardFSxLUSTREParams(),
                ]}
            />
        );
    }

    async forceRefreshSVMs(filesystemId: string) {
        return this.proxyService()
            .listFileSystemsForOnboard(this.getFilesystemIdsFromLocalStorage())
            .then((result) => {
                const fsxONTAPFileSystems = result.fsx_ontap;
                const refreshedFileSystem = fsxONTAPFileSystems?.find(fs => fs.filesystem.FileSystemId === filesystemId);

                if (refreshedFileSystem) {
                    const filesystemsNotOnboarded = {...this.state.filesystemsNotOnboarded};
                    dot.set(filesystemId, refreshedFileSystem, filesystemsNotOnboarded);
                    this.setState({ filesystemsNotOnboarded });

                    const volumeField = this.getOnboardFileSystemForm().getFormField(`${Constants.SHARED_STORAGE_PROVIDER_FSX_NETAPP_ONTAP}.volume_id`);
                    if (volumeField) {
                        volumeField.setValue('');
                    }

                    const fsxFileSystemSVMs = refreshedFileSystem.svm || [];
                    const choices: SocaUserInputChoice[] = [];
                    fsxFileSystemSVMs.forEach((svm) => {
                        const svmId = dot.pick("StorageVirtualMachineId", svm.storage_virtual_machine);
                        choices.push({
                            title: svmId,
                            value: svmId,
                        });
                    });
                    return { listing: choices };
                }
                return { listing: [] };
            });
    }

    async forceRefreshVolumes(filesystemId: string, selectedSVM: string) {
        return this.proxyService()
            .listFileSystemsForOnboard(this.getFilesystemIdsFromLocalStorage())
            .then((result) => {
                const fsxONTAPFileSystems = result.fsx_ontap;
                const refreshedFileSystem = fsxONTAPFileSystems?.find(fs => fs.filesystem.FileSystemId === filesystemId);

                if (refreshedFileSystem) {
                    const filesystemsNotOnboarded = {...this.state.filesystemsNotOnboarded};
                    dot.set(filesystemId, refreshedFileSystem, filesystemsNotOnboarded);
                    this.setState({ filesystemsNotOnboarded });

                    const fsxFileSystemVolumes = refreshedFileSystem.volume;
                    const choices: SocaUserInputChoice[] = [];

                    fsxFileSystemVolumes.forEach((volume) => {
                        if (dot.pick("OntapConfiguration.StorageVirtualMachineId", volume.volume) === selectedSVM) {
                            const volumeId = dot.pick("VolumeId", volume.volume);
                            const svmId = dot.pick("OntapConfiguration.StorageVirtualMachineId", volume.volume);
                            choices.push({
                                title: volumeId,
                                value: `${svmId}.${volumeId}`,
                            });
                        }
                    });

                    return { listing: choices };
                }
                return { listing: [] };
            });
    }

    buildListing() {
        return (
            <IdeaListView
                ref={this.listing}
                preferencesKey={"filesystem"}
                showPreferences={false}
                title="File systems"
                description="Create and manage file systems for Virtual Desktops"
                selectionType="single"
                primaryAction={{
                    id: "onboard-filesystem",
                    text: "Onboard File System",
                    onClick: () => {
                        this.showOnboardFileSystemForm();
                    },
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
                    {
                        id: "remove-filesystem",
                        text: "Remove File System",
                        onClick: () => {
                            if (this.getSelectedFileSystem()?.name! === "home") {
                                this.props.onFlashbarChange({
                                    items: [{
                                        type: "error",
                                        content: "Deletion of the home file system is not permitted.",
                                        dismissible: true,
                                    }],
                                });
                            } else {
                            this.showRemoveFileSystemConfirmModal();
                            }
                        },
                    }
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
                        selectedFileSystem: event.detail.selectedItems,
                    });
                }}
                onFetchRecords={() => {
                    return this.getSharedFileSystemTableItems();
                }}
                columnDefinitions={FILESYSTEM_TABLE_COLUMN_DEFINITIONS}
            />
        );
    }

    getSelectedFileSystem = () => {
        if (this.state.selectedFileSystem.length === 0) {
            return null;
        }
        return this.state.selectedFileSystem[0];
    };

    buildSplitPanelContent() {
        return (
            this.isSelected() && (
                <IdeaSplitPanel title={`Details for ${this.getSelectedFileSystem()?.getName()}`}>
                    <SpaceBetween size={"l"}>
                        <Container header={<Header variant={"h2"}>General</Header>}>
                            <ColumnLayout variant={"text-grid"} columns={3}>
                                <KeyValue title="Name" value={this.getSelectedFileSystem()?.getName()} clipboard={true} />
                                <KeyValue title="Title" value={this.getSelectedFileSystem()?.getTitle()} clipboard={true} />
                                <KeyValue title="Provider" value={this.getSelectedFileSystem()?.getProviderTitle()} clipboard={true} />
                                <KeyValue title="Created through RES?" value={!this.getSelectedFileSystem()?.isExistingFileSystem()} type={"boolean"} />
                                <KeyValue title="FileSystem ID" value={this.getSelectedFileSystem()?.getFileSystemId()} clipboard={true} />
                                {!this.getSelectedFileSystem()?.isFsxNetAppOntap() && <KeyValue title="DNS Name " value={this.getSelectedFileSystem()?.getFileSystemDns()} clipboard={true} />}
                            </ColumnLayout>
                        </Container>
                        <Container header={<Header variant={"h2"}>Mount Settings</Header>}>
                            <ColumnLayout variant={"text-grid"} columns={3}>
                                {this.getSelectedFileSystem()?.hasMountDirectory() && <KeyValue title="Mount Directory (Linux)" value={this.getSelectedFileSystem()?.getMountDirectory()} />}
                                {this.getSelectedFileSystem()?.hasMountDrive() && <KeyValue title="Mount Drive (Windows)" value={this.getSelectedFileSystem()?.getMountDrive()} />}
                                {this.getSelectedFileSystem()?.hasMountDrive() && <KeyValue title="File Share Name" value={this.getSelectedFileSystem()?.getFileShareName()} />}
                                <KeyValue title="Scope" value={this.getSelectedFileSystem()?.getScope()} />
                                {this.getSelectedFileSystem()?.isScopeProjects() && <KeyValue title="Projects" value={this.getSelectedFileSystem()?.getProjects()} />}
                            </ColumnLayout>
                        </Container>
                        {this.getSelectedFileSystem()?.isFsxNetAppOntap() && (
                            <Container header={<Header variant={"h2"}>Storage Virtual Machine</Header>}>
                                <ColumnLayout variant={"text-grid"} columns={3}>
                                    <KeyValue title="Storage Virtual Machine ID" value={this.getSelectedFileSystem()?.getSvmId()} clipboard={true} />
                                    <KeyValue title="SMB DNS" value={this.getSelectedFileSystem()?.getSvmSmbDns()} clipboard={true} />
                                    <KeyValue title="NFS DNS" value={this.getSelectedFileSystem()?.getSvmNfsDns()} clipboard={true} />
                                    <KeyValue title="Management DNS" value={this.getSelectedFileSystem()?.getSvmManagementDns()} clipboard={true} />
                                    <KeyValue title="iSCSI DNS" value={this.getSelectedFileSystem()?.getSvmIscsiDns()} clipboard={true} />
                                </ColumnLayout>
                            </Container>
                        )}
                        {this.getSelectedFileSystem()?.isVolumeApplicable() && (
                            <Container header={<Header variant={"h2"}>Volume</Header>}>
                                <ColumnLayout variant={"text-grid"} columns={3}>
                                    <KeyValue title="Volume ID" value={this.getSelectedFileSystem()?.getVolumeId()} clipboard={true} />
                                    <KeyValue title="Volume Path" value={this.getSelectedFileSystem()?.getVolumePath()} clipboard={true} />
                                    {this.getSelectedFileSystem()?.isFsxNetAppOntap() && <KeyValue title="Security Style" value={this.getSelectedFileSystem()?.getVolumeSecurityStyle()} clipboard={true} />}
                                </ColumnLayout>
                            </Container>
                        )}
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
                        text: "File system",
                        href: "",
                    },
                ]}
                content={
                    <div>
                        {this.state.showAddFileSystemToProjectForm && this.buildAddFileSystemToProjectForm()}
                        {this.state.showRemoveFileSystemFromProjectForm && this.buildRemoveFileSystemFromProjectForm()}
                        {this.state.showOnboardFileSystemForm && this.buildOnboardFileSystemForm()}
                        {this.state.showRemoveFileSystemConfirmModal && this.buildRemoveFileSystemConfirmModal()}
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
