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

import { v4 as uuid } from "uuid";
import { AuthService, LocalStorageService } from "../service";
import IdeaException from "../common/exceptions";
import JobTemplatesService from "../service/job-templates-service";
import ClusterSettingsService from "../service/cluster-settings-service";
import Utils from "./utils";
import { Constants } from "./constants";
import { IdeaAuthenticationContext } from "./authentication-context";
import { IdeaClients } from "../client";

export interface AppContextProps {
    httpEndpoint: string;
    albEndpoint: string;
    releaseVersion: string;
    app: AppData;
    serviceWorkerRegistration?: ServiceWorkerRegistration;
    serviceWorkerInitialized?: boolean;
}

export interface AppData {
    sso: boolean;
    version: string;
    cluster_name: string;
    aws_region: string;
    title: string;
    subtitle?: string;
    logo?: string;
    copyright_text?: string;
    module_set: string;
    modules: any;
    session_management: "local-storage" | "in-memory";
    default_log_level: number;
}

const DARK_MODE_KEY = "theme.dark-mode";
const COMPACT_MODE_KEY = "theme.compact-mode";

let IS_LOGGED_IN_INTERVAL: any = null;

class AppContext {
    private props: AppContextProps;

    private readonly clients: IdeaClients;
    private readonly localStorageService: LocalStorageService;
    private readonly authContext?: IdeaAuthenticationContext;
    private readonly authService: AuthService;
    private readonly jobTemplatesService: JobTemplatesService;
    private readonly clusterSettingsService: ClusterSettingsService;

    private static onRouteCallback?: any;

    private isLoggedIn: boolean = false;
    private onLogin?: () => Promise<boolean>;
    private onLogout?: () => Promise<boolean>;

    constructor(props: AppContextProps) {
        this.props = props;

        const authEndpoint = `${props.httpEndpoint}${Utils.getApiContextPath(Constants.MODULE_CLUSTER_MANAGER)}`;

        const reInitializeServiceWorker = () => {
            /*
             * Current mechanism to reInitialize is to hit the homepage
             * UX: User redirected to homepage regardless
             */
            window.location.href = "/";
        };

        const initializeServiceWorker = () => {
            if (this.props.serviceWorkerRegistration) {
                if (this.props.serviceWorkerInitialized && window.idea.context != null) {
                    AppContext.get()
                        .client()
                        .auth()
                        .getSWInitialized()
                        .then((isSwInitialized) => {
                            /*
                             * If ServiceWorker(SW) is not initialized but appContext says its initialized
                             * it means that the SW was stopped in between => re-initialize SW.
                             * The SW could be killed by the browser to save up on memory (known in Chrome).
                             */
                            if (!isSwInitialized) {
                                reInitializeServiceWorker();
                            }
                        });
                }
                this.props.serviceWorkerRegistration.active!.postMessage({
                    type: Constants.ServiceWorker.IDEA_SW_INIT,
                });
                this.props.serviceWorkerRegistration.active!.postMessage({
                    type: Constants.ServiceWorker.IDEA_AUTH_INIT,
                    options: {
                        authEndpoint: authEndpoint,
                        defaultLogLevel: props.app.default_log_level,
                    },
                });
                this.props.serviceWorkerInitialized = true;
            }
        };

        if (this.props.serviceWorkerRegistration) {
            initializeServiceWorker();
        } else {
            this.authContext = new IdeaAuthenticationContext({
                sessionManagement: "local-storage",
                authEndpoint: authEndpoint,
            });
        }

        this.localStorageService = new LocalStorageService({
            prefix: "idea",
        });

        this.clients = new IdeaClients({
            appId: "web-portal",
            baseUrl: props.httpEndpoint,
            authContext: this.authContext,
            serviceWorkerRegistration: props.serviceWorkerRegistration,
        });

        this.authService = new AuthService({
            localStorage: this.localStorageService,
            clients: this.clients,
        });

        this.clusterSettingsService = new ClusterSettingsService({
            clusterSettings: this.clients.clusterSettings(),
        });

        this.jobTemplatesService = new JobTemplatesService({});

        // the purpose of below interval is:
        // 1. ensure we send a periodic heart-beat to service-worker so that service worker remains active.
        //    this is only applicable when service worker is initialized. on FireFox, service worker becomes inactive
        //    after 30-seconds of no activity to service worker and session expires prematurely.
        // 2. check for login status changes and take respective actions

        if (IS_LOGGED_IN_INTERVAL != null) {
            clearInterval(IS_LOGGED_IN_INTERVAL);
        }

        IS_LOGGED_IN_INTERVAL = setInterval(() => {
            // initializing service worker in this interval ensures that in the event the service worker was stopped and
            //  started, the service worker knows the authentication endpoints
            initializeServiceWorker();

            // check if the user is logged in. this may query the service worker or authentication context based on current session management mode.
            this.authService.isLoggedIn().then((status) => {
                if (this.isLoggedIn && !status) {
                    this.authService.logout().finally();
                }
                this.isLoggedIn = status;
            });
        }, 10000);
    }

    static setOnRoute(onRoute: any) {
        this.onRouteCallback = onRoute;
    }

    static get(): AppContext {
        if (window.idea.context == null) {
            throw new IdeaException({
                errorCode: "APP_CONTEXT_NOT_INITIALIZED",
                message: "AppContext not initialized",
            });
        }
        return window.idea.context;
    }

    setHooks(onLogin: () => Promise<boolean>, onLogout: () => Promise<boolean>) {
        this.onLogin = onLogin;
        this.onLogout = onLogout;
        this.authService.setHooks(onLogin, onLogout);
        this.clients.getClients().forEach((client) => {
            client.setHooks(onLogin, onLogout);
        });
    }

    setDarkMode(darkMode: boolean) {
        return this.localStorage().setItem(DARK_MODE_KEY, `${darkMode}`);
    }

    isDarkMode(): boolean {
        return Utils.asBoolean(AppContext.get().localStorage().getItem(DARK_MODE_KEY), false);
    }

    setCompactMode(compactMode: boolean) {
        return this.localStorage().setItem(COMPACT_MODE_KEY, `${compactMode}`);
    }

    isCompactMode(): boolean {
        return Utils.asBoolean(AppContext.get().localStorage().getItem(COMPACT_MODE_KEY), false);
    }

    getHttpEndpoint(): string {
        return this.props.httpEndpoint;
    }

    getAlbEndpoint(): string {
        return this.props.albEndpoint;
    }

    releaseVersion(): string {
        return this.props.releaseVersion;
    }

    getClusterName(): string {
        return this.props.app.cluster_name;
    }

    getAwsRegion(): string {
        return this.props.app.aws_region;
    }

    getTitle(): string {
        return this.props.app.title;
    }

    getSubtitle(): string {
        if (this.props.app.subtitle != null) {
            return this.props.app.subtitle;
        }
        const clusterName = this.getClusterName();
        if (Utils.isNotEmpty(clusterName)) {
            return `${this.getClusterName()} (${this.getAwsRegion()})`;
        } else {
            return "";
        }
    }

    getLogoUrl(): string | undefined {
        return this.props.app.logo;
    }

    getCopyRightText(): string {
        if (this.props.app.copyright_text) {
            return this.props.app.copyright_text;
        } else {
            return "Copyright 2023 Amazon.com, Inc. or its affiliates. All Rights Reserved.";
        }
    }

    uuid(): string {
        return uuid();
    }

    client(): IdeaClients {
        return this.clients;
    }

    auth(): AuthService {
        return this.authService;
    }

    localStorage(): LocalStorageService {
        return this.localStorageService;
    }

    jobTemplates(): JobTemplatesService {
        return this.jobTemplatesService;
    }

    getClusterSettingsService(): ClusterSettingsService {
        return this.clusterSettingsService;
    }

    routeTo(path: string) {
        if (AppContext.onRouteCallback) {
            AppContext.onRouteCallback(path);
        }
    }

    getSSOEnabled(): boolean {
        return this.props.app.sso;
    }
}

export default AppContext;
