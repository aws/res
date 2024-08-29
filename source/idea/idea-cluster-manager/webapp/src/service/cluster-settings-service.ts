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

import { ClusterSettingsClient } from "../client";
import { Constants, ErrorCodes } from "../common/constants";
import { UNAUTHORIZED_ACCESS } from "../common/error-codes";
import IdeaException from "../common/exceptions";
import Utils from "../common/utils";

export interface ClusterSettingsServiceProps {
    clusterSettings: ClusterSettingsClient;
}

class ClusterSettingsService {
    private props: ClusterSettingsServiceProps;
    clusterModules: any;
    globalSettings: any;
    moduleSettings: any;
    instanceTypes: any[];
    clusterName: string;
    clusterLocale: string;
    clusterTimezone: string;
    clusterHomeDir: string;

    constructor(props: ClusterSettingsServiceProps) {
        this.props = props;
        this.clusterModules = [];
        this.moduleSettings = {};
        this.instanceTypes = [];
        this.clusterName = "";
        this.clusterLocale = "en-US";
        this.clusterTimezone = "UTC";
        this.clusterHomeDir = "";
    }

    initialize(): Promise<boolean> {
        return this.props.clusterSettings
            .listClusterModules({})
            .then((result) => {
                this.clusterModules = result.listing;
                return this.props.clusterSettings.getModuleSettings({
                    module_id: Constants.MODULE_GLOBAL_SETTINGS,
                });
            })
            .then((result) => {
                this.globalSettings = result.settings;
                return this.getModuleSettings(Constants.MODULE_CLUSTER);
            })
            .then((clusterSettings) => {
                this.clusterLocale = clusterSettings.locale.replace("_", "-");
                this.clusterTimezone = clusterSettings.timezone;
                this.clusterName = clusterSettings.cluster_name;
                return this.getModuleSettings(Constants.MODULE_SHARED_STORAGE);
            })
            .then((sharedStorageSettings) => {
                this.clusterHomeDir = `${sharedStorageSettings.internal.mount_dir}/${this.clusterName}`;
                return true;
            })
            .catch((error) => {
                console.error(error);
                //This is the first API call which happens from the client side
                //If the user is disable and gets unauthorized access,
                //Redirect it to /sso which will invoke sign out for user
                if (error.errorCode == UNAUTHORIZED_ACCESS) {
                    if (Utils.isSsoEnabled()) {
                        window.location.href = "/sso"
                    }
                }
                return false;
            });
    }

    fetchInstanceTypes(): Promise<boolean> {
        return this.props.clusterSettings.describeInstanceTypes({}).then((result) => {
            this.instanceTypes = result.instance_types;
            return true;
        });
    }

    getVirtualDesktopSettings(cached: boolean = true): Promise<any> {
        if (!this.isVirtualDesktopDeployed()) {
            return Promise.resolve({});
        }
        return this.getModuleSettings(Constants.MODULE_VIRTUAL_DESKTOP_CONTROLLER, cached);
    }

    getSchedulerSettings(): Promise<any> {
        if (!this.isSchedulerDeployed()) {
            return Promise.resolve({});
        }
        return this.getModuleSettings(Constants.MODULE_SCHEDULER);
    }

    getModuleSetId(): string {
        return window.idea.app.module_set;
    }

    getModuleSet(): any {
        if (this.globalSettings != null){
            return this.globalSettings.module_sets[this.getModuleSetId()];
        }
        return null;
    }

    getModuleId(name: string): string | null {
        const moduleSet = this.getModuleSet();
        if (moduleSet!= null && name in moduleSet) {
            return moduleSet[name].module_id;
        }
        return null;
    }

    getModuleSettings(name: string, cached: boolean = true): Promise<any> {
        if (cached && name in this.moduleSettings) {
            return Promise.resolve(this.moduleSettings[name]);
        }
        if (name === Constants.MODULE_GLOBAL_SETTINGS) {
            return Promise.resolve(this.globalSettings);
        }

        const moduleId = this.getModuleId(name);
        if (moduleId != null) {
            const moduleSet = this.getModuleSet();
            let moduleId = moduleSet[name].module_id;
            return this.props.clusterSettings
                .getModuleSettings({
                    module_id: moduleId,
                })
                .then((result) => {
                    this.moduleSettings[name] = result.settings;
                    return this.moduleSettings[name];
                });
        }

        return Promise.reject(
            new IdeaException({
                errorCode: "MODULE_NOT_FOUND",
                message: `ModuleId not found for module name: ${name}`,
            })
        );
    }

    getClusterTimeZone(): string {
        return this.clusterTimezone;
    }

    getClusterLocale(): string {
        return this.clusterLocale;
    }

    getModuleSetIds(moduleName: string): string[] {
        let result: string[] = [];
        const moduleSets = this.globalSettings.module_sets;
        for (let moduleSetId in moduleSets) {
            const moduleSet = moduleSets[moduleSetId];
            for (let currentModuleName in moduleSet) {
                if (currentModuleName === moduleName) {
                    result.push(moduleSetId);
                }
            }
        }
        return result;
    }

    isModuleEnabled(name: string): boolean {
        if (this.clusterModules) {
            for (let i = 0; i < this.clusterModules.length; i++) {
                let module = this.clusterModules[i];
                if (module.name === name) {
                    return true;
                }
            }
        }
        return false;
    }

    isModuleDeployed(name: string): boolean {
        if (this.clusterModules) {
            for (let i = 0; i < this.clusterModules.length; i++) {
                let module = this.clusterModules[i];
                if (module.name === name) {
                    return module.status === "deployed";
                }
            }
        }
        return false;
    }

    getModuleInfo(name: string): any {
        let moduleId = this.getModuleId(name);
        if (moduleId === null) {
            throw new IdeaException({
                errorCode: ErrorCodes.MODULE_NOT_FOUND,
                message: `Module not found: ${name}`,
            });
        }
        for (let i = 0; i < this.clusterModules.length; i++) {
            let module = this.clusterModules[i];
            if (module.module_id === moduleId) {
                return module;
            }
        }
    }

    isVirtualDesktopEnabled(): boolean {
        return this.isModuleEnabled(Constants.MODULE_VIRTUAL_DESKTOP_CONTROLLER);
    }

    isVirtualDesktopDeployed(): boolean {
        return this.isModuleDeployed(Constants.MODULE_VIRTUAL_DESKTOP_CONTROLLER);
    }

    isSchedulerEnabled(): boolean {
        return this.isModuleEnabled(Constants.MODULE_SCHEDULER);
    }

    isSchedulerDeployed(): boolean {
        return this.isModuleDeployed(Constants.MODULE_SCHEDULER);
    }

    isBastionHostEnabled(): boolean {
        return this.isModuleEnabled(Constants.MODULE_BASTION_HOST);
    }

    isBastionHostDeployed(): boolean {
        return this.isModuleDeployed(Constants.MODULE_BASTION_HOST);
    }

    getInstanceTypes(): Promise<any[]> {
        if (this.instanceTypes.length > 0) {
            return Promise.resolve(this.instanceTypes);
        }
        return this.fetchInstanceTypes().then((_) => {
            return this.instanceTypes;
        });
    }

    getClusterSettings(cached: boolean = true): Promise<any> {
        return this.getModuleSettings(Constants.MODULE_CLUSTER, cached);
    }

    getClusterManagerSettings(cached: boolean = true): Promise<any> {
        return this.getModuleSettings(Constants.MODULE_CLUSTER_MANAGER, cached);
    }

    getDirectoryServiceSettings(): Promise<any> {
        return this.getModuleSettings(Constants.MODULE_DIRECTORY_SERVICE);
    }

    getIdentityProviderSettings(): Promise<any> {
        return this.getModuleSettings(Constants.MODULE_IDENTITY_PROVIDER);
    }

    getSharedStorageSettings(): Promise<any> {
        return this.getModuleSettings(Constants.MODULE_SHARED_STORAGE);
    }

    getClusterHomeDir(): string {
        return this.clusterHomeDir;
    }
}

export default ClusterSettingsService;
