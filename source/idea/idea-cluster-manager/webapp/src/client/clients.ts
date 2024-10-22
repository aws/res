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

import AuthClient from "./auth-client";
import AccountsClient from "./accounts-client";
import SnapshotsClient from "./snapshots-client";
import SchedulerAdminClient from "./scheduler-admin-client";
import SchedulerClient from "./scheduler-client";
import FileBrowserClient from "./file-browser-client";
import VirtualDesktopClient from "./virtual-desktop-client";
import VirtualDesktopAdminClient from "./virtual-desktop-admin-client";
import ClusterSettingsClient from "./cluster-settings-client";
import ProjectsClient from "./projects-client";
import EmailTemplatesClient from "./email-templates-client";
import Utils from "../common/utils";
import { Constants } from "../common/constants";
import VirtualDesktopUtilsClient from "./virtual-desktop-utils-client";
import VirtualDesktopDCVClient from "./virtual-desktop-dcv-client";
import { IdeaAuthenticationContext } from "../common/authentication-context";
import IdeaBaseClient, { IdeaBaseClientProps } from "./base-client";
import FileSystemClient from "./filesystem-client";
import AuthzClient from "./authz-client";
import ProxyClient from "./proxy-client";

export interface IdeaClientsProps {
    appId: string;
    baseUrl: string;
    authContext?: IdeaAuthenticationContext;
    serviceWorkerRegistration?: ServiceWorkerRegistration;
}

class IdeaClients {
    private readonly authClient: AuthClient;
    private readonly authzClient: AuthzClient;
    private readonly authAdminClient: AccountsClient;
    private readonly snapshotsClient: SnapshotsClient;
    private readonly schedulerAdminClient: SchedulerAdminClient;
    private readonly schedulerClient: SchedulerClient;
    private readonly fileBrowserClient: FileBrowserClient;
    private readonly virtualDesktopClient: VirtualDesktopClient;
    private readonly virtualDesktopAdminClient: VirtualDesktopAdminClient;
    private readonly virtualDesktopUtilsClient: VirtualDesktopUtilsClient;
    private readonly virtualDesktopDCVClient: VirtualDesktopDCVClient;
    private readonly clusterSettingsClient: ClusterSettingsClient;
    private readonly projectsClient: ProjectsClient;
    private readonly filesystemClient: FileSystemClient;
    private readonly emailTemplatesClient: EmailTemplatesClient;
    private readonly proxyClient: ProxyClient;

    private readonly clients: IdeaBaseClient<IdeaBaseClientProps>[];

    constructor(props: IdeaClientsProps) {
        this.clients = [];

        this.authClient = new AuthClient({
            name: "auth-client",
            baseUrl: props.baseUrl,
            authContext: props.authContext,
            apiContextPath: Utils.getApiContextPath(Constants.MODULE_CLUSTER_MANAGER),
            serviceWorkerRegistration: props.serviceWorkerRegistration,
        });
        this.clients.push(this.authClient);

        this.authzClient = new AuthzClient({
            name: "authz-client",
            baseUrl: props.baseUrl,
            authContext: props.authContext,
            apiContextPath: Utils.getApiContextPath(Constants.MODULE_CLUSTER_MANAGER),
            serviceWorkerRegistration: props.serviceWorkerRegistration,
        });
        this.clients.push(this.authzClient);

        this.authAdminClient = new AccountsClient({
            name: "accounts-client",
            baseUrl: props.baseUrl,
            authContext: props.authContext,
            apiContextPath: Utils.getApiContextPath(Constants.MODULE_CLUSTER_MANAGER),
            serviceWorkerRegistration: props.serviceWorkerRegistration,
        });
        this.clients.push(this.authAdminClient);

        this.proxyClient = new ProxyClient({
            name: "proxy-client",
            baseUrl: `${props.baseUrl}/awsproxy`,
            authContext: props.authContext,
            apiContextPath: "",
            serviceWorkerRegistration: props.serviceWorkerRegistration,
        });
        this.clients.push(this.proxyClient);

        this.snapshotsClient = new SnapshotsClient({
            name: "snapshots-client",
            baseUrl: props.baseUrl,
            authContext: props.authContext,
            apiContextPath: Utils.getApiContextPath(Constants.MODULE_CLUSTER_MANAGER),
            serviceWorkerRegistration: props.serviceWorkerRegistration,
        });
        this.clients.push(this.snapshotsClient);

        this.schedulerAdminClient = new SchedulerAdminClient({
            name: "scheduler-admin-client",
            baseUrl: props.baseUrl,
            authContext: props.authContext,
            apiContextPath: Utils.getApiContextPath(Constants.MODULE_SCHEDULER),
            serviceWorkerRegistration: props.serviceWorkerRegistration,
        });
        this.clients.push(this.schedulerAdminClient);

        this.schedulerClient = new SchedulerClient({
            name: "scheduler-client",
            baseUrl: props.baseUrl,
            authContext: props.authContext,
            apiContextPath: Utils.getApiContextPath(Constants.MODULE_SCHEDULER),
            serviceWorkerRegistration: props.serviceWorkerRegistration,
        });
        this.clients.push(this.authClient);

        this.fileBrowserClient = new FileBrowserClient({
            name: "file-browser-client",
            baseUrl: props.baseUrl,
            authContext: props.authContext,
            apiContextPath: Utils.getApiContextPath(Constants.MODULE_CLUSTER_MANAGER),
            serviceWorkerRegistration: props.serviceWorkerRegistration,
        });
        this.clients.push(this.fileBrowserClient);

        this.virtualDesktopAdminClient = new VirtualDesktopAdminClient({
            name: "virtual-desktop-admin-client",
            baseUrl: props.baseUrl,
            authContext: props.authContext,
            apiContextPath: Utils.getApiContextPath(Constants.MODULE_VIRTUAL_DESKTOP_CONTROLLER),
            serviceWorkerRegistration: props.serviceWorkerRegistration,
        });
        this.clients.push(this.authClient);

        this.virtualDesktopClient = new VirtualDesktopClient({
            name: "virtual-desktop-client",
            baseUrl: props.baseUrl,
            authContext: props.authContext,
            apiContextPath: Utils.getApiContextPath(Constants.MODULE_VIRTUAL_DESKTOP_CONTROLLER),
            serviceWorkerRegistration: props.serviceWorkerRegistration,
        });
        this.clients.push(this.virtualDesktopClient);

        this.virtualDesktopUtilsClient = new VirtualDesktopUtilsClient({
            name: "virtual-desktop-utils-client",
            baseUrl: props.baseUrl,
            authContext: props.authContext,
            apiContextPath: Utils.getApiContextPath(Constants.MODULE_VIRTUAL_DESKTOP_CONTROLLER),
            serviceWorkerRegistration: props.serviceWorkerRegistration,
        });
        this.clients.push(this.virtualDesktopUtilsClient);

        this.virtualDesktopDCVClient = new VirtualDesktopDCVClient({
            name: "virtual-desktop-dcv-client",
            baseUrl: props.baseUrl,
            authContext: props.authContext,
            apiContextPath: Utils.getApiContextPath(Constants.MODULE_VIRTUAL_DESKTOP_CONTROLLER),
            serviceWorkerRegistration: props.serviceWorkerRegistration,
        });
        this.clients.push(this.virtualDesktopDCVClient);

        this.clusterSettingsClient = new ClusterSettingsClient({
            name: "cluster-settings-client",
            baseUrl: props.baseUrl,
            authContext: props.authContext,
            apiContextPath: Utils.getApiContextPath(Constants.MODULE_CLUSTER_MANAGER),
            serviceWorkerRegistration: props.serviceWorkerRegistration,
        });
        this.clients.push(this.clusterSettingsClient);

        this.projectsClient = new ProjectsClient({
            name: "projects-client",
            baseUrl: props.baseUrl,
            authContext: props.authContext,
            apiContextPath: Utils.getApiContextPath(Constants.MODULE_CLUSTER_MANAGER),
            serviceWorkerRegistration: props.serviceWorkerRegistration,
        });
        this.clients.push(this.projectsClient);

        this.filesystemClient = new FileSystemClient({
            name: "filesystem-client",
            baseUrl: props.baseUrl,
            authContext: props.authContext,
            apiContextPath: Utils.getApiContextPath(Constants.MODULE_CLUSTER_MANAGER),
            serviceWorkerRegistration: props.serviceWorkerRegistration,
        });
        this.clients.push(this.filesystemClient);

        this.emailTemplatesClient = new EmailTemplatesClient({
            name: "email-templates-client",
            baseUrl: props.baseUrl,
            authContext: props.authContext,
            apiContextPath: Utils.getApiContextPath(Constants.MODULE_CLUSTER_MANAGER),
            serviceWorkerRegistration: props.serviceWorkerRegistration,
        });
        this.clients.push(this.emailTemplatesClient);
    }

    getClients(): IdeaBaseClient<IdeaBaseClientProps>[] {
        return this.clients;
    }

    auth(): AuthClient {
        return this.authClient;
    }

    authz(): AuthzClient {
        return this.authzClient;
    }

    accounts(): AccountsClient {
        return this.authAdminClient;
    }

    snapshots(): SnapshotsClient {
        return this.snapshotsClient;
    }

    schedulerAdmin(): SchedulerAdminClient {
        return this.schedulerAdminClient;
    }

    scheduler(): SchedulerClient {
        return this.schedulerClient;
    }

    fileBrowser(): FileBrowserClient {
        return this.fileBrowserClient;
    }

    virtualDesktop(): VirtualDesktopClient {
        return this.virtualDesktopClient;
    }

    virtualDesktopAdmin(): VirtualDesktopAdminClient {
        return this.virtualDesktopAdminClient;
    }

    virtualDesktopUtils(): VirtualDesktopUtilsClient {
        return this.virtualDesktopUtilsClient;
    }

    virtualDesktopDCV(): VirtualDesktopDCVClient {
        return this.virtualDesktopDCVClient;
    }

    clusterSettings(): ClusterSettingsClient {
        return this.clusterSettingsClient;
    }

    projects(): ProjectsClient {
        return this.projectsClient;
    }

    filesystem(): FileSystemClient {
        return this.filesystemClient;
    }

    emailTemplates(): EmailTemplatesClient {
        return this.emailTemplatesClient;
    }

    proxy(): ProxyClient {
        return this.proxyClient;
    }
}

export default IdeaClients;
