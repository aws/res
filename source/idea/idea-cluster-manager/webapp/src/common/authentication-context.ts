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

import { JwtTokenClaims, JwtTokenClaimsProvider, JwtTokenUtils } from "./token-utils";
import { AUTH_TOKEN_EXPIRED, NETWORK_ERROR, REQUEST_TIMEOUT, SERVER_ERROR } from "./error-codes";
import { LocalStorageService } from "../service";
import IdeaException from "./exceptions";
import Utils from "./utils";
import AppLogger from "./app-logger";

export interface IdeaAuthenticationContextProps {
    authEndpoint?: string;
    sessionManagement: "local-storage" | "in-memory";
}

export interface InitializeAppOptions {
    authEndpoint: string;
    defaultLogLevel: number;
}

const KEY_REFRESH_TOKEN = "refresh-token";
const KEY_ACCESS_TOKEN = "access-token";
const KEY_ID_TOKEN = "id-token";
const KEY_SSO_AUTH = "sso-auth";
const KEY_DB_USERNAME = "db-username";
const KEY_ROLE = "role";

const HEADER_CONTENT_TYPE_JSON = "application/json;charset=UTF-8";
const NETWORK_TIMEOUT = 30000;

/**
 * IDEA Authentication Context
 * provides functionality authentication and managing "session" at client side. session can be managed via 2 modes:
 * 1. LocalStorage
 * 2. ServiceWorker (with tokens saved in-memory)
 *
 * ServiceWorker based session management is the ideal mechanism for production applications.
 * LocalStorage mode, is an unsecure fallback mechanism when ServiceWorker cannot be initialized.
 *
 * ServiceWorker cannot be initialized in below scenarios:
 * 1. Insecure SSL/TLS Context
 * For service workers to be initialized, the origin must be served over HTTPS with valid certificates.
 * Self-signed certificates do not work with Service Worker.
 * Refer to: https://www.chromium.org/blink/serviceworker/service-worker-faq/ for additional details.
 *
 * 2. Not supported or disabled by browsers
 * At the time of this writing, Service Workers are supported by most modern Web Browsers including Edge and Safari on iOS (11.3+)
 * Refer to https://developer.mozilla.org/en-US/docs/Web/API/ServiceWorker for Browser Compatibility for Service Workers.
 *
 * ServiceWorkers can be disabled by browsers, for eg. FireFox automatically disables ServiceWorkers in incognito mode.
 * Additionally, a user may disable service worker via browser preferences. In such scenarios, implementation will
 * automatically fall back to local storage for session management. This behavior can be customized based on server side configuration.
 *
 */

export class IdeaAuthenticationContext {
    private readonly props: IdeaAuthenticationContextProps;

    private authEndpoint: string | null;
    private ssoAuth: boolean;
    private readonly localStorage: LocalStorageService | null;

    private refreshToken: string | null;
    private accessToken: string | null;
    private idToken: string | null;
    private claimsProvider: JwtTokenClaimsProvider | null;
    private dbUsername: string | null;
    private role: string | null;
    private logger: AppLogger;

    private authContextInitialized: boolean;
    private renewalInProgress: any;
    //Service worker initialized flag to know if service worker was killed in between or not
    private isServiceworkerInitialized: boolean;

    constructor(props: IdeaAuthenticationContextProps) {
        this.logger = new AppLogger({
            name: "authentication-context",
        });

        this.authContextInitialized = false;
        this.renewalInProgress = null;

        this.authEndpoint = null;
        this.ssoAuth = false;
        this.localStorage = null;

        this.refreshToken = null;
        this.accessToken = null;
        this.idToken = null;
        this.claimsProvider = null;
        this.dbUsername = null;
        this.role = null;
        this.props = props;
        this.isServiceworkerInitialized = false;

        // used in fallback mode when service-worker cannot be initialized
        if (typeof this.props.authEndpoint !== "undefined") {
            this.authEndpoint = this.props.authEndpoint;
        }

        // session management will never be local-storage, when AuthenticationContext is initialized from ServiceWorker.
        if (this.props.sessionManagement === "local-storage") {
            this.localStorage = new LocalStorageService({
                prefix: "idea.auth",
            });
            this.initializeFromLocalStorage();
        }
    }

    private initializeFromLocalStorage() {
        if (this.localStorage == null) {
            return;
        }

        this.accessToken = this.localStorage.getItem(KEY_ACCESS_TOKEN);
        this.idToken = this.localStorage.getItem(KEY_ID_TOKEN);
        this.refreshToken = this.localStorage.getItem(KEY_REFRESH_TOKEN);
        this.dbUsername = this.localStorage.getItem(KEY_DB_USERNAME);
        this.role = this.localStorage.getItem(KEY_ROLE);
        let ssoAuth = this.localStorage.getItem(KEY_SSO_AUTH);
        if (ssoAuth != null) {
            this.ssoAuth = Utils.asBoolean(ssoAuth);
        }

        if (this.accessToken != null && this.idToken != null && this.dbUsername != null && this.role != null) {
            this.claimsProvider = new JwtTokenClaimsProvider(this.accessToken, this.idToken, this.dbUsername, this.role);
        }
    }

    initializeSW() {
        this.isServiceworkerInitialized = true;
    }

    getSWInitialized(): boolean {
        return this.isServiceworkerInitialized;
    }

    /**
     * Initialize app authentication context
     * this is exposed primarily for the ServiceWorker flow, where the AuthenticationContext instance resides in ServiceWorker, and
     * authEndpoint and ssoAuth must be initialized after the app is initialized.
     * @param {string} options.authEndpoint
     * @param {boolean} options.ssoAuth
     */
    initializeAuthContext(options: InitializeAppOptions): Promise<boolean> {
        this.logger = new AppLogger({
            name: "authentication-context",
            default_log_level: options.defaultLogLevel,
        });
        return new Promise((resolve, _) => {
            this.authEndpoint = options.authEndpoint;
            resolve(true);
        });
    }

    private getAuthTokenExpiredError = () => {
        this.logger.warn("session expired");
        return {
            success: false,
            message: "Session Expired",
            error_code: AUTH_TOKEN_EXPIRED,
        };
    };

    /**
     * save the authentication result in-memory
     * if session_management == 'local-storage', local storage is initialized and tokens are saved in local storage.
     * @param authResult
     * @param ssoAuth
     * @private
     */
    private saveAuthResult(initiateAuthResult: any, ssoAuth: boolean) {
        if (initiateAuthResult.auth.refresh_token) {
            this.refreshToken = initiateAuthResult.auth.refresh_token;
        }
        this.accessToken = initiateAuthResult.auth.access_token;
        this.idToken = initiateAuthResult.auth.id_token;
        this.dbUsername = initiateAuthResult.db_username;
        this.role = initiateAuthResult.role;
        this.claimsProvider = new JwtTokenClaimsProvider(this.accessToken!, 
            this.idToken!,
            this.dbUsername!,
            this.role!);
        this.ssoAuth = ssoAuth;

        if (this.localStorage != null) {
            if (initiateAuthResult.auth.refresh_token) {
                this.localStorage.setItem(KEY_REFRESH_TOKEN, initiateAuthResult.auth.refresh_token!);
            }
            this.localStorage.setItem(KEY_SSO_AUTH, ssoAuth ? "true" : "false");
            this.localStorage.setItem(KEY_ACCESS_TOKEN, initiateAuthResult.auth.access_token!);
            this.localStorage.setItem(KEY_ID_TOKEN, initiateAuthResult.auth.id_token!);
            this.localStorage.setItem(KEY_DB_USERNAME, initiateAuthResult.db_username!);
            this.localStorage.setItem(KEY_ROLE, initiateAuthResult.role!);
        }
    }

    getClaims(): JwtTokenClaims {
        if (this.claimsProvider == null) {
            throw new IdeaException({
                errorCode: AUTH_TOKEN_EXPIRED,
                message: "Unauthorized Access",
            });
        }
        const claims = this.claimsProvider.getClaims();
        this.logger.debug("jwt token claims", claims);
        return claims;
    }

    getClientId(): string  {
        return this.claimsProvider!.getClientId();
    }

    isLoggedIn(): Promise<boolean> {
        if (this.localStorage != null) {
            // this is primarily to allow force token renewal in local storage mode for testing, by deleting the access token from local storage
            return this.renewAccessToken().then(() => {
                if (this.accessToken != null && this.idToken != null && this.dbUsername != null && this.role != null) {
                    this.claimsProvider = new JwtTokenClaimsProvider(this.accessToken,
                        this.idToken, this.dbUsername, this.role);
                    return true;
                } else {
                    return false;
                }
            });
        } else {
            const isLoggedIn = this.accessToken != null;
            this.logger.debug("is logged in: ", isLoggedIn);
            return Promise.resolve(isLoggedIn);
        }
    }

    logout(): Promise<boolean> {
        if (this.refreshToken == null) {
            return Promise.resolve(true);
        }

        const request = {
            header: {
                namespace: "Auth.SignOut",
                request_id: Utils.getUUID(),
            },
            payload: {
                sso_auth: this.ssoAuth,
                refresh_token: this.refreshToken,
            },
        };

        const signOutEndpoint = `${this.authEndpoint}/Auth.SignOut`;
        this.logger.info("logging out ...");

        return this.invoke(signOutEndpoint, request, false)
            .catch((error) => {
                this.logger.warn("sign out failed: unable to invalidate refresh token", error);
                return true;
            })
            .finally(() => {
                this.refreshToken = null;
                this.accessToken = null;
                this.idToken = null;
                this.claimsProvider = null;
                this.dbUsername = null;
                this.role = null;
                if (this.localStorage != null) {
                    this.localStorage.removeItem(KEY_ACCESS_TOKEN);
                    this.localStorage.removeItem(KEY_REFRESH_TOKEN);
                    this.localStorage.removeItem(KEY_SSO_AUTH);
                    this.localStorage.removeItem(KEY_ID_TOKEN);
                    this.localStorage.removeItem(KEY_DB_USERNAME);
                    this.localStorage.removeItem(KEY_ROLE);
                }
                return true;
            });
    }

    getAccessToken(): Promise<string> {
        return this.renewAccessToken().then((success) => {
            if (success) {
                return this.accessToken!;
            } else {
                return Promise.reject(this.getAuthTokenExpiredError());
            }
        });
    }

    isAccessTokenExpired(): boolean {
        if (this.accessToken == null) {
            return true;
        }
        if (this.claimsProvider == null) {
            return true;
        }
        return new Date().getTime() >= this.claimsProvider!.getExpiresAt() - 5 * 60 * 1000;
    }

    /**
     * wrapper over the in-built fetch method
     * @param url
     * @param options
     */
    private _fetch = (url: string, options: any): Promise<any> => {
        const abortController = new AbortController();
        const timeout = setTimeout(() => abortController.abort(), NETWORK_TIMEOUT);
        options = {
            ...options,
            signal: abortController.signal,
        };
        return fetch(url, options)
            .then((response) => {
                if (response.status === 200) {
                    return response.json();
                } else {
                    this.logger.error("server error", response);
                    return {
                        success: false,
                        error_code: SERVER_ERROR,
                        message: "Server error",
                    };
                }
            })
            .catch((error) => {
                this.logger.error("network error", error);
                if (error.name === "AbortError") {
                    return {
                        success: false,
                        error_code: REQUEST_TIMEOUT,
                        message: "Request timed-out",
                    };
                } else {
                    return {
                        success: false,
                        error_code: NETWORK_ERROR,
                        message: "Network error",
                    };
                }
            })
            .finally(() => {
                clearTimeout(timeout);
            });
    };

    /**
     * renew the access token using refresh token
     * 1. upon concurrent invocation of renewAccessToken(), the Promise created by the first invocation will be returned to subsequent invocations.
     * 2. if local storage is enabled, this function keeps the in-memory and local storage state in-sync by calling initializeFromLocalStorage()
     * 3. if refresh token is saved in local storage, and idToken or accessToken is missing, implementation will still try to renew the token.
     *
     * returns true if token was renewed successfully, false if token cannot be renewed and session must expire.
     * in case of network errors, throws exception with the IDEA response payload as error. token renewal invocations must handle this error appropriately.
     *  this ensures session is not invalidated due to network errors, where the session state is still valid and user does not need to re-login.
     */
    private renewAccessToken(): Promise<boolean> {
        // before renewing, check if the current in-memory tokens are stale.
        // this can only happen when using local storage, as another tab may renew the access token and update local storage.
        if (this.localStorage != null) {
            // this may need some sort of lock in future as there will be concurrent renewal scenario when multiple tabs are active.
            // since local storage is not recommended for production, this is safe to ignore.
            let accessToken = this.localStorage.getItem(KEY_ACCESS_TOKEN);
            if (accessToken !== this.accessToken) {
                this.initializeFromLocalStorage();
                if (!this.isAccessTokenExpired()) {
                    this.logger.info("✓ refreshed stale access token");
                    return Promise.resolve(true);
                }
            }
        }

        if (!this.isAccessTokenExpired()) {
            return Promise.resolve(true);
        }

        if (this.refreshToken == null) {
            return Promise.resolve(false);
        }

        this.logger.info("renewing access token ...");

        let cognito_username;
        if (this.claimsProvider == null) {
            if (this.accessToken != null) {
                let claims = JwtTokenUtils.parseJwtToken(this.accessToken);
                cognito_username = claims.username;
            } else if (this.idToken != null) {
                let claims = JwtTokenUtils.parseJwtToken(this.idToken);
                cognito_username = claims["cognito:username"];
            } else {
                console.info("✗ failed to renew token.");
                return Promise.resolve(false);
            }
        } else {
            cognito_username = this.claimsProvider.getCognitoUsername();
        }

        if (this.renewalInProgress != null) {
            return this.renewalInProgress;
        }

        let authFlow = "REFRESH_TOKEN_AUTH";
        if (this.ssoAuth) {
            authFlow = "SSO_REFRESH_TOKEN_AUTH";
        }

        let request = {
            header: {
                namespace: "Auth.InitiateAuth",
                request_id: Utils.getUUID(),
            },
            payload: {
                auth_flow: authFlow,
                cognito_username: cognito_username,
                refresh_token: this.refreshToken,
            },
        };

        const authEndpoint = `${this.authEndpoint}/${request.header.namespace}`;
        this.renewalInProgress = this._fetch(authEndpoint, {
            method: "POST",
            headers: {
                "Content-Type": HEADER_CONTENT_TYPE_JSON,
            },
            body: JSON.stringify(request),
        })
            .then((result) => {
                if (result.success && result.payload.auth) {
                    this.logger.info("✓ access token renewed successfully");
                    this.saveAuthResult(result.payload, this.ssoAuth);
                    return true;
                } else {
                    if (result.error_code === NETWORK_TIMEOUT || result.error_code === NETWORK_ERROR || result.error_code === SERVER_ERROR) {
                        throw result;
                    } else {
                        this.logger.info("✗ failed to renew token.");
                        return false;
                    }
                }
            })
            .finally(() => {
                this.renewalInProgress = null;
            });

        return this.renewalInProgress;
    }

    invoke(url: string, request: any, isPublic: boolean = false): Promise<any> {
        const invokeApi = () => {
            let headers: any = {
                "Content-Type": HEADER_CONTENT_TYPE_JSON,
            };
            let fetchOptions = {
                method: "POST",
                headers: headers,
                body: JSON.stringify(request),
            };
            if (!isPublic) {
                headers["Authorization"] = `Bearer ${this.accessToken}`;
            }
            return this._fetch(url, fetchOptions);
        };

        if (isPublic) {
            return invokeApi();
        }

        // if access token is expired, try to renew using refresh token and then invoke api.
        if (this.isAccessTokenExpired()) {
            return this.renewAccessToken()
                .then((success) => {
                    if (success) {
                        return invokeApi();
                    } else {
                        return Promise.resolve(this.getAuthTokenExpiredError());
                    }
                })
                .catch((error) => {
                    return error;
                });
        }

        return invokeApi();
    }

    initiateAuth(request: any): Promise<any> {
        const authEndpoint = `${this.authEndpoint}/${request.header.namespace}`;
        return this._fetch(authEndpoint, {
            method: "POST",
            headers: {
                "Content-Type": HEADER_CONTENT_TYPE_JSON,
            },
            body: JSON.stringify(request),
        }).then((result) => {
            if (result.success && result.payload.auth) {
                // cache auth result in-memory and return success response.
                // all subsequent API invocations will be attached with the Authorization header.
                this.logger.debug("✓ initiate auth successful");
                const isSsoAuth = request.payload.auth_flow === "SSO_AUTH";
                this.saveAuthResult(result.payload, isSsoAuth);
                return {
                    success: true,
                    payload: {},
                };
            }

            // return response message in all the other scenarios, where refresh and access token is not exposed to
            // the main thread.
            return result;
        });
    }

    fetch(url: string, options: any, isPublic: boolean = false): Promise<Response> {
        if (!isPublic) {
            if (typeof options.headers === "undefined") {
                options.headers = {};
            }
            options.headers["Authorization"] = `Bearer ${this.accessToken}`;
        }
        return fetch(url, options);
    }

    /**
     * print debug info using in-memory state.
     * helpful to debug service worker implementation and check the in-memory state via browser console.
     */
    printDebugInfo() {
        this.isLoggedIn().then((status) => {
            if (status) {
                console.log("Is Logged In: ", "Yes");
                console.log("Access Token: ", this.accessToken);
                console.log("Refresh Token: ", this.refreshToken);
                console.log("Id Token: ", this.idToken);
                console.log("Is SSO Auth: ", this.ssoAuth);
                console.log("Claims: ", this.claimsProvider?.getClaims());
            } else {
                console.log("Is Logged In: ", "No");
            }
        });
    }
}
