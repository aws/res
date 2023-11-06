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

import dot from "dot-object";
import Utils from "./utils";
import { Constants } from "./constants";
import { AppContext } from "./index";

export class SharedStorageFileSystem {
    name: string;
    sharedStorage: any;

    constructor(name: string, sharedStorage: any) {
        this.name = name;
        this.sharedStorage = sharedStorage;
    }

    getName(): string {
        return this.name;
    }

    getTitle(): string {
        let title = dot.pick("title", this.sharedStorage);
        if (Utils.isEmpty(title)) {
            // backward compat
            const name = this.getName();
            switch (name) {
                case 'internal':
                    title = 'Applications'
                    break
                case 'home':
                    title = 'User Home Directories'
                    break
                default:
                    title = name;
                    break;
            }
        }
        return title;
    }

    getProvider(): string {
        return dot.pick("provider", this.sharedStorage);
    }

    isEfs(): boolean {
        return this.getProvider() === Constants.SHARED_STORAGE_PROVIDER_EFS;
    }

    isFsxCache(): boolean {
        return this.getProvider() === Constants.SHARED_STORAGE_PROVIDER_FSX_CACHE;
    }

    isFsxLustre(): boolean {
        return this.getProvider() === Constants.SHARED_STORAGE_PROVIDER_FSX_LUSTRE;
    }

    isFsxOpenZfs(): boolean {
        return this.getProvider() === Constants.SHARED_STORAGE_PROVIDER_FSX_OPENZFS;
    }

    isFsxNetAppOntap(): boolean {
        return this.getProvider() === Constants.SHARED_STORAGE_PROVIDER_FSX_NETAPP_ONTAP;
    }

    isFsxWindowsFileServer(): boolean {
        return this.getProvider() === Constants.SHARED_STORAGE_PROVIDER_FSX_WINDOWS_FILE_SERVER;
    }

    isVolumeApplicable(): boolean {
        return this.isFsxNetAppOntap() || this.isFsxOpenZfs();
    }

    getProviderTitle(): string {
        return Utils.getFileSystemProviderTitle(this.getProvider());
    }

    isExistingFileSystem(): boolean {
        const provider = this.getProvider();
        return Utils.asBoolean(dot.pick(`${provider}.use_existing_fs`, this.sharedStorage));
    }

    getMountDirectory(): string {
        return dot.pick("mount_dir", this.sharedStorage);
    }

    getMountDrive(): string {
        return dot.pick("mount_drive", this.sharedStorage)
    }

    getFileShareName(): string {
        const provider = this.getProvider();
        return dot.pick(`${provider}.volume.cifs_share_name`, this.sharedStorage);
    }

    hasMountDrive(): boolean {
        return Utils.isNotEmpty(this.getMountDrive());
    }

    hasMountDirectory(): boolean {
        return this.getMountDirectory() != null;
    }

    getMountOptions(): string {
        const mount_options = dot.pick("mount_options", this.sharedStorage);
        if (Utils.isNotEmpty(mount_options)) {
            return mount_options;
        }
        if (this.isEfs()) {
            return "nfs4 nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport 0 0";
        } else if (this.isFsxLustre()) {
            return "lustre defaults,noatime,flock,_netdev 0 0";
        } else if (this.isFsxNetAppOntap()) {
            return "nfs4 nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport 0 0";
        } else if (this.isFsxOpenZfs()) {
            return "nfs4 nfsvers=4.1,rsize=1048576,wsize=1048576,timeo=600 0 0";
        }
        return "";
    }

    getMountName(): string {
        const provider = this.getProvider();
        return dot.pick(`${provider}.mount_name`, this.sharedStorage);
    }

    getLustreVersion(): string {
        const provider = this.getProvider();
        return dot.pick(`${provider}.version`, this.sharedStorage);
    }

    getScope(): string[] {
        const scope = dot.pick("scope", this.sharedStorage);
        if (Utils.isEmpty(scope)) {
            return ["cluster"];
        }
        return scope;
    }

    isScopeProjects(): boolean {
        return this.getScope().includes("project");
    }

    getProjects(): string[] {
        return dot.pick("projects", this.sharedStorage);
    }

    isScopeModule(): boolean {
        return this.getScope().includes("module");
    }

    getModules(): string[] {
        return dot.pick("modules", this.sharedStorage);
    }

    isScopeQueueProfile(): boolean {
        return AppContext.get().getClusterSettingsService().isSchedulerDeployed() && this.getScope().includes("scheduler:queue-profile");
    }

    getQueueProfiles(): string[] {
        return dot.pick("queue_profiles", this.sharedStorage);
    }

    getFileSystemId(): string {
        const provider = this.getProvider();
        return dot.pick(`${provider}.file_system_id`, this.sharedStorage);
    }

    getFileSystemDns(): string {
        const provider = this.getProvider();
        return dot.pick(`${provider}.dns`, this.sharedStorage);
    }

    getSvmId(): string {
        const provider = this.getProvider();
        return dot.pick(`${provider}.svm.svm_id`, this.sharedStorage);
    }

    getSvmSmbDns(): string {
        const provider = this.getProvider();
        return dot.pick(`${provider}.svm.smb_dns`, this.sharedStorage);
    }

    getSvmNfsDns(): string {
        const provider = this.getProvider();
        return dot.pick(`${provider}.svm.nfs_dns`, this.sharedStorage);
    }

    getSvmManagementDns(): string {
        const provider = this.getProvider();
        return dot.pick(`${provider}.svm.management_dns`, this.sharedStorage);
    }

    getSvmIscsiDns(): string {
        const provider = this.getProvider();
        return dot.pick(`${provider}.svm.iscsi_dns`, this.sharedStorage);
    }

    getVolumeId(): string {
        const provider = this.getProvider();
        if (this.isFsxNetAppOntap()) {
            return dot.pick(`${provider}.volume.volume_id`, this.sharedStorage);
        } else {
            return dot.pick(`${provider}.volume_id`, this.sharedStorage);
        }
    }

    getVolumePath(): string {
        const provider = this.getProvider();
        if (this.isFsxNetAppOntap()) {
            return dot.pick(`${provider}.volume.volume_path`, this.sharedStorage);
        } else {
            return dot.pick(`${provider}.volume_path`, this.sharedStorage);
        }
    }

    getVolumeSecurityStyle(): string {
        const provider = this.getProvider();
        return dot.pick(`${provider}.volume.security_style`, this.sharedStorage);
    }
}
