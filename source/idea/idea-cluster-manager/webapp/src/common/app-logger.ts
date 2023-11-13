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

import Utils from "./utils";

const LogLevel = {
    OFF: 0,
    ERROR: 1,
    WARN: 2,
    INFO: 3,
    DEBUG: 4,
    TRACE: 5,
};

const LogLevelName: { [k: number]: string } = {
    0: "OFF",
    1: "ERROR",
    2: "WARN",
    3: "INFO",
    4: "DEBUG",
    5: "TRACE",
};

const KEY_LOG_LEVEL = "idea.log-level";

export interface AppLoggerProps {
    name: string;
    default_log_level?: number;
}

/***
 * AppLoger class as a central logging function across IDEA frontend components
 *
 * To enable debug logging in production environments:
 *  1. navigate to browser menu-> developer tools -> console
 *  2. type: localStorage.setItem('idea.log-level', '4') to enable debug logging.
 *  3. reload the page
 *
 * Roadmap:
 * * Front end logs can be routed to cloud watch in a future release to track frontend activity and errors.
 */
class AppLogger {
    private readonly name: string;
    private readonly logLevel: number;

    constructor(props: AppLoggerProps) {
        this.name = props.name;

        if (typeof props.default_log_level !== "undefined") {
            // window reference is not available in service worker, so default log level is passed to ServiceWorker during IDEA_APP_INIT
            // which in turn is passed to AppLoggerProps by AuthenticationContext that runs within a service worker
            this.logLevel = Utils.asNumber(props.default_log_level, LogLevel.INFO);
        } else if (typeof window !== "undefined" && typeof localStorage !== "undefined") {
            // for all other components (not initialized in service worker) window reference will be available and initialize default log level from app data
            const defaultLogLevel = Utils.asNumber(window.idea.app.default_log_level, LogLevel.INFO);
            // local storage reference is not available in service worker.
            this.logLevel = Utils.asNumber(localStorage.getItem(KEY_LOG_LEVEL), defaultLogLevel);
        } else {
            this.logLevel = LogLevel.INFO;
        }
    }

    private getLogLevel(logLevel: number): string {
        let result = LogLevelName[logLevel];
        if (result == null) {
            return "UNKNOWN";
        }
        return result;
    }

    private getLogTag(logLevel: number): string {
        return `[${this.getLogLevel(logLevel)}] [${new Date().toISOString()}] [${this.name}]`;
    }

    isEnabled(): boolean {
        return this.logLevel > LogLevel.OFF;
    }

    isError(): boolean {
        return this.logLevel >= LogLevel.ERROR;
    }

    isWarn(): boolean {
        return this.logLevel >= LogLevel.WARN;
    }

    isInfo(): boolean {
        return this.logLevel >= LogLevel.INFO;
    }

    isDebug(): boolean {
        return this.logLevel >= LogLevel.DEBUG;
    }

    isTrace(): boolean {
        return this.logLevel >= LogLevel.TRACE;
    }

    error(message?: any, ...optionalParams: any[]) {
        if (this.logLevel < LogLevel.ERROR) {
            return;
        }
        console.error(this.getLogTag(LogLevel.ERROR), message, ...optionalParams);
    }

    warn(message?: any, ...optionalParams: any[]) {
        if (this.logLevel < LogLevel.WARN) {
            return;
        }
        console.warn(`${this.getLogTag(LogLevel.WARN)} ${message}`, ...optionalParams);
    }

    info(message?: any, ...optionalParams: any[]) {
        if (this.logLevel < LogLevel.INFO) {
            return;
        }
        console.info(`${this.getLogTag(LogLevel.INFO)} ${message}`, ...optionalParams);
    }

    debug(message?: any, ...optionalParams: any[]) {
        if (this.logLevel < LogLevel.DEBUG) {
            return;
        }
        console.log(`${this.getLogTag(LogLevel.DEBUG)} ${message}`, ...optionalParams);
    }

    trace(message?: any, ...optionalParams: any[]) {
        if (this.logLevel < LogLevel.TRACE) {
            return;
        }
        console.log(`${this.getLogTag(LogLevel.TRACE)} ${message}`, ...optionalParams);
    }
}

export default AppLogger;
