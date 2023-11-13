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

/// <reference lib="webworker" />
/* eslint-disable no-restricted-globals */

import { clientsClaim } from "workbox-core";
import "workbox-precaching";
import { IdeaAuthenticationContext } from "./common/authentication-context";
import { Constants } from "./common/constants";

declare const self: ServiceWorkerGlobalScope;
const IDEA_AUTH_CONTEXT = new IdeaAuthenticationContext({
    sessionManagement: "in-memory",
});

clientsClaim();

// precaching disabled
// eslint-disable-next-line no-restricted-globals
const ignored = self.__WB_MANIFEST;

self.addEventListener("message", (event) => {
    if (event.data && event.data.type) {
        switch (event.data.type) {
            case Constants.ServiceWorker.SKIP_WAITING:
                self.skipWaiting();
                break;
            case Constants.ServiceWorker.IDEA_SW_INIT:
                IDEA_AUTH_CONTEXT.initializeSW()
                break;
            case Constants.ServiceWorker.IDEA_GET_SW_INIT:
                try {
                    event.ports[0].postMessage({
                        isSwInitialized: IDEA_AUTH_CONTEXT.getSWInitialized(),
                    });
                } catch (e) {
                    event.ports[0].postMessage({
                        error: e,
                    });
                }
                break;
            case Constants.ServiceWorker.IDEA_AUTH_INIT:
                IDEA_AUTH_CONTEXT.initializeAuthContext(event.data.options).then((status) => {
                    if (event.ports && event.ports.length > 0) {
                        event.ports[0].postMessage({
                            status: status,
                        });
                    }
                });
                break;
            case Constants.ServiceWorker.IDEA_AUTH_TOKEN_CLAIMS:
                try {
                    event.ports[0].postMessage({
                        claims: IDEA_AUTH_CONTEXT.getClaims(),
                    });
                } catch (e) {
                    event.ports[0].postMessage({
                        error: e,
                    });
                }
                break;
            case Constants.ServiceWorker.IDEA_AUTH_ACCESS_TOKEN:
                IDEA_AUTH_CONTEXT.getAccessToken()
                    .then((accessToken) => {
                        event.ports[0].postMessage({
                            accessToken: accessToken,
                        });
                    })
                    .catch((error) => {
                        event.ports[0].postMessage({
                            error: error,
                        });
                    });
                break;
            case Constants.ServiceWorker.IDEA_CLIENT_ID:
                try {
                    event.ports[0].postMessage({
                        clientId: IDEA_AUTH_CONTEXT.getClientId(),
                    });
                } catch (e) {
                    event.ports[0].postMessage({
                        error: e,
                    });
                }
                break;
            case Constants.ServiceWorker.IDEA_AUTH_IS_LOGGED_IN:
                IDEA_AUTH_CONTEXT.isLoggedIn()
                    .then((status) => {
                        event.ports[0].postMessage({
                            status: status,
                        });
                    })
                    .catch((error) => {
                        event.ports[0].postMessage({
                            error: error,
                        });
                    });
                break;
            case Constants.ServiceWorker.IDEA_AUTH_DEBUG:
                IDEA_AUTH_CONTEXT.printDebugInfo();
                break;
            case Constants.ServiceWorker.IDEA_AUTH_LOGOUT:
                IDEA_AUTH_CONTEXT.logout()
                    .then((status) => {
                        event.ports[0].postMessage({
                            status: status,
                        });
                    })
                    .catch((error) => {
                        event.ports[0].postMessage({
                            error: error,
                        });
                    });
                break;
            case Constants.ServiceWorker.IDEA_HTTP_FETCH:
                IDEA_AUTH_CONTEXT.fetch(event.data.options.url, event.data.options.options, typeof event.data.options.isPublic !== "undefined" ? event.data.options.isPublic : false)
                    .then((response) => {
                        event.ports[0].postMessage({
                            response: response,
                        });
                    })
                    .catch((error) => {
                        event.ports[0].postMessage({
                            error: error,
                        });
                    });
                break;
            case Constants.ServiceWorker.IDEA_API_INVOCATION:
                if (event.data.options.request.header.namespace === "Auth.InitiateAuth") {
                    IDEA_AUTH_CONTEXT.initiateAuth(event.data.options.request)
                        .then((result) => {
                            event.ports[0].postMessage({
                                response: result,
                            });
                        })
                        .catch((error) => {
                            event.ports[0].postMessage({
                                error: error,
                            });
                        });
                } else {
                    IDEA_AUTH_CONTEXT.invoke(event.data.options.url, event.data.options.request, event.data.options.isPublic)
                        .then((result) => {
                            event.ports[0].postMessage({
                                response: result,
                            });
                        })
                        .catch((error) => {
                            event.ports[0].postMessage({
                                error: error,
                            });
                        });
                }
                break;
        }
    }
});
