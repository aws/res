/**
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
import IdeaException from "../common/exceptions";
import { IdeaAuthenticationContext } from "../common/authentication-context";
import { JwtTokenClaims } from "../common/token-utils";
import { Constants } from "../common/constants";
import AppLogger from "../common/app-logger";
import { AUTH_TOKEN_EXPIRED } from "../common/error-codes";

export interface IdeaHeader {
    namespace: string;
    request_id: string;
    version?: number;
}

export interface IdeaEnvelope<T> {
    header?: IdeaHeader;
    payload?: T;
    success?: boolean;
    error_code?: string;
    message?: string;
}

export interface IdeaApiInvokerProps {
    name: string;
    url: string;
    timeout?: number;
    serviceWorkerRegistration?: ServiceWorkerRegistration;
    authContext?: IdeaAuthenticationContext;
}

export class IdeaApiInvoker {
    props: IdeaApiInvokerProps;
    logger: AppLogger;
    onLoginHook: (() => Promise<boolean>) | null;
    onLogoutHook: (() => Promise<boolean>) | null;

    constructor(props: IdeaApiInvokerProps) {
        this.props = props;
        this.logger = new AppLogger({
            name: props.name,
        });
        this.onLoginHook = null;
        this.onLogoutHook = null;
    }

    setHooks(onLogin: () => Promise<boolean>, onLogout: () => Promise<boolean>) {
        this.onLoginHook = onLogin;
        this.onLogoutHook = onLogout;
    }

    private empty = () => {
        const emptyPayload: any = {};
        return emptyPayload;
    };

    async invoke_service_worker(message: any): Promise<any> {
        return new Promise((resolve, reject) => {
            let messageChannel = new MessageChannel();
            messageChannel.port1.onmessage = (event) => {
                if (event.data.error) {
                    this.logger.error(event.data.error);
                    reject(event.data.error);
                }
                return resolve(event.data);
            };
            this.props.serviceWorkerRegistration!.active!.postMessage(message, [messageChannel.port2]);
        });
    }

    async invoke<REQ = any, RES = any>(request: IdeaEnvelope<REQ>, isPublic: boolean = false): Promise<IdeaEnvelope<RES>> {
        let url = `${this.props.url}/${request.header!.namespace}`;

        if (this.logger.isTrace()) {
            this.logger.trace(`(req) ${JSON.stringify(request, null, 2)}`);
        }

        let response;
        if (this.props.serviceWorkerRegistration) {
            const result = await this.invoke_service_worker({
                type: Constants.ServiceWorker.IDEA_API_INVOCATION,
                options: {
                    url: url,
                    request: request,
                    isPublic: isPublic,
                },
            });
            response = result.response;
        } else {
            if (request.header?.namespace === "Auth.InitiateAuth") {
                response = await this.props.authContext?.initiateAuth(request);
            } else {
                response = await this.props.authContext?.invoke(url, request, isPublic);
            }
        }

        if (this.logger.isTrace()) {
            this.logger.trace(`(res) ${JSON.stringify(response, null, 2)}`);
        }

        if (typeof response.success !== "undefined" && !response.success && response.error_code === AUTH_TOKEN_EXPIRED) {
            this.logout().then(() => {
                if (this.onLogoutHook) {
                    this.onLogoutHook();
                }
            });
        }

        return response;
    }

    async invoke_alt<REQ = any | null, RES = any>(namespace: string, payload?: REQ, isPublic: boolean = false): Promise<RES> {
        const result = await this.invoke<REQ, RES>(
            {
                header: {
                    namespace: namespace,
                    request_id: uuid(),
                },
                payload: payload ? payload : this.empty(),
            },
            isPublic
        );
        if (result.success) {
            return result.payload!;
        } else {
            console.error(result);
            throw new IdeaException({
                errorCode: result.error_code!,
                message: result.message,
                payload: result.payload,
            });
        }
    }

    async isLoggedIn(): Promise<boolean> {
        if (this.props.serviceWorkerRegistration) {
            const result = await this.invoke_service_worker({
                type: Constants.ServiceWorker.IDEA_AUTH_IS_LOGGED_IN,
            });
            return result.status;
        } else {
            return this.props.authContext!.isLoggedIn();
        }
    }

    async logout(): Promise<boolean> {
        if (this.props.serviceWorkerRegistration) {
            const result = await this.invoke_service_worker({
                type: Constants.ServiceWorker.IDEA_AUTH_LOGOUT,
            });
            return result.status;
        } else {
            return this.props.authContext!.logout();
        }
    }

    async getAccessToken(): Promise<string> {
        if (this.props.serviceWorkerRegistration) {
            const result = await this.invoke_service_worker({
                type: Constants.ServiceWorker.IDEA_AUTH_ACCESS_TOKEN,
            });
            return result.accessToken;
        } else {
            return await this.props.authContext!.getAccessToken();
        }
    }

    async getSWInitialized(): Promise<boolean>{
        const result = await this.invoke_service_worker({
            type: Constants.ServiceWorker.IDEA_GET_SW_INIT,
        });
        return result.isSwInitialized;
    }

    async getClientId(): Promise<string> {
        if (this.props.serviceWorkerRegistration) {
            const result = await this.invoke_service_worker({
                type: Constants.ServiceWorker.IDEA_CLIENT_ID,
            });
            return result.clientId;
        } else {
            try {
                return this.props.authContext!.getClientId();
            } catch (error) {
                return Promise.reject(error);
            }
        }
    }

    debug() {
        if (this.props.serviceWorkerRegistration) {
            this.props.serviceWorkerRegistration!.active!.postMessage({
                type: Constants.ServiceWorker.IDEA_AUTH_DEBUG,
            });
        } else {
            this.props.authContext!.printDebugInfo();
        }
    }

    async getClaims(): Promise<JwtTokenClaims> {
        if (this.props.serviceWorkerRegistration) {
            const result = await this.invoke_service_worker({
                type: Constants.ServiceWorker.IDEA_AUTH_TOKEN_CLAIMS,
            });
            return result.claims;
        } else {
            try {
                return this.props.authContext!.getClaims();
            } catch (error) {
                return Promise.reject(error);
            }
        }
    }

    async fetch(url: string, options: any, isPublic: boolean = false): Promise<Response> {
        if (this.props.serviceWorkerRegistration) {
            const result = await this.invoke_service_worker({
                type: Constants.ServiceWorker.IDEA_HTTP_FETCH,
                options: {
                    url: url,
                    options: options,
                    isPublic: isPublic,
                },
            });
            return result.response;
        } else {
            try {
                return await this.props.authContext!.fetch(url, options, isPublic);
            } catch (error) {
                return Promise.reject(error);
            }
        }
    }
}

export default IdeaApiInvoker;
