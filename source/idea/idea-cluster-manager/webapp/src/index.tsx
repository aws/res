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

import React from "react";
import ReactDOM from "react-dom/client";
import { HashRouter } from "react-router-dom";
import "@cloudscape-design/global-styles/index.css";
import "./index.scss";
import IdeaWebPortal from "./App";
import { AppContext } from "./common";
import Utils from "./common/utils";
import * as serviceWorkerRegistration from "./service-worker-registration";
import { ChonkyIconFA } from "chonky-icon-fontawesome";
import AppLogger from "./common/app-logger";

import { setChonkyDefaults } from "chonky";

setChonkyDefaults({ iconComponent: ChonkyIconFA });

declare global {
    interface Window {
        idea: any;
    }
}

const IDEA_RELEASE_VERSION = process.env.REACT_APP_IDEA_RELEASE_VERSION!;

/**
 * load app initialization data from index.html
 * below code block ensures that app init data is available even during development when web-portal is running via `yarn serve`.
 * since index.html is not rendered via cluster-manager app server, app init data is empty and the jinja2 code block is not replaced.
 */
if (window.idea.app_init_data.startsWith("{{") && window.idea.app_init_data.endsWith("}}")) {
    // defaults for local development and testing

    // to test ServiceWorker in development mode:
    //  1. ensure your cluster ALB external endpoint is serving a trusted TLS context. (self-signed certs will not work)
    //  2. yarn build
    //  3. serve -s build (you might need to install serve npm package globally)

    // service workers for local dev can be disabled by setting session_management = 'local-storage'
    // by default, service workers are enabled and local dev mode will fall back to local-storage as service workers cannot be initialized in dev mode.

    // NOTE: session_management is an IDEA specific concept for handling sessions via either saving access and refresh tokens in-memory (within ServiceWorker) or in browser local-storage.
    // when using browser local storage, web portal can be exposed to XSS attacks (https://owasp.org/www-community/attacks/xss/).
    // refer to: https://create-react-app.dev/docs/making-a-progressive-web-app/ for additional documentation on react app support for service workers.

    window.idea.app = {
        sso: false,
        version: IDEA_RELEASE_VERSION,
        title: "Research and Engineering Studio",
        logo: "/logo.png",
        module_set: "default",
        modules: Utils.getDefaultModuleSettings(),
        session_management: "in-memory",
        default_log_level: 3,
    };
} else {
    const appData = JSON.parse(window.atob(window.idea.app_init_data));
    // enable ability to disable sso, even if enabled from server
    const currentUrl = new URL(window.location.href);
    const ssoParam = currentUrl.searchParams.get("sso");
    if (ssoParam != null) {
        appData.sso = Utils.asBoolean(ssoParam);
    }
    window.idea.app = appData;
}

document.title = window.idea.app.title;
if (window.idea.app.logo) {
    document.querySelectorAll(".app-logo").forEach(function (el) {
        el.setAttribute("href", window.idea.app.logo);
    });
}

/**
 * Remove all query params (excluding hash) provided by server or user on initial page load.
 */
const currentUrl = new URL(window.location.href);
if (Utils.isNotEmpty(currentUrl.hash)) {
    window.history.replaceState({}, "", `${currentUrl.origin}${currentUrl.hash}`);
} else {
    window.history.replaceState({}, "", currentUrl.origin);
}

/***
 * Lazy App Initialization after Service Worker is initialized.
 * loading animation is displayed in the initial page load until IdeaAppLayout/AuthLayout is mounted.
 * The IdeaAppLayout/AuthLayout -> componentDidMount() method hides the loading animation
 */

// print app banner
console.log(Utils.getBanner(IDEA_RELEASE_VERSION));

const LOGGER = new AppLogger({
    name: "index.tsx",
});

interface InitializeAppProps {
    serviceWorkerRegistration?: ServiceWorkerRegistration;
}

const initializeApp = (props: InitializeAppProps) => {
    let httpEndpoint;
    let albEndpoint;

    if (currentUrl.origin.startsWith("http://localhost")) {
        httpEndpoint = process.env.REACT_APP_IDEA_HTTP_ENDPOINT!;
        albEndpoint = process.env.REACT_APP_IDEA_ALB_ENDPOINT!;
    } else {
        httpEndpoint = currentUrl.origin;
        albEndpoint = currentUrl.origin;
    }

    if (window.idea.context == null) {
        window.idea.context = new AppContext({
            httpEndpoint: httpEndpoint,
            albEndpoint: albEndpoint,
            releaseVersion: IDEA_RELEASE_VERSION,
            app: window.idea.app,
            serviceWorkerRegistration: props.serviceWorkerRegistration,
        });
    }

    const root = ReactDOM.createRoot(document.getElementById("app") as HTMLElement);

    root.render(
        <HashRouter>
            <IdeaWebPortal />
        </HashRouter>
    );
};

const sessionManagement = Utils.asString(window.idea.app.session_management, "local-storage");
if (sessionManagement === "local-storage") {
    serviceWorkerRegistration.unregister();
    initializeApp({});
} else {
    serviceWorkerRegistration.register({
        onSuccess: () => {
            LOGGER.info("✓ service worker installed");
        },
        onUpdate: () => {
            LOGGER.info("⚠ service worker updates available");
        },
        onReady: (registration) => {
            LOGGER.info("✓ service worker ready");
            initializeApp({
                serviceWorkerRegistration: registration,
            });
        },
        onError: (error) => {
            LOGGER.warn("✗ failed to initialize service worker. ", error);
            LOGGER.info("✓ using local-storage based fallback mode ...");
            initializeApp({});
        },
    });
}
