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

import { Box, Button, Header, Modal, Tabs } from "@cloudscape-design/components";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faDownload, faExternalLinkAlt } from "@fortawesome/free-solid-svg-icons";
import React from "react";
import { VirtualDesktopSession } from "../../../client/data-model";
import { AppContext } from "../../../common";

function downloadDcvClient(os: string) {
    let client_settings: any = AppContext.get().getClusterSettingsService().globalSettings.package_config.dcv.clients;
    if (os === "windows-zip") {
        window.open(client_settings.windows.zip.url);
    } else if (os === "windows-msi") {
        window.open(client_settings.windows.msi.url);
    } else if (os === "macos-m1") {
        window.open(client_settings.macos.m1.url);
    } else if (os === "macos-intel") {
        window.open(client_settings.macos.intel.url);
    } else if (os === "linux-rhel_centos_rocky8") {
        window.open(client_settings.linux.rhel_centos_rocky8.url);
    } else if (os === "linux-suse15") {
        window.open(client_settings.linux.suse15.url);
    } else if (os === "ubuntu-ubuntu2004") {
        window.open(client_settings.ubuntu.ubuntu2004.url);
    } else if (os === "ubuntu-ubuntu2204") {
        window.open(client_settings.ubuntu.ubuntu2204.url);
    }
}

function getDCVClientLabelForOSFlavor(os: string): string {
    let client_settings: any = AppContext.get().getClusterSettingsService().globalSettings.package_config.dcv.clients;
    if (os === "windows-zip") {
        return client_settings.windows.zip.label;
    } else if (os === "windows-msi") {
        return client_settings.windows.msi.label;
    } else if (os === "macos-m1") {
        return client_settings.macos.m1.label;
    } else if (os === "macos-intel") {
        return client_settings.macos.intel.label;
    } else if (os === "linux-rhel_centos_rocky8") {
        return client_settings.linux.rhel_centos_rocky8.label;
    } else if (os === "linux-suse15") {
        return client_settings.linux.suse15.label;
    } else if (os === "ubuntu-ubuntu2004") {
        return client_settings.ubuntu.ubuntu2004.label;
    } else if (os === "ubuntu-ubuntu2204") {
        return client_settings.ubuntu.ubuntu2204.label;
    }
    return "";
}

export interface DcvClientHelpModalProps {
    session: VirtualDesktopSession;
    onDismiss: () => void;
    onDownloadDcvSessionFile: (session: VirtualDesktopSession) => Promise<boolean>;
    onLaunchSession: (session: VirtualDesktopSession) => Promise<boolean>;
    visible: boolean;
}

export function DcvClientHelpModal(props: DcvClientHelpModalProps) {
    return (
        <Modal
            visible={props.visible}
            onDismiss={props.onDismiss}
            size="large"
            header={<Header>How to connect to your Virtual Desktop?</Header>}
            footer={
                <Box float="right">
                    <Button variant="primary" onClick={props.onDismiss}>
                        Close
                    </Button>
                </Box>
            }
        >
            <Tabs
                tabs={[
                    {
                        label: "Windows",
                        id: "dcv-native-windows",
                        content: (
                            <div>
                                <p>
                                    <strong>Step 1)</strong> Download DCV Windows Client.
                                </p>
                                <p>
                                    <Button variant={"link"} onClick={() => downloadDcvClient("windows-zip")}>
                                        <FontAwesomeIcon icon={faDownload} /> {getDCVClientLabelForOSFlavor("windows-zip")}
                                    </Button>
                                    <Button variant={"link"} onClick={() => downloadDcvClient("windows-msi")}>
                                        <FontAwesomeIcon icon={faDownload} /> {getDCVClientLabelForOSFlavor("windows-msi")}
                                    </Button>
                                </p>
                                <p>
                                    <strong>Step 2)</strong> Install the DCV client on your computer.
                                </p>
                                <p>
                                    <strong>Step 3)</strong> Download your virtual desktop connection file. (DCV Session File)
                                    <Button disabled={props.session.state !== "READY"} variant={"link"} onClick={() => props.onDownloadDcvSessionFile(props.session).finally()}>
                                        <FontAwesomeIcon icon={faDownload} /> Download
                                    </Button>
                                </p>
                                <p>
                                    <strong>Step 4)</strong> Open your .dcv (DCV Session File) with DCV viewer client.
                                </p>
                            </div>
                        ),
                    },
                    {
                        label: "Mac OS",
                        id: "dcv-native-mac-os",
                        content: (
                            <div>
                                <p>
                                    <strong>Step 1)</strong> Download DCV MacOS Client.
                                </p>
                                <p>
                                    <Button variant={"link"} onClick={() => downloadDcvClient("macos-m1")}>
                                        <FontAwesomeIcon icon={faDownload} /> {getDCVClientLabelForOSFlavor("macos-m1")}
                                    </Button>
                                    <Button variant={"link"} onClick={() => downloadDcvClient("macos-intel")}>
                                        <FontAwesomeIcon icon={faDownload} /> {getDCVClientLabelForOSFlavor("macos-intel")}
                                    </Button>
                                </p>
                                <p>
                                    <strong>Step 2)</strong> Install the DCV client on your computer.
                                </p>
                                <p>
                                    <strong>Step 3)</strong> Download your virtual desktop connection file. (DCV Session File)
                                    <Button disabled={props.session.state !== "READY"} variant={"link"} onClick={() => props.onDownloadDcvSessionFile(props.session).finally()}>
                                        <FontAwesomeIcon icon={faDownload} /> Download
                                    </Button>
                                </p>
                                <p>
                                    <strong>Step 4)</strong> Open your .dcv (DCV Session File) with DCV viewer client.
                                </p>
                            </div>
                        ),
                    },
                    {
                        label: "Linux",
                        id: "dcv-native-linux",
                        content: (
                            <div>
                                <p>
                                    <strong>Step 1)</strong> Download DCV Linux Client.
                                </p>
                                <p>
                                    <Button variant={"link"} onClick={() => downloadDcvClient("linux-rhel_centos_rocky8")}>
                                        <FontAwesomeIcon icon={faDownload} /> {getDCVClientLabelForOSFlavor("linux-rhel_centos_rocky8")}
                                    </Button>
                                    <Button variant={"link"} onClick={() => downloadDcvClient("linux-suse15")}>
                                        <FontAwesomeIcon icon={faDownload} /> {getDCVClientLabelForOSFlavor("linux-suse15")}
                                    </Button>
                                </p>
                                <p>
                                    <strong>Step 2)</strong> Install the DCV client on your computer.
                                </p>
                                <p>
                                    <strong>Step 3)</strong> Download your virtual desktop connection file. (DCV Session File)
                                    <Button disabled={props.session.state !== "READY"} variant={"link"} onClick={() => props.onDownloadDcvSessionFile(props.session).finally()}>
                                        <FontAwesomeIcon icon={faDownload} /> Download
                                    </Button>
                                </p>
                                <p>
                                    <strong>Step 4)</strong> Open your .dcv (DCV Session File) with DCV viewer client.
                                </p>
                            </div>
                        ),
                    },
                    {
                        label: "Ubuntu",
                        content: (
                            <div>
                                <p>
                                    <strong>Step 1)</strong> Download DCV Ubuntu Client.
                                </p>
                                <p>
                                    <Button variant={"link"} onClick={() => downloadDcvClient("ubuntu-ubuntu2004")}>
                                        <FontAwesomeIcon icon={faDownload} /> {getDCVClientLabelForOSFlavor("ubuntu-ubuntu2004")}
                                    </Button>
                                    <Button variant={"link"} onClick={() => downloadDcvClient("ubuntu-ubuntu2204")}>
                                        <FontAwesomeIcon icon={faDownload} /> {getDCVClientLabelForOSFlavor("ubuntu-ubuntu2204")}
                                    </Button>
                                </p>
                                <p>
                                    <strong>Step 2)</strong> Install the DCV client on your computer.
                                </p>
                                <p>
                                    <strong>Step 3)</strong> Download your virtual desktop connection file. (DCV Session File)
                                    <Button disabled={props.session.state !== "READY"} variant={"link"} onClick={() => props.onDownloadDcvSessionFile(props.session).finally()}>
                                        <FontAwesomeIcon icon={faDownload} /> Download
                                    </Button>
                                </p>
                                <p>
                                    <strong>Step 4)</strong> Open your .dcv (DCV Session File) with DCV viewer client.
                                </p>
                            </div>
                        ),
                        id: "dcv-native-ubuntu",
                    },
                    {
                        label: "Web Browser",
                        id: "web-browser",
                        content: (
                            <div>
                                <p>Connect using your Web Browser (One-Click).</p>
                                <p>
                                    <Button disabled={props.session.state !== "READY"} variant="primary" onClick={() => props.onLaunchSession(props.session).finally()}>
                                        <FontAwesomeIcon icon={faExternalLinkAlt} /> Connect
                                    </Button>
                                </p>
                            </div>
                        ),
                    },
                ]}
            />
        </Modal>
    );
}
