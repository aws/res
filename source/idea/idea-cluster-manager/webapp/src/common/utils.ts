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

import { SocaListingPayload, SocaUserInputParamCondition, SocaUserInputParamMetadata, SocaMemory, SocaAmount, SocaDateRange, SocaUserInputChoice, VirtualDesktopGPU, VirtualDesktopSchedule, VirtualDesktopScheduleType, User, ProjectPermissions, VDIPermissions, Project } from "../client/data-model";
import { IdeaFormFieldRegistry } from "../components/form-field";
import { v4 as uuid } from "uuid";
import { DateRangePickerProps } from "@cloudscape-design/components";
import dot from "dot-object";
import moment from "moment";
import IdeaException from "./exceptions";
import { Constants } from "./constants";
import { ProjectsClient } from "../client";
import AuthzClient from "../client/authz-client";
import AppContext from "./app-context";

const TRUE_VALUES = ["true", "yes", "y"];
const FALSE_VALUES = ["false", "no", "n"];

class Utils {
    static getUUID(): string {
        return uuid();
    }

    static getRandomInt(min: number, max: number): number {
        min = Math.ceil(min);
        max = Math.floor(max);
        // The maximum is exclusive and the minimum is inclusive
        return Math.floor(Math.random() * (max - min) + min);
    }

    static asString(val?: any, def: string = ""): string {
        if (val == null) {
            return def;
        }
        if (typeof val === "string") {
            return val;
        }
        return `${val}`;
    }

    static asStringArray(val?: any): string[] {
        if (val == null) {
            return [];
        }
        if (!Array.isArray(val)) {
            return [Utils.asString(val)];
        }

        const array: any[] = val;
        const result: string[] = [];
        array.forEach((entry) => {
            result.push(Utils.asString(entry));
        });

        return result;
    }

    static asBooleanArray(val?: any): boolean[] {
        if (val == null) {
            return [];
        }
        if (!Array.isArray(val)) {
            return [Utils.asBoolean(val)];
        }

        const array: any[] = val;
        const result: boolean[] = [];
        array.forEach((entry) => {
            result.push(Utils.asBoolean(entry));
        });

        return result;
    }

    static asNumberArray(val?: any): number[] {
        if (val == null) {
            return [];
        }
        if (!Array.isArray(val)) {
            return [Utils.asNumber(val)];
        }

        const array: any[] = val;
        const result: number[] = [];
        array.forEach((entry) => {
            result.push(Utils.asNumber(entry));
        });

        return result;
    }

    static isArrayEqual(array1: string[], array2: string[]): boolean {
        return array1.length === array2.length && array1.every((value, index) => value === array2[index]);
    }

    static asBoolean(value?: any, def: boolean = false): boolean {
        if (value == null) {
            return def;
        }
        if (typeof value === "boolean") {
            return value;
        }
        const stringVal = Utils.asString(value);
        const token = stringVal.trim().toLowerCase();
        if (["true", "yes", "y"].find((val) => val === token)) {
            return true;
        } else if (["false", "no", "n"].find((val) => val === token)) {
            return false;
        }
        return def;
    }

    static asNumber(value?: any, def: number = 0, decimal: boolean = false): number {
        if (value == null) {
            return def;
        }
        if (typeof value === "number") {
            return value;
        }
        if (typeof value === "string") {
            try {
                if (decimal) {
                    return parseFloat(value);
                } else {
                    return parseInt(value, 10);
                }
            } catch (error) {
                return def;
            }
        }
        return def;
    }

    static isListOfRecordStrings(value?: any): boolean {
        let result = true;
        if (value == null) {
            result = false
        } else {
            for (let item of value) {
                if (item == null || typeof item != "object") {
                    result = false;
                }
                Object.keys(item).map((key) => {
                    if (typeof item[key] != "string") {
                        result = false;
                    }
                });
            }
        }
        return result;
    }

    static isListOfAttributeEditorRecords(value?: any): boolean {
        let result = true;
        if (value == null) {
            result = false
        } else {
            for (let item of value) {
                if (item == null || typeof item != "object") {
                    result = false;
                }
                for (let required_key of  [ "key", "value"] ) {
                    if(item[required_key] === null || typeof item[required_key] != "string") {
                        result = false;
                    }
                }
            }
        }
        return result;
    }

    static isEmpty(value?: any): boolean {
        if (value == null) {
            return true;
        }
        if (typeof value === "string") {
            return value.trim().length === 0;
        }
        if (Array.isArray(value)) {
            return value.length === 0;
        }
        if (typeof value === "object") {
            return Object.keys(value).length === 0;
        }
        return false;
    }

    static isNotEmpty(value?: any): boolean {
        return !Utils.isEmpty(value);
    }

    static areAllEmpty(...values: any): boolean {
        if (values == null) {
            return true;
        }
        for (let i = 0; i < values.length; i++) {
            let value = values[i];
            if (Utils.isNotEmpty(value)) {
                return false;
            }
        }
        return true;
    }

    static isAnyEmpty(...values: any): boolean {
        if (values == null) {
            return true;
        }
        for (let i = 0; i < values.length; i++) {
            let value = values[i];
            if (Utils.isEmpty(value)) {
                return true;
            }
        }
        return false;
    }

    static isBoolean(value?: any): boolean {
        if (value == null) {
            return false;
        }
        return typeof value === "boolean";
    }

    static isPositiveInteger(value?: any): boolean {
        if (value == null) {
            return false;
        }
        if (typeof value === "number") {
            return value >= 0;
        }
        if (typeof value === "string") {
            const s = value.trim();
            const num = Number(s);
            return Number.isInteger(num) && num >= 0;
        }
        return false;
    }

    static isTrue(value?: any): boolean {
        if (typeof value === "boolean") {
            return value;
        }
        if (typeof value === "string") {
            return TRUE_VALUES.includes(value.trim().toLowerCase());
        }
        return false;
    }

    static isFalse(value?: any): boolean {
        if (typeof value === "boolean") {
            return !value;
        }
        if (typeof value === "string") {
            return FALSE_VALUES.includes(value.trim().toLowerCase());
        }
        return false;
    }

    static getFilterValueAsString(key: string, payload?: SocaListingPayload): string {
        if (payload == null) {
            return "";
        }
        if (payload.filters == null || payload.filters.length === 0) {
            return "";
        }
        for (let i = 0; i < payload.filters.length; i++) {
            let filter = payload.filters[i];
            if (filter.key === key) {
                return Utils.asString(filter.value);
            }
        }
        return "";
    }

    static canShowFormField(fieldRegistry: IdeaFormFieldRegistry, values: any, when?: SocaUserInputParamCondition) {
        if (when == null) {
            return true;
        }
        if (Utils.areAllEmpty(when.param, when.and, when.or)) {
            return true;
        }

        const getParamMeta = (param: string): SocaUserInputParamMetadata | null => {
            fieldRegistry.list().forEach((field) => {
                if (field.getParamName() === param) {
                    return field.getParamMeta();
                }
            });
            return null;
        };

        if (Utils.isNotEmpty(when.param)) {
            const paramName = when.param!;
            const paramValue = dot.pick(paramName, values);
            if (Utils.isTrue(when.empty) && Utils.isEmpty(paramValue)) {
                return true;
            } else if (Utils.isTrue(when.not_empty) && Utils.isNotEmpty(paramValue)) {
                return true;
            } else if (Utils.isNotEmpty(when.eq) && paramValue === when.eq) {
                return true;
            } else if (Utils.isNotEmpty(when.not_eq) && paramValue !== when.not_eq) {
                return true;
            } else if (Utils.isNotEmpty(when.in) && when.in?.includes(paramValue)) {
                return true;
            } else if (Utils.isNotEmpty(when.not_in) && !when.not_in?.includes(paramValue)) {
                return true;
            } else if (when.starts_with && typeof paramValue === "string" && paramValue.startsWith(when.starts_with!)) {
                return true;
            }

            const param = getParamMeta(paramName);
            if (param != null && (param.data_type === "int" || param.data_type === "float")) {
                const paramFloatVal = parseFloat(paramValue + "");
                if (Utils.isNotEmpty(when.gt) && paramFloatVal > parseFloat(when.gt + "")) {
                    return true;
                } else if (Utils.isNotEmpty(when.gte) && paramFloatVal >= parseFloat(when.gte + "")) {
                    return true;
                } else if (Utils.isNotEmpty(when.lt) && paramFloatVal < parseFloat(when.lt + "")) {
                    return true;
                } else if (Utils.isNotEmpty(when.lte) && paramFloatVal <= parseFloat(when.lte + "")) {
                    return true;
                }
            }

            return false;
        }

        if (Utils.isNotEmpty(when.and)) {
            const and = when.and!;
            for (let i = 0; i < and.length; i++) {
                const condition = and[i];
                if (!Utils.canShowFormField(fieldRegistry, values, condition)) {
                    return false;
                }
            }
            return true;
        }

        if (Utils.isNotEmpty(when.or)) {
            const or = when.or!;
            for (let i = 0; i < or.length; i++) {
                const condition = or[i];
                if (Utils.canShowFormField(fieldRegistry, values, condition)) {
                    return true;
                }
            }
            return false;
        }

        return true;
    }

    static getFormattedGPUManufacturer(gpu?: VirtualDesktopGPU): string {
        if (gpu == null || gpu === "NO_GPU") {
            return "N/A";
        }
        return gpu;
    }

    static getFormattedMemory(memory?: SocaMemory): string {
        if (memory == null) {
            return "-";
        }
        return `${memory.value}${memory.unit}`.toUpperCase();
    }

    static getFormattedAmount(amount?: SocaAmount): string {
        if (amount == null) {
            return "-";
        }
        return `${amount.amount.toFixed(2)} ${amount.unit}`;
    }

    static isArray(value: any): boolean {
        if (value == null) {
            return false;
        }
        return Array.isArray(value);
    }

    static convertToDateRange(value?: DateRangePickerProps.Value | null): SocaDateRange | null {
        if (value == null) {
            return null;
        }
        if (value.type === "absolute") {
            return {
                start: value.startDate,
                end: value.endDate,
            };
        } else {
            const amount = value.amount;
            const unit = value.unit;
            const end = new Date();
            let start = new Date();
            switch (unit) {
                case "second":
                    start.setTime(start.getTime() - amount * 1000);
                    break;
                case "minute":
                    start.setTime(start.getTime() - amount * 60 * 1000);
                    break;
                case "hour":
                    start.setTime(start.getTime() - amount * 60 * 60 * 1000);
                    break;
                case "day":
                    start.setTime(start.getTime() - amount * 24 * 60 * 60 * 1000);
                    break;
                case "week":
                    start.setTime(start.getTime() - amount * 7 * 24 * 60 * 60 * 1000);
                    break;
                case "month":
                    start.setTime(start.getTime() - amount * 30 * 24 * 60 * 60 * 1000);
                    break;
                case "year":
                    start.setTime(start.getTime() - amount * 365 * 24 * 60 * 60 * 1000);
                    break;
            }
            return {
                start: start.toISOString(),
                end: end.toISOString(),
            };
        }
    }

    static getDCVSessionTypes(): SocaUserInputChoice[] {
        const options: SocaUserInputChoice[] = [];
        options.push({
            title: "Virtual",
            value: "VIRTUAL",
        });

        options.push({
            title: "Console",
            value: "CONSOLE",
        });
        return options;
    }

    static getSupportedGPUChoices(gpuList: string[]): SocaUserInputChoice[] {
        const options: SocaUserInputChoice[] = [];
        gpuList.forEach((gpu) => {
            switch (gpu) {
                case "NO_GPU":
                    options.push({
                        title: "N/A",
                        value: "NO_GPU",
                    });
                    break;
                case "AMD":
                    options.push({
                        title: "AMD",
                        value: "AMD",
                    });
                    break;
                case "NVIDIA":
                    options.push({
                        title: "NVIDIA",
                        value: "NVIDIA",
                    });
            }
        });
        return options;
    }

    static generateUserSelectionChoices(users: User[], project?: Project, isAdmin: boolean = true): SocaUserInputChoice[] {
        let choices: SocaUserInputChoice[] = [];
        users?.forEach((user) => {
            // if we are not admin, we don't include users that aren't in the project and our own username
            if (!isAdmin) {
                let isInProject = user.username === AppContext.get().auth().getUsername();
                isInProject = isInProject || (project?.users?.includes(user.username!) ?? false);
                isInProject = isInProject || (user.additional_groups?.some((group) => project?.ldap_groups?.includes(group)) ?? false);
                if (!isInProject) {
                    return;
                }
            }
            choices.push({
                title: user.username,
                description: user.email,
                value: user.username,
            });
        });
        return choices;
    }

    static compare_instance_types = (a: any, b: any): number => {
        let a_InstanceFamily = a.InstanceType.split(".")[0];
        let b_InstanceFamily = b.InstanceType.split(".")[0];
        if (a_InstanceFamily === b_InstanceFamily) {
            // same instance family - sort in reverse memory order
            return b.MemoryInfo.SizeInMiB - a.MemoryInfo.SizeInMiB;
        } else {
            // diff instance family - return alphabetical
            return a_InstanceFamily.toLowerCase().localeCompare(b_InstanceFamily.toLowerCase(), undefined, { numeric: true });
        }
    };

    static generateInstanceTypeListing(instanceTypes: any[] | undefined): SocaUserInputChoice[] {
        if (instanceTypes === undefined)
            return [
                {
                    title: "No instance types available.",
                    disabled: true,
                },
            ];

        let bareMetalChoice: SocaUserInputChoice[] = [];
        let regularChoice: SocaUserInputChoice[] = [];
        instanceTypes.sort(this.compare_instance_types);

        instanceTypes.forEach((instanceType) => {
            let memory;
            if (instanceType.MemoryInfo.SizeInMiB < 1024) {
                memory = `${instanceType.MemoryInfo.SizeInMiB}MiB`;
            } else {
                memory = `${Utils.asNumber(instanceType.MemoryInfo.SizeInMiB / 1024)}GiB`;
            }

            let architectures = "";
            instanceType.ProcessorInfo.SupportedArchitectures.forEach((arch: string) => {
                architectures += arch + " | ";
            });
            architectures = architectures.slice(0, -3);

            let gpus = "";
            instanceType?.GpuInfo?.Gpus?.forEach((gpuInfo: any) => {
                gpus += gpuInfo.Manufacturer + " | ";
            });

            if (gpus.length > 0) {
                gpus = gpus.slice(0, -3);
                gpus = ", GPU: " + gpus;
            }

            let description_value = `vCPUs: ${instanceType.VCpuInfo.DefaultVCpus}${gpus}, Memory: ${memory}, Arch: ${architectures}`;

            let instance_choice = {
                title: instanceType.InstanceType,
                value: instanceType.InstanceType,
                description: description_value,
                disabled: false,
            };

            if (instanceType.BareMetal) {
                bareMetalChoice.push(instance_choice);
            } else {
                regularChoice.push(instance_choice);
            }
        });

        let instanceTypeChoices: SocaUserInputChoice[] = [];
        if (regularChoice.length > 0) {
            instanceTypeChoices.push({
                title: "Regular",
                options: regularChoice,
            });
        }

        if (bareMetalChoice.length > 0) {
            instanceTypeChoices.push({
                title: "Bare Metal",
                options: bareMetalChoice,
            });
        }

        if (instanceTypeChoices.length === 0) {
            instanceTypeChoices.push({
                title: "No instance types available.",
                disabled: true,
            });
        }
        return instanceTypeChoices;
    }

    static getSupportedOSChoices(osList: string[]): SocaUserInputChoice[] {
        const options: SocaUserInputChoice[] = [];
        osList.forEach((os) => {
            options.push({
                title: Utils.getOsTitle(os),
                value: os,
            });
        });
        return options;
    }

    static getScheduleTypeDisplay(schedule_type: VirtualDesktopScheduleType | undefined, working_hours_start: string | undefined, working_hours_end: string | undefined, start_time: string | undefined, end_time: string | undefined): string {
        if (schedule_type === "NO_SCHEDULE") {
            return "No Schedule";
        }

        if (schedule_type === "CUSTOM_SCHEDULE") {
            return `Custom Schedule (${start_time} - ${end_time})`;
        }

        if (schedule_type === "WORKING_HOURS") {
            return `Working Hours (${working_hours_start} - ${working_hours_end})`;
        }

        if (schedule_type === "START_ALL_DAY") {
            return "Start All Day";
        }

        return "Stop All Day";
    }

    static getScheduleDisplay(schedule: VirtualDesktopSchedule | undefined, working_hours_start: string | undefined, working_hours_end: string | undefined): string {
        return Utils.getScheduleTypeDisplay(schedule?.schedule_type, working_hours_start, working_hours_end, schedule?.start_up_time, schedule?.shut_down_time);
    }

    static getOsTitle(name?: string): string {
        switch (name) {
            case "amazonlinux2":
                return "Amazon Linux 2";
            case "rhel8":
                return "RedHat Enterprise Linux 8";
            case "rhel9":
                return "RedHat Enterprise Linux 9";
            case "ubuntu2204":
                return "Ubuntu 22.04";
            case "windows":
                return "Windows";
        }
        return "Unknown";
    }

    static getAwsConsoleParts(awsRegion: string): [string, string, string] {
        let consolePrefix = awsRegion;
        let consoleSuffix = ".aws.amazonaws.com";
        let s3Prefix = "s3.";

        // Determine the consoleParts by AWS region/partition
        switch (true) {
            case /^cn-.*/i.test(awsRegion):
                consolePrefix = "";
                consoleSuffix = ".amazonaws.cn";
                s3Prefix = "";
                break;
            case /^us-gov-.*/i.test(awsRegion):
                consolePrefix = "";
                consoleSuffix = ".amazonaws-us-gov.com";
                s3Prefix = "";
                break;
            // TODO Add support for additional partitions as needed
            default:
                consolePrefix = `${awsRegion}.`;
                consoleSuffix = ".aws.amazon.com";
                s3Prefix = "s3.";
                break;
        }
        return [consolePrefix, consoleSuffix, s3Prefix];
    }

    static getAwsConsoleUrl(awsRegion: string): string {
        let [consolePrefix, consoleSuffix, s3Prefix] = Utils.getAwsConsoleParts(awsRegion);
        // consolePrefix is what proceeds the plainword 'console', including the trailing dot
        // consoleSuffix is what follows the plainword 'console', including the leading dot
        return `https://${consolePrefix}console${consoleSuffix}`;
    }

    static getEc2InstanceUrl(awsRegion: string, instanceId: string): string {
        const consoleUrl = Utils.getAwsConsoleUrl(awsRegion);
        return `${consoleUrl}/ec2/v2/home?region=${awsRegion}#InstanceDetails:instanceId=${instanceId}`;
    }

    static getASGUrl(awsRegion: string, asgName: string): string {
        const consoleUrl = Utils.getAwsConsoleUrl(awsRegion);
        return `${consoleUrl}/ec2/v2/home?region=${awsRegion}#AutoScalingGroupDetails:id=${asgName}`;
    }

    static getSecurityGroupUrl(awsRegion: string, groupId: string): string {
        const consoleUrl = Utils.getAwsConsoleUrl(awsRegion);
        return `${consoleUrl}/ec2/v2/home?region=${awsRegion}#SecurityGroup:groupId=${groupId}`;
    }

    static getSessionManagerConnectionUrl(awsRegion: string, instanceId: string): string {
        const consoleUrl = Utils.getAwsConsoleUrl(awsRegion);
        return `${consoleUrl}/systems-manager/session-manager/${instanceId}?region=${awsRegion}`;
    }

    static getCognitoUserPoolUrl(awsRegion: string, userPoolId: string): string {
        const consoleUrl = Utils.getAwsConsoleUrl(awsRegion);
        return `${consoleUrl}/cognito/v2/idp/user-pools/${userPoolId}/users?region=${awsRegion}`;
    }

    static getS3BucketUrl(awsRegion: string, bucketName: string): string {
        // getS3BucketUrl cannot use getAwsConsoleUrl() as it needs the s3Prefix
        let [consolePrefix, consoleSuffix, s3Prefix] = Utils.getAwsConsoleParts(awsRegion);
        return `https://${s3Prefix}console${consoleSuffix}/s3/buckets/${bucketName}?region=${awsRegion}`;
    }

    static copyToClipBoard(text: string): Promise<boolean> {
        if (!navigator.clipboard) {
            return Promise.resolve(false);
        }
        return navigator.clipboard
            .writeText(text)
            .then(() => {
                return true;
            })
            .catch((error) => {
                console.error(error);
                return false;
            });
    }

    static getDayOfWeek(): string | null {
        const day = new Date().getDay();
        switch (day) {
            case 0:
                return "sunday";
            case 1:
                return "monday";
            case 2:
                return "tuesday";
            case 3:
                return "wednesday";
            case 4:
                return "thursday";
            case 5:
                return "friday";
            case 6:
                return "saturday";
        }
        return null;
    }

    static getDirectoryServiceTitle(provider: string): string {
        switch (provider) {
            case "openldap":
                return "OpenLDAP";
            case "aws_managed_activedirectory":
                return "AWS Managed Microsoft AD";
            case "activedirectory":
                return "Microsoft AD (Self-Hosted or On-Prem)";
        }
        return "Unknown";
    }

    static getDaysBetween(date1: Date, date2: Date): number {
        const m1 = moment(date1);
        const m2 = moment(date2);
        return m1.diff(m2, "days");
    }

    static getUserGroupName(moduleId: string) {
        return `${moduleId}-users-module-group`;
    }

    static getAdministratorGroup(moduleId: string) {
        return `${moduleId}-administrators-module-group`;
    }

    static getModuleId(moduleName: string): string {
        const modules: any = window.idea.app.modules;
        let moduleId: string = "";
        modules.forEach((module: any) => {
            if (moduleName === module.name) {
                moduleId = module.module_id;
                return true;
            }
        });
        return moduleId;
    }

    static getApiContextPath(moduleName: string): string {
        const modules: any = window.idea.app.modules;
        let apiContextPath: string = "";
        modules.forEach((module: any) => {
            if (moduleName === module.name) {
                apiContextPath = module.api_context_path;
                return true;
            }
        });

        // default api context paths for local dev as index.html page is not rendered server side
        if (Utils.isEmpty(apiContextPath)) {
            switch (moduleName) {
                case Constants.MODULE_CLUSTER_MANAGER:
                    apiContextPath = "/cluster-manager/api/v1";
                    break;
                case Constants.MODULE_SCHEDULER:
                    apiContextPath = "/scheduler/api/v1";
                    break;
                case Constants.MODULE_VIRTUAL_DESKTOP_CONTROLLER:
                    apiContextPath = "/vdc/api/v1";
                    break;
            }
        }

        if (Utils.isEmpty(apiContextPath)) {
            throw new IdeaException({
                errorCode: "MODULE_NOT_FOUND",
                message: `Module not found for name: ${moduleName}`,
            });
        }
        return apiContextPath;
    }

    static getFileSystemProviderTitle(provider: string): string {
        switch (provider) {
            case Constants.SHARED_STORAGE_PROVIDER_EFS:
                return "Amazon EFS";
            case Constants.SHARED_STORAGE_PROVIDER_FSX_CACHE:
                return "Amazon File Cache";
            case Constants.SHARED_STORAGE_PROVIDER_FSX_LUSTRE:
                return "Amazon FSx for Lustre";
            case Constants.SHARED_STORAGE_PROVIDER_FSX_NETAPP_ONTAP:
                return "Amazon FSx for NetApp ONTAP ";
            case Constants.SHARED_STORAGE_PROVIDER_FSX_OPENZFS:
                return "Amazon FSx for OpenZFS";
            case Constants.SHARED_STORAGE_PROVIDER_FSX_WINDOWS_FILE_SERVER:
                return "Amazon FSx for Windows File Server";
            default:
                return "Unknown";
        }
    }

    /**
     * try to find Platform based on UserAgent data.
     * approximation based on information available. cannot be guaranteed.
     * source: https://stackoverflow.com/questions/38241480/detect-macos-ios-windows-android-and-linux-os-with-js
     */
    static getPlatform(): string {
        const navigator: any = window.navigator;
        let userAgent = navigator.userAgent;
        let platform = navigator.platform;
        const OSX_TOKENS = ["Macintosh", "MacIntel", "MacPPC", "Mac68K"];
        const WINDOWS_TOKENS = ["Win32", "Win64", "Windows", "WinCE"];
        const IOS_TOKENS = ["iPhone", "iPad", "iPod"];

        let os = "";

        if (OSX_TOKENS.indexOf(platform) !== -1) {
            os = "osx";
        } else if (IOS_TOKENS.indexOf(platform) !== -1) {
            os = "ios";
        } else if (WINDOWS_TOKENS.indexOf(platform) !== -1) {
            os = "windows";
        } else if (/Android/.test(userAgent)) {
            os = "android";
        } else if (/Linux/.test(platform)) {
            os = "linux";
        }

        return os;
    }

    static openNewTab(url: string) {
        const element = document.createElement("a");
        element.setAttribute("href", url);
        element.setAttribute("target", "_blank");
        element.style.display = "none";
        document.body.appendChild(element);
        element.click();
        document.body.removeChild(element);
    }

    static getBanner(version: string): string {
        return `
 '######::'#######: '#####::
 .##    #: ##...  : ##    #:
 :##    #: ##:::  : ##....::
 :######:: #####  :  #####::
 :##  # :: ##:::  :      ##:
 :##   #:: ##     : #    ##:
 '##    #: #######:  #####::

  Research and Engineering Studio
             Version ${version}

`;
    }

    static getDefaultModuleSettings() {
        return [
            {
                deployment_priority: 7,
                module_id: "bastion-host",
                name: "bastion-host",
                title: "Bastion Host",
                type: "stack",
            },
            {
                api_context_path: "/cluster-manager/api/v1",
                deployment_priority: 5,
                module_id: "cluster-manager",
                name: "cluster-manager",
                title: "Cluster Manager",
                type: "app",
            },
            {
                deployment_priority: 2,
                module_id: "cluster",
                name: "cluster",
                title: "Cluster",
                type: "stack",
            },
            {
                deployment_priority: 3,
                module_id: "directoryservice",
                name: "directoryservice",
                title: "Directory Service",
                type: "stack",
            },
            {
                deployment_priority: 3,
                module_id: "identity-provider",
                name: "identity-provider",
                title: "Identity Provider",
                type: "stack",
            },
            {
                api_context_path: "/scheduler/api/v1",
                deployment_priority: 6,
                module_id: "scheduler",
                name: "scheduler",
                title: "Scale-Out Computing",
                type: "app",
            },
            {
                deployment_priority: 4,
                module_id: "shared-storage",
                name: "shared-storage",
                title: "Shared Storage",
                type: "stack",
            },
            {
                api_context_path: "/vdc/api/v1",
                deployment_priority: 6,
                module_id: "vdc",
                name: "virtual-desktop-controller",
                title: "eVDI",
                type: "app",
            },
        ];
    }

    static hideLoadingAnimation() {
        document.getElementById("app-loading")!.style.display = "none";
    }

    static isSsoEnabled(): boolean {
        return typeof window.idea.app.sso !== "undefined" && window.idea.app.sso;
    }

    static getPermissionAsUIString(permission: keyof ProjectPermissions | keyof VDIPermissions): string {
      switch (permission) {
        case "update_personnel":
          return "Update project membership";
        case "update_status":
          return "Update project status";
        case "create_sessions":
          return "Create session";
        case "create_terminate_others_sessions":
          return "Create/Terminate other's session";
        default:
          return "-"
      }
    }

    static getPermissionDescription(permission: keyof ProjectPermissions | keyof VDIPermissions): string {
      switch (permission) {
        case "update_personnel":
          return "Update users and groups associated with a project."
        case "update_status":
          return "Enable or disable a project."
        case "create_sessions":
          return "Create your own session. Users can always terminate their own sessions with or without this permission.";
        case "create_terminate_others_sessions":
          return "Create/Terminate another user's session within a project.";
        default:
          return "-";
      }
    }

    static async getAffectedProjects(projectsClient: ProjectsClient, authzClient: AuthzClient): Promise<{
      affectedProjects: Map<string, number>;
      roleProjectSetMap: Map<string, Set<string>>;
    }> {
      const affectedProjects = new Map<string, number>();
      const roleProjectSetMap = new Map<string, Set<string>>();
  
      const projects = (await projectsClient.listProjects({ })).listing ?? [];
  
      const requests = [];
  
      for (const project of projects) {
        requests.push(
          authzClient.listRoleAssignments({
            resource_key: `${project.project_id!}:project`,
          })
          .then((response) => {
            response.items.forEach(assignment => {
              if (!roleProjectSetMap.has(assignment.role_id)) {
                roleProjectSetMap.set(assignment.role_id, new Set<string>());
              }
        
              const tempSet = roleProjectSetMap.get(assignment.role_id)!;
              tempSet.add(assignment.resource_id);
              affectedProjects.set(assignment.role_id, tempSet.size);
              roleProjectSetMap.set(assignment.role_id, tempSet);
            });
          })
        );
      }
  
      await Promise.all(requests);
      
      return {
        affectedProjects,
        roleProjectSetMap,
      };
    }

    static convertToRelativeTime(
      date: Date | number,
    ): string {
      const timeMs = typeof date === "number" ? date : date.getTime();
      const deltaSeconds = Math.round((timeMs - Date.now()) / 1000);
    
      // one minute, hour, day, week, month, etc in seconds
      const cutoffs = [60, 3600, 86400, 86400 * 7, 86400 * 30, 86400 * 365, Infinity];
      const units: Intl.RelativeTimeFormatUnit[] = ["second", "minute", "hour", "day", "week", "month", "year"];
    
      // Find the appropriate cutoff to divide the ms by for relative time representation
      const unitIndex = cutoffs.findIndex(cutoff => cutoff > Math.abs(deltaSeconds));
      const divisor = unitIndex ? cutoffs[unitIndex - 1] : 1;
      const rtf = new Intl.RelativeTimeFormat('en', { numeric: "auto" });
      return rtf.format(Math.floor(deltaSeconds / divisor), units[unitIndex]);
    }

    static convertToAbsoluteTime(
      date: Date | number,
    ): string {
      return new Intl.DateTimeFormat('en', {
        dateStyle: 'full',
        timeStyle: 'long',
      }).format(date);
    }

    static async fetchProjectsFilteredByVDIPermissions(
      isAdmin: boolean,
      vdiPerm: keyof VDIPermissions
    ): Promise<Project[]> {
      const user = await AppContext.get().auth().getUser();
      const projects = await AppContext.get().client().projects().getUserProjects({
          username: user.username,
      });
      if (isAdmin) {
          return projects.projects ?? [];
      }
      const authzClient: AuthzClient = AppContext.get().client().authz();
      const roles = await authzClient.listRoles({
          include_permissions: true,
      });

      // Create a Set so that there are no duplicates
      const validProjectIds: Set<string> = new Set<string>();

      const vdiRoleAssignments: Promise<void>[] = [];

      // filter out projects based on Role Permissions
      for (const project of projects.projects!) {
          const resource_key = `${project.project_id!}:project`;
          vdiRoleAssignments.push(
              Promise.resolve(authzClient.listRoleAssignments({
                  resource_key,
              })
              .then((roleAssignments) => {
                  for (const roleAssignment of roleAssignments.items) {
                      if (roleAssignment.actor_type === "user") {
                          if (!project.users) project.users = [];
                          project.users.push(roleAssignment.actor_id);
                      }
                      if (roleAssignment.actor_type === "group") {
                          if (!project.ldap_groups) project.ldap_groups = [];
                          project.ldap_groups.push(roleAssignment.actor_id);
                      }
                      let currentUserIsInRole = user.additional_groups?.includes(roleAssignment.actor_id) || roleAssignment.actor_id === user.username!;

                      if (currentUserIsInRole) {
                          const rolePermission = roles.items.find(perm => perm.role_id === roleAssignment.role_id);
                    
                          if (rolePermission?.vdis && (rolePermission.vdis![vdiPerm])) {
                              validProjectIds.add(project.project_id!);
                          }
                      }
                  }
              })
          ));
      }

      await Promise.all(vdiRoleAssignments);
      return projects.projects?.filter(proj => validProjectIds.has(proj.project_id!)) ?? [];
  }
}

export default Utils;
