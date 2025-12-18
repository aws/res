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
import { Constants, HTTPMethod } from "../common/constants";
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
    additionalHeader?: any;
}

export interface IdeaApiInvokerProps {
    name: string;
    url: string;
    timeout?: number;
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

    async invoke<REQ = any, RES = any>(request: IdeaEnvelope<REQ>, isPublic: boolean = false, isAWSProxyRequest: boolean = false, httpMethod:HTTPMethod = "POST"): Promise<IdeaEnvelope<RES>> {
        let url = `${this.props.url}/${request.header!.namespace}`;

        if (this.logger.isTrace()) {
            this.logger.trace(`(req) ${JSON.stringify(request, null, 2)}`);
        }

        let response;
        if (request.header?.namespace === "Auth.InitiateAuth") {
            response = await this.props.authContext?.initiateAuth(request);
        } else if (isAWSProxyRequest) {
            response = await this.props.authContext?.invoke(url, request.payload, isPublic, request.additionalHeader, httpMethod);
        } else {
            response = await this.props.authContext?.invoke(url, request, isPublic);
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

    async invoke_alt<REQ = any | null, RES = any>(namespace: string, payload?: REQ, isPublic: boolean = false, isAWSProxyRequest: boolean = false, additionalHeader: any = {}, httpMethod:HTTPMethod = "POST" ): Promise<RES> {
        const result = await this.invoke<REQ, RES>(
            {
                header: {
                    namespace: namespace,
                    request_id: uuid(),
                },
                payload: payload ? payload : this.empty(),
                additionalHeader
            },
            isPublic,
            isAWSProxyRequest,
            httpMethod
        );
        if (result.success) {
            return result.payload!
        }
        else if (isAWSProxyRequest) {
            return result as RES;
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
        return this.props.authContext!.isLoggedIn();
    }

    async logout(): Promise<boolean> {
        return this.props.authContext!.logout();
    }

    async getAccessToken(): Promise<string> {
        return await this.props.authContext!.getAccessToken();
    }

    async getClientId(): Promise<string> {
        try {
                return this.props.authContext!.getClientId();
            } catch (error) {
                return Promise.reject(error);
            }
    }

    debug() {
        this.props.authContext!.printDebugInfo();
    }

    async getClaims(): Promise<JwtTokenClaims> {
        try {
            return this.props.authContext!.getClaims();
        } catch (error) {
            return Promise.reject(error);
        }
    }

    async fetch(url: string, options: any, isPublic: boolean = false): Promise<Response> {
        try {
            return await this.props.authContext!.fetch(url, options, isPublic);
        } catch (error) {
            return Promise.reject(error);
        }
    }
}

export default IdeaApiInvoker;
