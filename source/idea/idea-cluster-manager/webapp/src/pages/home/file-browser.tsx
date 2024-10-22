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

import { ClusterSettingsClient, FileBrowserClient } from "../../client";
import { AppContext } from "../../common";
import { ListFilesResult } from "../../client/data-model";
import { LocalStorageService } from "../../service";
import Utils from "../../common/utils";
import { Alert, Box, Button, CodeEditor, ColumnLayout, Container, Header, Link, Modal, SpaceBetween, StatusIndicator, Tabs, Tiles, FlashbarProps } from "@cloudscape-design/components";
import { ChonkyActions, FileData, FileNavbar, FileBrowser, FileToolbar, FileList, FileContextMenu, defineFileAction } from "chonky";
import dot from "dot-object";

import "ace-builds/css/ace.css";
import "ace-builds/css/theme/dawn.css";
import { CodeEditorProps } from "@cloudscape-design/components/code-editor/interfaces";
import { faDownload, faMicrochip, faRedo, faStar, faTerminal, faTrash } from "@fortawesome/free-solid-svg-icons";
import Uppy from "@uppy/core";
import XHRUpload from "@uppy/xhr-upload";
import Dashboard from "@uppy/dashboard";
import "@uppy/core/dist/style.css";
import "@uppy/dashboard/dist/style.css";
import IdeaForm from "../../components/form";
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import IdeaAppLayout, { IdeaAppLayoutProps } from "../../components/app-layout";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { KeyValue } from "../../components/key-value";
import { Constants, ErrorCodes, ErrorMessages } from "../../common/constants";
import IdeaConfirm from "../../components/modals";
import { withRouter } from "../../navigation/navigation-utils";

export interface IdeaFileBrowserProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {}

export interface IdeaFileBrowserState {
    files: FileData[];
    favorites: FileData[];
    folderChain: FileData[];
    filesToDelete: FileData[];
    showDeleteConfirmModal: boolean;
    editorOpen: boolean;
    fileUploadResult: any;
    activeTabId: string;
    downloadPemLoading: boolean;
    downloadPpkLoading: boolean;
    sshHostIp: string;
    sshAccess: boolean;
    fileTransferMethod: string;
    isLoading: boolean;
    isFileBrowserEnabled: boolean;
}

export interface IdeaFileEditorProps {
    show: boolean;
    onSave: (file: string, content: string) => Promise<boolean>;
    onClose: () => void;
    language?: CodeEditorProps.Language;
    filepath?: string;
    content?: string;
}

export interface IdeaFileEditorState {
    ace: any;
    preferences: any;
    language: CodeEditorProps.Language;
    filepath: string;
    content: string;
    onSaveMessage: React.ReactNode | null;
}

const CustomActionSubmitJob = defineFileAction({
    id: "soca_submit_job",
    button: {
        name: "Submit Job",
        toolbar: true,
        contextMenu: true,
        icon: faMicrochip,
    },
});

const CustomActionFavorite = defineFileAction({
    id: "soca_favorite",
    button: {
        name: "Favorite",
        toolbar: true,
        contextMenu: true,
        icon: faStar,
    },
});

const CustomActionRemoveFavorite = defineFileAction({
    id: "soca_remove_favorite",
    button: {
        name: "Remove Favorite",
        toolbar: true,
        contextMenu: true,
        icon: faTrash,
    },
});

const CustomActionRefresh = defineFileAction({
    id: "soca_refresh",
    button: {
        name: "Refresh",
        toolbar: true,
        contextMenu: true,
        icon: faRedo,
    },
});

const CustomActionTailLogFile = defineFileAction({
    id: "soca_tail_log_file",
    button: {
        name: "Tail File",
        toolbar: false,
        contextMenu: true,
        icon: faTerminal,
    },
});

const ACTIONS = [ChonkyActions.OpenFiles, ChonkyActions.UploadFiles, ChonkyActions.CreateFolder, ChonkyActions.DeleteFiles, ChonkyActions.CopyFiles, ChonkyActions.DownloadFiles, CustomActionFavorite, CustomActionRefresh, CustomActionTailLogFile];

const FAVORITE_ACTIONS = [ChonkyActions.OpenFiles, CustomActionRemoveFavorite];

class IdeaFileEditorModal extends Component<IdeaFileEditorProps, IdeaFileEditorState> {
    onSaveTimeout: any | null = null;

    constructor(props: IdeaFileEditorProps) {
        super(props);
        this.state = {
            ace: undefined,
            preferences: undefined,
            filepath: this.props.filepath ? this.props.filepath : "",
            content: this.props.content ? this.props.content : "",
            language: this.props.language ? this.props.language : "text",
            onSaveMessage: null,
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
    }

    setContent(filepath: string, content: string) {
        this.setState({
            filepath: filepath,
            content: content,
        });
    }

    setLangauge(language: CodeEditorProps.Language) {
        this.setState({
            language: language,
        });
    }

    render() {
        const showStatus = (success: boolean, errorMessage?: string) => {
            if (this.onSaveTimeout) {
                clearTimeout(this.onSaveTimeout);
            }
            this.setState(
                {
                    onSaveMessage: success ? <StatusIndicator type="success">File saved successfully</StatusIndicator> : <StatusIndicator type="error">Failed to save file: {errorMessage}</StatusIndicator>,
                },
                () => {
                    this.onSaveTimeout = setTimeout(() => {
                        this.setState({
                            onSaveMessage: null,
                        });
                    }, 10000);
                }
            );
        };

        return (
            <Modal
                visible={this.props.show}
                onDismiss={this.props.onClose}
                size="max"
                header={<small>{this.state.filepath}</small>}
                footer={
                    <div>
                        <Box>{this.state.onSaveMessage && this.state.onSaveMessage}</Box>
                        <Box float="right">
                            <SpaceBetween size="xs" direction="horizontal">
                                <Button variant="normal" onClick={this.props.onClose}>
                                    Cancel
                                </Button>
                                <Button
                                    variant="primary"
                                    onClick={() => {
                                        this.props
                                            .onSave(this.state.filepath, this.state.content)
                                            .then((status) => {
                                                showStatus(true);
                                            })
                                            .catch((error) => {
                                                if (error.errorCode === ErrorCodes.UNAUTHORIZED_ACCESS) {
                                                    showStatus(false, ErrorMessages.PERMISSION_DENIED);
                                                } else if (error.errorCode === ErrorCodes.DISABLED_FEATURE) {
                                                    showStatus(false, ErrorMessages.DISABLED_FILE_BROWSER_BY_ADMIN);
                                                }
                                                else {
                                                    showStatus(false, error.message);
                                                }
                                            });
                                    }}
                                >
                                    Save
                                </Button>
                            </SpaceBetween>
                        </Box>
                    </div>
                }
            >
                <CodeEditor
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
            </Modal>
        );
    }
}

const FILE_BROWSER_API_PATH = "/cluster-manager/api/v1";

class IdeaFileBrowser extends Component<IdeaFileBrowserProps, IdeaFileBrowserState> {
    fileEditor: RefObject<IdeaFileEditorModal>;
    _fileBrowserClient: FileBrowserClient;
    _clusterSettingsClient: ClusterSettingsClient;
    createFolderForm: RefObject<IdeaForm>;
    deleteFileConfirmModal: RefObject<IdeaConfirm>;
    localStorage: LocalStorageService;

    constructor(props: IdeaFileBrowserProps) {
        super(props);

        const localStoragePrefix = (): string => {
            const appContext = AppContext.get();
            return `${appContext.getAwsRegion()}/${appContext.getClusterName()}/${appContext.auth().getUsername()}`;
        };

        this.fileEditor = React.createRef();
        this.localStorage = new LocalStorageService({
            prefix: localStoragePrefix(),
        });
        this.state = {
            files: [],
            favorites: [],
            folderChain: [],
            editorOpen: false,
            fileUploadResult: null,
            activeTabId: "files",
            downloadPemLoading: false,
            downloadPpkLoading: false,
            sshHostIp: "",
            sshAccess: false,
            isFileBrowserEnabled: false,
            isLoading: true,
            fileTransferMethod: "file-zilla",
            filesToDelete: [],
            showDeleteConfirmModal: false,
        };
        this._fileBrowserClient = AppContext.get().client().fileBrowser();
        this._clusterSettingsClient = AppContext.get().client().clusterSettings();
        this.createFolderForm = React.createRef();
        this.deleteFileConfirmModal = React.createRef();
    }

    getCreateFolderForm(): IdeaForm {
        return this.createFolderForm.current!;
    }

    adjustFileBrowserHeight() {
        setTimeout(() => {
            let fileBrowsers = document.getElementsByClassName("soca-file-browser");
            for (let i = 0; i < fileBrowsers.length; i++) {
                let fileBrowser = fileBrowsers[i];
                fileBrowser.setAttribute("style", `height: 100vh`);
            }
        }, 100);
    }

    setFlashbarMessage(type: FlashbarProps.Type, content: string, header?: React.ReactNode, action?: React.ReactNode) {
        this.props.onFlashbarChange({
          items: [
            {
              type,
              header,
              content,
              action,
              dismissible: true,
            }
          ]
        })
    }

    componentDidMount() {
        AppContext.get()
            .getClusterSettingsService()
            .getModuleSettings(Constants.MODULE_BASTION_HOST)
            .then((moduleInfo) => {
                this.setState({
                    sshHostIp: Utils.asString(moduleInfo.public_ip),
                    sshAccess: true,
                });
            })
            .catch((error) => {
                if (error.errorCode === ErrorCodes.MODULE_NOT_FOUND) {
                    this.setState({
                        sshAccess: false,
                    });
                }
            });
        const cwd = this.props.searchParams.get("cwd");
        this.listFiles(cwd ? cwd : undefined)
            .catch((error) => {
                if (error.errorCode === ErrorCodes.DISABLED_FEATURE) {
                    this.setFlashbarMessage("error", ErrorMessages.DISABLED_FILE_BROWSER_BY_ADMIN);
                    this.setState({
                        isFileBrowserEnabled: false,
                    });
                }
                if (error.errorCode === ErrorCodes.UNAUTHORIZED_ACCESS) {
                    this.setFlashbarMessage("error", ErrorMessages.DISABLED_FILE_BROWSER_NEW_USER);
                    this.setState({
                        isFileBrowserEnabled: false,
                    });
                }
            })
            .finally( () => {
                    this.setState({
                        isLoading: false,
                    },
                    () => {
                        this.adjustFileBrowserHeight();
                        this.listFavorites();
                    });
                }
            );
    }

    componentWillUnmount() {
        let appContent = document.getElementsByClassName("soca-app-content")[0];
        appContent.removeAttribute("style");
    }

    fileBrowserClient(): FileBrowserClient {
        return this._fileBrowserClient;
    }

    clusterSettingsClient(): ClusterSettingsClient {
        return this._clusterSettingsClient;
    }

    convert(payload?: ListFilesResult, cwd?: string): FileData[] {
        if (payload?.listing == null) {
            return [];
        }
        const files: any = [];
        payload.listing.forEach((entry) => {
            const notSlashInternal: boolean = !(entry.name === "internal" && cwd === "/");
            if(notSlashInternal) {
                files.push({
                    id: entry.file_id,
                    name: entry.name,
                    isDir: entry.is_dir,
                    isHidden: entry.is_hidden,
                    modDate: entry.mod_date,
                    size: entry.size,
                });
            }
        });
        return files;
    }

    buildFolderChain(cwd: string): FileData[] {
        const tokens = cwd.split("/");
        const result: FileData[] = [];
        let index = 0;
        result.push({ id: "root", name: "root", isDir: true, folderChain: true,  openable: false, index: index++ });
        tokens.forEach((token) => {
            if (Utils.isEmpty(token)) {
                return true;
            }
            result.push({ id: token, name: token, isDir: true, folderChain: true, index: index++ });
        });
        return result;
    }

    getCwd(index: number): string {
        const tokens: string[] = [];
        const folderChain = this.state.folderChain;
        if (index === 0) {
            return "/";
        }
        for (let i = 1; i < folderChain.length; i++) {
            const entry = folderChain[i];
            tokens.push(entry.name);
            if (index === entry.index) {
                break;
            }
        }
        return "/" + tokens.join("/");
    }

    listFiles(cwd?: string): Promise<boolean> {
        return this.fileBrowserClient()
            .listFiles({
                cwd: cwd,
            })
            .then((result: ListFilesResult) => {
                this.props.searchParams.set("cwd", result.cwd!);
                this.props.setSearchParams(this.props.searchParams);
                this.setState({
                    files: this.convert(result, result.cwd),
                    folderChain: this.buildFolderChain(result.cwd!),
                    isFileBrowserEnabled: true,
                });
            })
            .then(() => {
                return true;
            });
    }

    listFavorites() {
        const favorites = this.localStorage.getItem("favorites");
        if (favorites == null) {
            this.setState({
                favorites: [],
            });
            return;
        }
        const files = JSON.parse(favorites);
        this.setState({
            favorites: files,
        });
    }

    addFavorite(file: FileData) {
        const favorites = [...this.state.favorites];
        const path = `${this.getCwd(-1)}/${file.name}`;
        const parent = path.substring(0, path.lastIndexOf("/"));
        const favorite = {
            id: file.id,
            name: `(${parent}) ${file.name}`,
            isDir: file.isDir,
            size: file.size,
            modDate: file.modDate,
            path: path,
        };
        const found = favorites.find((file) => file.path === path);
        if (found == null) {
            favorites.push(favorite);
            this.localStorage.setItem("favorites", JSON.stringify(favorites));
            this.setState({
                favorites: favorites,
            });
        }
    }

    removeFavorite(file: FileData) {
        const favorites = [...this.state.favorites];
        for (let i = 0; i < favorites.length; i++) {
            let favorite = favorites[i];
            if (favorite.path === file.path) {
                favorites.splice(i, 1);
                this.localStorage.setItem("favorites", JSON.stringify(favorites));
                this.setState({
                    favorites: favorites,
                });
                break;
            }
        }
    }

    getFilePath(file: FileData): string {
        let path = file.path;
        if (path == null) {
            let cwd = this.getCwd(-1);
            if (cwd === "/") {
                path = "/" + file.name;
            } else {
                path = cwd + "/" + file.name;
            }
        }
        return path;
    }

    downloadFiles(files: FileData[]) {
        const download = (file: string) => {
            const tokens = file.split("/");
            const fileName = tokens[tokens.length - 1];
            const fileBrowserEndpointUrl = AppContext.get().client().fileBrowser().getEndpointUrl();
            const url = `${fileBrowserEndpointUrl}/download?file=${file}`;
            AppContext.get()
                .auth()
                .getAccessToken()
                .then((accessToken) => {
                    fetch(url, {
                        headers: {
                            Authorization: `Bearer ${accessToken}`,
                        },
                    })
                        .then((response) => {
                            return response.blob();
                        })
                        .then((blob) => {
                            const url = window.URL.createObjectURL(new Blob([blob]));
                            const link = document.createElement("a");
                            link.href = url;
                            link.setAttribute("download", fileName);
                            document.body.appendChild(link);
                            link.click();
                            document.body.removeChild(link);
                        });
                });
        };

        if (files.length === 1) {
            this.clusterSettingsClient()
                .getModuleSettings({module_id: Constants.MODULE_SHARED_STORAGE})
                .then((sharedStorageSettings) => {
                    if (dot.pick(Constants.SHARED_STORAGE_FILE_BROWSER_KEY, sharedStorageSettings.settings)) {
                        download(this.getFilePath(files[0]));
                    } else {
                        this.setFlashbarMessage("error", ErrorMessages.DISABLED_FILE_BROWSER_BY_ADMIN);
                        this.setState({
                            isFileBrowserEnabled: false,
                        });
                    }
                });
        } else {
            const file_paths: string[] = [];
            files.forEach((file) => file_paths.push(this.getFilePath(file)));
            this.fileBrowserClient()
                .downloadFiles({
                    files: file_paths,
                })
                .catch((error) => {
                    if (error.errorCode === ErrorCodes.DISABLED_FEATURE) {
                        this.setFlashbarMessage("error", ErrorMessages.DISABLED_FILE_BROWSER_BY_ADMIN);
                        this.setState({
                            isFileBrowserEnabled: false,
                        });
                    } else {
                        this.setFlashbarMessage("error", error.message);
                    }
                })
                .then((result) => {
                    download(result?.download_url!);
                });
        }
    }

    onOpenSelection(payload?: FileData) {
        if (payload == null) {
            return;
        }
        if (payload.folderChain) {
            this.listFiles(this.getCwd(payload.index))
                .catch((error) => {
                    if (error.errorCode === ErrorCodes.DISABLED_FEATURE) {
                        this.setFlashbarMessage("error", ErrorMessages.DISABLED_FILE_BROWSER_BY_ADMIN);
                        this.setState({
                            isFileBrowserEnabled: false,
                        });
                    } else {
                        this.setFlashbarMessage("error", error.message);
                    }
                })
                .finally();
        } else if (payload.isDir) {
            let cwd = this.getCwd(-1);
            let targetDir = "";
            if (cwd === "/") {
                targetDir = "/" + payload.name;
            } else {
                targetDir = cwd + "/" + payload.name;
            }
            this.listFiles(targetDir)
                .catch((error) => {
                    if (error.errorCode === ErrorCodes.DISABLED_FEATURE) {
                        this.setFlashbarMessage("error", ErrorMessages.DISABLED_FILE_BROWSER_BY_ADMIN);
                        this.setState({
                            isFileBrowserEnabled: false,
                        });
                    } else {
                        this.setFlashbarMessage("error", error.message);
                    }
                })
                .finally();
        } else {
            this.openFile(payload);
        }
    }

    onOpenFavorite(payload?: FileData) {
        if (payload == null) {
            return;
        }
        if (payload.isDir) {
            this.listFiles(payload.path)
            .catch((error) => {
                if (error.errorCode === ErrorCodes.DISABLED_FEATURE) {
                    this.setFlashbarMessage("error", ErrorMessages.DISABLED_FILE_BROWSER_BY_ADMIN);
                    this.setState({
                        isFileBrowserEnabled: false,
                    });
                } else {
                    this.setFlashbarMessage("error", error.message);
                }
            })
            .then(() => {
                this.setState(
                    {
                        activeTabId: "files",
                    },
                    () => {
                        this.adjustFileBrowserHeight();
                    }
                );
            });
        } else {
            this.openFile(payload);
        }
    }

    buildFileEditor() {
        return (
            <IdeaFileEditorModal
                ref={this.fileEditor}
                show={this.state.editorOpen}
                onSave={(file: string, content: string) => {
                    return this.fileBrowserClient()
                        .saveFile({
                            file: file,
                            content: btoa(content),
                        })
                        .then(() => {
                            return true;
                        });
                }}
                onClose={() => {
                    this.setState({
                        editorOpen: false,
                    });
                }}
            />
        );
    }

    openFile(file: FileData) {
        const path = this.getFilePath(file);
        this.fileBrowserClient()
            .readFile({
                file: path,
            })
            .then((result) => {
                this.fileEditor.current?.setContent(path, atob(result.content!));
                this.fileEditor.current?.setLangauge("text");
                this.setState({
                    editorOpen: true,
                });
            })
            .catch((error) => {
                if (error.errorCode === ErrorCodes.NOT_A_TEXT_FILE) {
                    this.downloadFiles([file]);
                } else if (error.errorCode === ErrorCodes.DISABLED_FEATURE) {
                    this.setFlashbarMessage("error", ErrorMessages.DISABLED_FILE_BROWSER_BY_ADMIN);
                    this.setState({
                        isFileBrowserEnabled: false,
                    });
                } else {
                    this.setFlashbarMessage("error", error.message);
                }
            });
    }

    showUploadModal() {
        AppContext.get()
            .auth()
            .getAccessToken()
            .then((accessToken) => {
                const httpEndpoint = AppContext.get().getHttpEndpoint();
                const uppy = new Uppy()
                    .use(Dashboard, {
                        animateOpenClose: false,
                        closeModalOnClickOutside: true,
                        browserBackButtonClose: true,
                        proudlyDisplayPoweredByUppy: false,
                        fileManagerSelectionType: "both",
                        theme: AppContext.get().isDarkMode() ? "dark" : "light",
                    })
                    .use(XHRUpload, {
                        endpoint: `${httpEndpoint}${FILE_BROWSER_API_PATH}/upload?cwd=${this.getCwd(-1)}`,
                        headers: {
                            Authorization: `Bearer ${accessToken}`,
                        },
                        formData: true,
                        fieldName: "files[]",
                        method: "PUT",
                        bundle: true,
                        responseType: "text",
                        validateStatus(statusCode, responseText, response) {
                            return JSON.parse(responseText).success
                        },
                        getResponseError(responseText, xhr) {
                            return JSON.parse(responseText)
                        },
                    });
                const dashboard: Dashboard = uppy.getPlugin("Dashboard")!;
                dashboard.openModal();
                uppy.on("upload-error", (file, error : any) => {
                    if (error.error_code === ErrorCodes.DISABLED_FEATURE) {
                        this.setFlashbarMessage("error", ErrorMessages.DISABLED_FILE_BROWSER_BY_ADMIN);
                        this.setState({
                            isFileBrowserEnabled: false,
                        });
                        dashboard.closeModal();
                    } else {
                        this.setFlashbarMessage("error", error.error_code);
                    }
                });
                uppy.on("complete", () => {
                    this.listFiles(this.getCwd(-1)).finally();
                });
            });
    }

    buildCreateFolderForm() {
        return (
            <IdeaForm
                ref={this.createFolderForm}
                name="create-folder"
                modal={true}
                modalSize="medium"
                title="Create New Folder"
                onSubmit={() => {
                    if (!this.getCreateFolderForm().validate()) {
                        return;
                    }
                    const values = this.getCreateFolderForm().getValues();
                    this.fileBrowserClient()
                        .createFile({
                            cwd: this.getCwd(-1),
                            filename: values.name,
                            is_folder: true,
                        })
                        .then(() => {
                            this.listFiles(this.getCwd(-1)).finally();
                            this.getCreateFolderForm().hideModal();
                        })
                        .catch((error) => {
                            if (error.errorCode === ErrorCodes.DISABLED_FEATURE) {
                                this.getCreateFolderForm().setError(error.errorCode, ErrorMessages.DISABLED_FILE_BROWSER_BY_ADMIN);
                                this.setFlashbarMessage("error", ErrorMessages.DISABLED_FILE_BROWSER_BY_ADMIN);
                                this.setState({
                                    isFileBrowserEnabled: false,
                                });
                            } else {
                                this.getCreateFolderForm().setError(error.errorCode, error.message);
                            }
                        });
                }}
                params={[
                    {
                        name: "name",
                        title: "Folder Name",
                        description: "Enter the name of the folder",
                        data_type: "str",
                        param_type: "text",
                        validate: {
                            required: true,
                        },
                    },
                ]}
            />
        );
    }

    getDeleteFileConformModal(): IdeaConfirm {
        return this.deleteFileConfirmModal.current!;
    }

    buidlDeleteFileConfirmModal() {
        return (
            <IdeaConfirm
                ref={this.deleteFileConfirmModal}
                title={"Delete File(s)"}
                onCancel={() => {
                    this.setState({
                        filesToDelete: [],
                        showDeleteConfirmModal: false,
                    });
                }}
                onConfirm={() => {
                    const toDelete: string[] = [];
                    this.state.filesToDelete.forEach((file) => {
                        toDelete.push(`${this.getCwd(-1)}/${file.name}`);
                    });
                    this.fileBrowserClient()
                        .deleteFiles({
                            files: toDelete,
                        })
                        .then(() => {
                            this.listFiles(this.getCwd(-1))
                            .catch((error) => {
                                if (error.errorCode === ErrorCodes.DISABLED_FEATURE) {
                                    this.setFlashbarMessage("error", ErrorMessages.DISABLED_FILE_BROWSER_BY_ADMIN);
                                    this.setState({
                                        isFileBrowserEnabled: false,
                                    });
                                } else {
                                    this.setFlashbarMessage("error", error.message);
                                }
                            })
                            .finally();
                        })
                        .catch((error) => {
                            if (error.errorCode === ErrorCodes.UNAUTHORIZED_ACCESS) {
                                this.setFlashbarMessage("error", "Permission denied");
                            } else if (error.errorCode === ErrorCodes.DISABLED_FEATURE) {
                                this.setFlashbarMessage("error", ErrorMessages.DISABLED_FILE_BROWSER_BY_ADMIN);
                                this.setState({
                                    isFileBrowserEnabled: false,
                                });
                            } 
                            else {
                                this.setFlashbarMessage("error", error.message);
                            }
                        });
                }}
            >
                <p>Are you sure you want to delete the following Files? </p>
                {this.state.filesToDelete.map((file, index) => {
                    return <li key={index}>{file.name}</li>;
                })}
            </IdeaConfirm>
        );
    }

    deleteFiles(files: FileData[]) {
        this.setState(
            {
                filesToDelete: files,
                showDeleteConfirmModal: true,
            },
            () => {
                this.getDeleteFileConformModal().show();
            }
        );
    }

    onDownloadPrivateKey = (keyFormat: "pem" | "ppk") => {
        const state: any = {};
        if (keyFormat === "pem") {
            state.downloadPemLoading = true;
        } else if (keyFormat === "ppk") {
            state.downloadPpkLoading = true;
        }
        this.setState(state, () => {
            AppContext.get()
                .auth()
                .downloadPrivateKey(keyFormat)
                .finally(() => {
                    const state: any = {};
                    if (keyFormat === "pem") {
                        state.downloadPemLoading = false;
                    } else if (keyFormat === "ppk") {
                        state.downloadPpkLoading = false;
                    }
                    this.setState(state);
                });
        });
    };

    render() {
        const getPath = (fileName: string): string => {
            return `${this.getCwd(-1)}/${fileName}`;
        };

        const getFileBrowserActions = () => {
            let actions = [...ACTIONS];
            if (AppContext.get().getClusterSettingsService().isSchedulerDeployed()) {
                actions.push(CustomActionSubmitJob);
            }
            return actions;
        };

        const getFavoriteActions = () => {
            let actions = [...FAVORITE_ACTIONS];
            if (AppContext.get().getClusterSettingsService().isSchedulerDeployed()) {
                actions.push(CustomActionSubmitJob);
            }
            return actions;
        };

        const buildLoadingContent = () => {
            return (
                <div style={{ marginTop: "20px" }}>
                    <Box variant="p" textAlign="center">
                        <StatusIndicator type="loading"/>
                    </Box>
                </div>
            )
        }

        const buildDisabledPageContent = () => {
            return (
                <Box textAlign="center" variant="p" color="text-body-secondary" padding={{ top: "xxxl", bottom: "s" }}>
                    <b>No access to files.</b>
                    <br/>File access has been disabled.
                </Box>
            )
        }

        const buildFileBrowserContent = () => {
            return (
            <div style={{ marginTop: "20px" }}>
                {this.state.showDeleteConfirmModal && this.buidlDeleteFileConfirmModal()}
                {this.buildCreateFolderForm()}
                {this.buildFileEditor()}
                {/*<Container>*/}
                <Tabs
                    onChange={(event) => {
                        this.setState(
                            {
                                activeTabId: event.detail.activeTabId,
                            },
                            () => {
                                this.adjustFileBrowserHeight();
                            }
                        );
                    }}
                    activeTabId={this.state.activeTabId}
                    tabs={[
                        {
                            id: "files",
                            label: "My Files",
                            content: (
                                <Container disableContentPaddings={true}>
                                    <div className="soca-file-browser" style={{ height: "100vh - 200px" }}>
                                        <FileBrowser
                                            darkMode={AppContext.get().isDarkMode()}
                                            folderChain={this.state.folderChain}
                                            files={this.state.files}
                                            fileActions={getFileBrowserActions()}
                                            disableDragAndDrop={true}
                                            onFileAction={(event) => {
                                                const eventId: string = event.id;
                                                if (event.id === ChonkyActions.OpenFiles.id) {
                                                    this.onOpenSelection(event.payload.targetFile);
                                                } else if (event.id === ChonkyActions.UploadFiles.id) {
                                                    this.showUploadModal();
                                                } else if (event.id === ChonkyActions.DownloadFiles.id) {
                                                    this.downloadFiles(event.state.selectedFiles);
                                                } else if (event.id === ChonkyActions.CreateFolder.id) {
                                                    this.getCreateFolderForm().showModal();
                                                } else if (event.id === ChonkyActions.DeleteFiles.id) {
                                                    this.deleteFiles(event.state.selectedFiles);
                                                } else if (event.id === ChonkyActions.CopyFiles.id) {
                                                    if (event.state.selectedFiles && event.state.selectedFiles.length > 0) {
                                                        const name = event.state.selectedFiles[0].name;
                                                        const path = getPath(name);
                                                        Utils.copyToClipBoard(path).then((status) => {
                                                            if (status) {
                                                                this.setFlashbarMessage("info", `${name} path copied to clipboard`);
                                                            }
                                                        });
                                                    }
                                                } else if (eventId === "soca_refresh") {
                                                    this.listFiles(this.getCwd(-1))
                                                    .catch((error) => {
                                                        if (error.errorCode === ErrorCodes.DISABLED_FEATURE) {
                                                            this.setFlashbarMessage("error", ErrorMessages.DISABLED_FILE_BROWSER_BY_ADMIN);
                                                            this.setState({
                                                                isFileBrowserEnabled: false,
                                                            });
                                                        } else {
                                                            this.setFlashbarMessage("error", error.message);
                                                        }
                                                    })
                                                    .finally();
                                                } else if (eventId === "soca_submit_job") {
                                                    if (event.state.selectedFiles && event.state.selectedFiles.length > 0) {
                                                        this.props.navigate(`/soca/jobs/submit-job?input_file=${this.getCwd(-1)}/${event.state.selectedFiles[0].name}`);
                                                    }
                                                } else if (eventId === "soca_favorite") {
                                                    if (event.state.selectedFiles && event.state.selectedFiles.length > 0) {
                                                        event.state.selectedFiles.forEach((file) => this.addFavorite(file));
                                                    }
                                                } else if (eventId === "soca_tail_log_file") {
                                                    if (event.state.selectedFiles && event.state.selectedFiles.length > 0) {
                                                        this.listFiles(this.getCwd(-1))
                                                        .then(() => {
                                                            Utils.openNewTab(`/#/home/file-browser/tail?file=${this.getCwd(-1)}/${event.state.selectedFiles[0].name}&cwd=${this.getCwd(-1)}`);
                                                        })
                                                        .catch((error) => {
                                                            if (error.errorCode === ErrorCodes.DISABLED_FEATURE) {
                                                                this.setFlashbarMessage("error", ErrorMessages.DISABLED_FILE_BROWSER_BY_ADMIN);
                                                                this.setState({
                                                                    isFileBrowserEnabled: false,
                                                                });
                                                            } else {
                                                                this.setFlashbarMessage("error", error.message);
                                                            }
                                                        })
                                                    }
                                                }
                                            }}
                                            defaultFileViewActionId={ChonkyActions.EnableListView.id}
                                            disableDefaultFileActions={[ChonkyActions.CopyFiles.id, ChonkyActions.ToggleHiddenFiles.id, ChonkyActions.ToggleShowFoldersFirst.id]}
                                        >
                                            <FileNavbar />
                                            <FileToolbar />
                                            <FileList />
                                            <FileContextMenu />
                                        </FileBrowser>
                                    </div>
                                </Container>
                            ),
                        },
                        {
                            id: "favorites",
                            label: "Favorites",
                            content: (
                                <Container disableContentPaddings={true}>
                                    <div className="soca-file-browser" style={{ height: "100vh - 200px" }}>
                                        <FileBrowser
                                            darkMode={AppContext.get().isDarkMode()}
                                            folderChain={this.state.folderChain}
                                            files={this.state.favorites}
                                            fileActions={getFavoriteActions()}
                                            disableDragAndDrop={true}
                                            onFileAction={(event) => {
                                                const eventId: string = event.id;
                                                if (event.id === ChonkyActions.OpenFiles.id) {
                                                    this.onOpenFavorite(event.payload.targetFile);
                                                } else if (eventId === "soca_submit_job") {
                                                    const targetFile = event.state.selectedFiles[0];
                                                    this.props.navigate(`/soca/jobs/submit-job?input_location=${targetFile.path}`);
                                                } else if (eventId === "soca_remove_favorite") {
                                                    if (event.state.selectedFiles && event.state.selectedFiles.length > 0) {
                                                        event.state.selectedFiles.forEach((file) => this.removeFavorite(file));
                                                    }
                                                }
                                            }}
                                            defaultFileViewActionId={ChonkyActions.EnableListView.id}
                                            disableDefaultFileActions={[ChonkyActions.CopyFiles.id, ChonkyActions.ToggleHiddenFiles.id, ChonkyActions.ToggleShowFoldersFirst.id]}
                                        >
                                            <FileToolbar />
                                            <FileList />
                                            <FileContextMenu />
                                        </FileBrowser>
                                    </div>
                                </Container>
                            ),
                        },
                        {
                            id: "file-transfer",
                            label: "File Transfer",
                            disabled: !this.state.sshAccess,
                            content: (
                                <SpaceBetween size={"s"}>
                                    <Container>
                                        <b>File Transfer Method</b>
                                        <br />
                                        <p>We recommend using below methods to transfer large files to your RES environment. Select an option below.</p>
                                        <Tiles
                                            value={this.state.fileTransferMethod}
                                            columns={3}
                                            items={[
                                                {
                                                    label: <b>FileZilla</b>,
                                                    description: "Available for download on Windows, MacOS and Linux",
                                                    value: "file-zilla",
                                                },
                                                {
                                                    label: <b>WinSCP</b>,
                                                    description: "Available for download on Windows Only",
                                                    value: "winscp",
                                                },
                                                {
                                                    label: <b>AWS Transfer</b>,
                                                    description: "Your RES environment must be using Amazon EFS to use AWS Transfer",
                                                    value: "aws-transfer",
                                                },
                                            ]}
                                            onChange={(event) => {
                                                this.setState({
                                                    fileTransferMethod: event.detail.value,
                                                });
                                            }}
                                        />
                                    </Container>
                                    {this.state.fileTransferMethod === "file-zilla" && (
                                        <Container header={<Header variant={"h3"}>FileZilla</Header>}>
                                            <SpaceBetween size={"s"}>
                                                <Box>
                                                    <h2>Step 1: Download FileZilla</h2>
                                                    <ul>
                                                        <li>
                                                            <Link external={true} href={"https://filezilla-project.org/download.php?platform=osx"}>
                                                                Download FileZilla (MacOS)
                                                            </Link>
                                                        </li>
                                                        <li>
                                                            <Link external={true} href={"https://filezilla-project.org/download.php?platform=win64"}>
                                                                Download FileZilla (Windows)
                                                            </Link>
                                                        </li>
                                                        <li>
                                                            <Link external={true} href={"https://filezilla-project.org/download.php?platform=linux"}>
                                                                Download FileZilla (Linux)
                                                            </Link>
                                                        </li>
                                                    </ul>
                                                </Box>
                                                <Box>
                                                    <h2>Step 2: Download Key File</h2>
                                                    <SpaceBetween size={"l"} direction={"horizontal"}>
                                                        <Button variant={"normal"} onClick={() => this.onDownloadPrivateKey("pem")} loading={this.state.downloadPemLoading}>
                                                            <FontAwesomeIcon icon={faDownload} /> Download Key File [*.pem] (MacOS / Linux)
                                                        </Button>
                                                        <Button variant={"normal"} onClick={() => this.onDownloadPrivateKey("ppk")} loading={this.state.downloadPpkLoading}>
                                                            <FontAwesomeIcon icon={faDownload} /> Download Key File [*.ppk] (Windows)
                                                        </Button>
                                                    </SpaceBetween>
                                                </Box>
                                                <Box>
                                                    <h2>Step 3: Configure FileZilla</h2>
                                                    <p>
                                                        Open FileZilla and select <b>File &gt; Site Manager</b> to create a new Site using below options:
                                                    </p>
                                                    <Container>
                                                        <ColumnLayout columns={2}>
                                                            <KeyValue title="Host" value={this.state.sshHostIp} />
                                                            <KeyValue title="Port" value={"22"} />
                                                            <KeyValue title="Protocol" value={"SFTP"} />
                                                            <KeyValue title="Logon Type" value={"Key File"} />
                                                            <KeyValue title="User" value={AppContext.get().auth().getUsername()} />
                                                            <KeyValue title="Key File" value={"/path/to/key-file (downloaded in Step 2)"} />
                                                        </ColumnLayout>
                                                    </Container>
                                                    <p>
                                                        <b>Save</b> the settings and click <b>Connect</b>
                                                    </p>
                                                </Box>
                                                <Box>
                                                    <h2>Step 4: Connect and transfer file to FileZilla</h2>
                                                    <p>During your first connection, you will be asked whether or not you want to trust {this.state.sshHostIp}. Check "Always Trust this Host" and Click "Ok".</p>
                                                    <p>Once connected, simply drag & drop to upload/download files.</p>
                                                </Box>
                                            </SpaceBetween>
                                        </Container>
                                    )}
                                    {this.state.fileTransferMethod === "winscp" && (
                                        <Container header={<Header variant={"h3"}>WinSCP (Windows)</Header>}>
                                            <SpaceBetween size={"s"}>
                                                <Box>
                                                    <Alert onDismiss={() => false} dismissAriaLabel="Close alert" header="Info">
                                                        WinSCP is only available on Windows. Please use alternate methods (FileZilla, AWS FTP) if you are running Linux/Mac clients.
                                                    </Alert>
                                                    <h2>Step 1: Download WinSCP</h2>
                                                    <ul>
                                                        <li>
                                                            <Link external={true} href={"https://winscp.net/eng/download.php"}>
                                                                Download WinSCP (Windows)
                                                            </Link>
                                                        </li>
                                                    </ul>
                                                </Box>
                                                <Box>
                                                    <h2>Step 2: Download Key File</h2>
                                                    <SpaceBetween size={"l"} direction={"horizontal"}>
                                                        <Button variant={"normal"} onClick={() => this.onDownloadPrivateKey("pem")} loading={this.state.downloadPemLoading}>
                                                            <FontAwesomeIcon icon={faDownload} /> Download Key File [*.pem] (MacOS / Linux)
                                                        </Button>
                                                        <Button variant={"normal"} onClick={() => this.onDownloadPrivateKey("ppk")} loading={this.state.downloadPpkLoading}>
                                                            <FontAwesomeIcon icon={faDownload} /> Download Key File [*.ppk] (Windows)
                                                        </Button>
                                                    </SpaceBetween>
                                                </Box>
                                                <Box>
                                                    <h2>Step 3: Configure WinSCP</h2>
                                                    <p>
                                                        Open WinSCP and select <b>File &gt; Site Manager</b> to create a new Site using below options:
                                                    </p>
                                                    <Container>
                                                        <ColumnLayout columns={2}>
                                                            <KeyValue title="Host Name" value={this.state.sshHostIp} />
                                                            <KeyValue title="Port Number" value={"22"} />
                                                            <KeyValue title="File Protocol" value={"SFTP"} />
                                                            <KeyValue title="Logon Type" value={"Key File"} />
                                                            <KeyValue title="User Name" value={AppContext.get().auth().getUsername()} />
                                                            <KeyValue title="Password" value={"Leave Blank and click Advanced. Click SSH > Authentication Page and load your key under Private Key File."} />

                                                            <KeyValue title="Key File" value={"/path/to/key-file (downloaded in Step 2)"} />
                                                        </ColumnLayout>
                                                    </Container>
                                                    <p>
                                                        <b>Save</b> the settings and click <b>Connect</b>
                                                    </p>
                                                </Box>
                                                <Box>
                                                    <h2>Step 4: Connect and transfer file to WinSCP</h2>
                                                    <p>During your first connection, you will be asked whether or not you want to trust {this.state.sshHostIp}. Check "Always Trust this Host" and Click "Ok".</p>
                                                    <p>Once connected, simply drag & drop to upload/download files.</p>
                                                </Box>
                                            </SpaceBetween>
                                        </Container>
                                    )}
                                    {this.state.fileTransferMethod === "aws-transfer" && (
                                        <Container header={<Header variant={"h3"}>AWS Transfer</Header>}>
                                            <SpaceBetween size={"s"}>
                                                <Box>
                                                    <Alert onDismiss={() => false} dismissAriaLabel="Close alert" header="Limitations">
                                                        Your RES environment must be using Amazon EFS to use AWS Transfer
                                                    </Alert>
                                                    <h2>Step 1: Configure AWS Transfer</h2>
                                                    <ul>
                                                        <li>
                                                            Open AWS Console and navigate to the service named <b>AWS Transfer Family</b> then click <b>Create Server</b>
                                                        </li>
                                                        <li>
                                                            Select <b>SFTP (SSH File Transfer Protocol) - file transfer over Secure Shell</b>
                                                        </li>
                                                        <li>
                                                            Select <b>Service Managed</b> as identity provider
                                                        </li>
                                                        <li>
                                                            Choose <b>Endpoint type</b> depending on your setup. It's recommended to use <b>VPC hosted</b> for IP restrictions via your security groups. <b>Publicly accessible</b> means your AWS Transfer endpoint won't be protected by IP safelist.
                                                        </li>
                                                        <li>
                                                            Select <b>Amazon EFS</b> as Domain
                                                        </li>
                                                        <li>
                                                            Select <b>Create a new role</b> and use the latest <b>TransferSecurityPolicy</b> available
                                                        </li>
                                                        . Leave everything else as default.
                                                        <li>
                                                            In the <b>Review and create</b> section click <b>Create server</b>
                                                        </li>
                                                    </ul>

                                                    <h2>Step 2: Create IAM role for your AWS Transfer Users</h2>
                                                    <ul>
                                                        <li>
                                                            Open AWS Console and navigate to the service named <b>IAM</b> then click <b>Roles</b> on the left sidebar and finally click <b>Create Role</b>
                                                        </li>
                                                        <li>
                                                            Select <b>AWS Service</b> as Trusted Entity Type and select <b>Transfer</b> as Use Case
                                                        </li>
                                                        <li>
                                                            Select the AWS managed policy named <b>AmazonElasticFileSystemClientReadWriteAccess</b>
                                                        </li>
                                                        <li>
                                                            Select a Role name (for example <b>TransferEFSClient</b> and save it
                                                        </li>
                                                    </ul>

                                                    <h2>Step 3: Download PEM Key File (Public)</h2>
                                                    <ul>
                                                        <li>
                                                            Download your <b>public</b> SSH key. You can retrieve it under <b>$HOME/.ssh/id_rsa.pub</b>
                                                        </li>
                                                    </ul>

                                                    <h2>Step 4: Download your PEM key File (Private)</h2>
                                                    <SpaceBetween size={"l"} direction={"horizontal"}>
                                                        <Button variant={"normal"} onClick={() => this.onDownloadPrivateKey("pem")} loading={this.state.downloadPemLoading}>
                                                            <FontAwesomeIcon icon={faDownload} /> Download Key File [*.pem] (MacOS / Linux)
                                                        </Button>
                                                    </SpaceBetween>

                                                    <h2>Step 5: Register your AWS Transfer Users</h2>
                                                    <Alert onDismiss={() => false} dismissAriaLabel="Close alert" header="User Information">
                                                        <p>
                                                            You will need your user UID/GID. You can retrieve this value by typing <b>id {AppContext.get().auth().getUsername()}</b> on your RES environment. In the example below, the UID is 5001 and GID is also 5001
                                                        </p>
                                                        <code>
                                                            #id {AppContext.get().auth().getUsername()} <br />
                                                            uid=5001({AppContext.get().auth().getUsername()}) gid=5001({AppContext.get().auth().getUsername()}) groups=5001({AppContext.get().auth().getUsername()})
                                                        </code>
                                                    </Alert>

                                                    <p>
                                                        Open AWS Console and navigate to the service named <b>AWS Transfer Family</b> select the server you have created and click <b>Add User</b> and enter the following information.
                                                    </p>

                                                    <Container>
                                                        <ColumnLayout columns={2}>
                                                            <KeyValue title="Username" value={AppContext.get().auth().getUsername()} />
                                                            <KeyValue title="User ID" value={"The Posix UID of your user you have retrieved via `id` command"} />
                                                            <KeyValue title="Group ID" value={"The Posix GID of your user you have retrieved via `id` command"} />
                                                            <KeyValue title="Role" value={"The IAM role you have created (ex: TransferEFSClient)"} />
                                                            <KeyValue title="Home Directory" value={"Select your RES EFS file system you have mounted as /home"} />
                                                            <KeyValue title="SSH Public Key" value={"The content of your SSH public key retrieved during Step 3"} />
                                                        </ColumnLayout>
                                                    </Container>

                                                    <h2>Step 6: Test</h2>
                                                    <p>
                                                        Open AWS Console and navigate to the service named <b>AWS Transfer Family</b> select the server you have created, and retrieve the <b>Endpoint</b> under <b>Endpoint Details</b>.
                                                    </p>
                                                    <Alert onDismiss={() => false} dismissAriaLabel="Close alert" header="Endpoint Information">
                                                        Your endpoint use the following syntax:{" "}
                                                        <b>
                                                            {"s-<UNIQUE_ID>"}-.server.transfer.{"<AWS_REGION>"}.amazonaws.com
                                                        </b>
                                                    </Alert>

                                                    <p>Connect to your AWS Transfer endpoint using your favorite FTP application via command line such as: </p>
                                                    <code>
                                                        sftp -i {"/PATH/TO/PRIVATE_KEY"} {AppContext.get().auth().getUsername()}@{"<AWS_TRANSFER_ENDPOINT>"}
                                                    </code>
                                                    <p>Alternatively, you can use WinSCP/FileZilla. Refer to the instructions available on this website and use your AWS Transfer endpoint as hostname.</p>
                                                </Box>
                                            </SpaceBetween>
                                        </Container>
                                    )}
                                </SpaceBetween>
                            ),
                        },
                    ]}
                />
                {/*</Container>*/}
            </div>
            )
        }

        const buildContent = () => {
            if (this.state.isLoading) {
                return buildLoadingContent();
            }
            if (this.state.isFileBrowserEnabled) {
                return buildFileBrowserContent();
            } else {
                return buildDisabledPageContent();
            }
        }

        return (
            <IdeaAppLayout
                ideaPageId={this.props.ideaPageId}
                header={<Header variant={"h1"}>File Browser</Header>}
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
                        text: "Home",
                        href: "#/",
                    },
                    {
                        text: "File Browser",
                        href: "",
                    },
                ]}
                contentType={"default"}
                disableContentHeaderOverlap={true}
                content={buildContent()}
            />
        );
    }
}

export default withRouter(IdeaFileBrowser);
