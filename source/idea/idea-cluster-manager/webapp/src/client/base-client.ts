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

import { IdeaAuthenticationContext } from "../common/authentication-context";
import IdeaApiInvoker from "./idea-api-invoker";

export interface IdeaBaseClientProps {
    name: string;
    baseUrl: string;
    apiContextPath: string;
    authContext?: IdeaAuthenticationContext;
    serviceWorkerRegistration?: ServiceWorkerRegistration;
}

class IdeaBaseClient<P extends IdeaBaseClientProps> {
    readonly props: P;
    readonly apiInvoker: IdeaApiInvoker;

    onLoginHook: (() => Promise<boolean>) | null;
    onLogoutHook: (() => Promise<boolean>) | null;

    constructor(props: P) {
        this.props = props;

        this.apiInvoker = new IdeaApiInvoker({
            name: props.name,
            url: this.getEndpointUrl(),
            authContext: this.props.authContext,
            serviceWorkerRegistration: this.props.serviceWorkerRegistration,
        });

        this.onLoginHook = null;
        this.onLogoutHook = null;
    }

    getEndpointUrl(): string {
        return `${this.props.baseUrl}${this.props.apiContextPath}`;
    }

    setHooks(onLogin: () => Promise<boolean>, onLogout: () => Promise<boolean>) {
        this.onLoginHook = onLogin;
        this.onLogoutHook = onLogout;
        this.apiInvoker.setHooks(onLogin, onLogout);
    }
}

export default IdeaBaseClient;
