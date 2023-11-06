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

// This lets the app load faster on subsequent visits in production, and gives
// it offline capabilities. However, it also means that developers (and users)
// will only see deployed updates on subsequent visits to a page, after all the
// existing tabs open on the page have been closed, since previously cached
// resources are updated in the background.

// To learn more about the benefits of this model and instructions on how to
// opt-in, read https://cra.link/PWA

import IdeaException from "./common/exceptions";

const isLocalhost = Boolean(
    window.location.hostname === "localhost" ||
        // [::1] is the IPv6 localhost address.
        window.location.hostname === "[::1]" ||
        // 127.0.0.0/8 are considered localhost for IPv4.
        window.location.hostname.match(/^127(?:\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)){3}$/)
);

type Config = {
    onSuccess: (registration: ServiceWorkerRegistration) => void;
    onUpdate: (registration: ServiceWorkerRegistration) => void;
    onReady: (registration: ServiceWorkerRegistration) => void;
    onError: (error: any) => void;
};

export function register(config: Config) {
    if (process.env.NODE_ENV === "production" && "serviceWorker" in navigator) {
        const publicUrl = new URL(process.env.PUBLIC_URL, window.location.href);
        if (publicUrl.origin !== window.location.origin) {
            config.onError(
                new IdeaException({
                    errorCode: "SERVICE_WORKER_INITIALIZATION_FAILED",
                    message: "Service worker won't work if PUBLIC_URL is on a different origin " + "from what our page is served on. This might happen if a CDN is used to " + "serve assets; see https://github.com/facebook/create-react-app/issues/2374",
                })
            );
            return;
        }

        window.addEventListener("load", () => {
            const swUrl = `${process.env.PUBLIC_URL}/service-worker.js`;

            if (isLocalhost) {
                // This is running on localhost. Let's check if a service worker still exists or not.
                checkValidServiceWorker(swUrl, config);
            } else {
                // Is not localhost. Just register service worker
                registerValidSW(swUrl, config);
            }
        });
    } else {
        config.onError({
            errorCode: "SERVICE_WORKER_INITIALIZATION_FAILED",
            message: "Service worker is not supported in development mode",
        });
    }
}

function registerValidSW(swUrl: string, config: Config) {
    navigator.serviceWorker.ready.then((registration) => {
        config.onReady(registration);
    });

    navigator.serviceWorker
        .register(swUrl)
        .then((registration) => {
            registration.onupdatefound = () => {
                const installingWorker = registration.installing;
                if (installingWorker == null) {
                    return;
                }
                installingWorker.onstatechange = () => {
                    if (installingWorker.state === "installed") {
                        if (navigator.serviceWorker.controller) {
                            config.onUpdate(registration);
                        } else {
                            config.onSuccess(registration);
                        }
                    }
                };
            };
        })
        .catch((error) => {
            config.onError(error);
        });
}

function checkValidServiceWorker(swUrl: string, config: Config) {
    // Check if the service worker can be found. If it can't reload the page.
    fetch(swUrl, {
        headers: { "Service-Worker": "script" },
    })
        .then((response) => {
            // Ensure service worker exists, and that we really are getting a JS file.
            const contentType = response.headers.get("content-type");
            if (response.status === 404 || (contentType != null && contentType.indexOf("javascript") === -1)) {
                // No service worker found. Probably a different app. Reload the page.
                navigator.serviceWorker.ready.then((registration) => {
                    registration.unregister().then(() => {
                        window.location.reload();
                    });
                });
            } else {
                // Service worker found. Proceed as normal.
                registerValidSW(swUrl, config);
            }
        })
        .catch(() => {
            console.log("No internet connection found. App is running in offline mode.");
        });
}

export function unregister() {
    if ("serviceWorker" in navigator) {
        navigator.serviceWorker.ready
            .then((registration) => {
                registration.unregister().finally();
            })
            .catch((error) => {
                console.error(error.message);
            });
    }
}
