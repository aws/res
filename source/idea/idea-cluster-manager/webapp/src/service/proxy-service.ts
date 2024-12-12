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

import * as _ from "lodash";
import ProxyClient from "../client/proxy-client";
import ClusterSettingsService from "./cluster-settings-service";
import { ClusterSettingsClient } from "../client";
import { DescribeMountTargetResult, EFS, FSx, FSxLUSTREFileSystem, FSxONTAPFileSystem, ListFileSystemsInVPCResult, MountTarget, SVM, Volume } from "../client/data-model";
import { Constants } from "../common/constants";

class ProxyService {
    private proxyClient: ProxyClient;
    private clusterSettingsService: ClusterSettingsService;
    private clusterSettingsClient: ClusterSettingsClient;

    constructor(proxyClient: ProxyClient, clusterSettingsService: ClusterSettingsService, clusterSettingsClient: ClusterSettingsClient) {
        this.proxyClient = proxyClient;
        this.clusterSettingsService = clusterSettingsService;
        this.clusterSettingsClient = clusterSettingsClient;
    }

    async listFileSystemsForOnboard(justOnboardedFS: string[]): Promise<ListFileSystemsInVPCResult> {
        const clusterSettings = await this.clusterSettingsService.getModuleSettings(Constants.MODULE_CLUSTER);
        const aws_region = clusterSettings.aws.region;
        const vpc_id = clusterSettings.network.vpc_id;
        const sharedStorageSettings: any = await this.clusterSettingsClient.getModuleSettings({ module_id: Constants.MODULE_SHARED_STORAGE });
        const onboardedFileSystemIds: string[] = this._getOnboardedFileSystemIds(sharedStorageSettings);
        const listEFSRequest = this.listEFSFileSystemsForOnboard(aws_region, vpc_id, [...onboardedFileSystemIds, ...justOnboardedFS]);
        const listFSxRequest = this.listFSxSystemsForOnboard(aws_region, vpc_id, [...onboardedFileSystemIds, ...justOnboardedFS]);

        const [listEFSResult, listFSxResult] = await Promise.all([listEFSRequest, listFSxRequest]);

        const efs = listEFSResult.map((id) => {
            return { efs: { FileSystemId: id } };
        });

        return {
            ...listFSxResult,
            efs,
        };
    }

    async listEFSFileSystemsForOnboard(aws_region: string, vpc_id: string, onboardedFS: string[]): Promise<String[]> {
        const fileSystemsResult = await this.proxyClient.listEFS({AWSRegion: aws_region});
        const fileSystemForOnboard = fileSystemsResult.FileSystems.filter((fileSystem: EFS) => !onboardedFS.includes(fileSystem.FileSystemId));
        const fileSystemIDsAvailableForOnboard = fileSystemForOnboard.filter((fileSystem: EFS) => fileSystem.LifeCycleState == "available").map((fileSystem: EFS) => fileSystem.FileSystemId);

        const fileSystemIDsAvailableForOnboardInVpc: string[] = [];
        const mountTargetRequests = fileSystemIDsAvailableForOnboard.map(async (fileSystemId: string): Promise<DescribeMountTargetResult> => {
            return this.proxyClient.describeEFSMountTarget({ AWSRegion: aws_region, FileSystemId: fileSystemId });
        });
        const mountTargetResults = await Promise.all(mountTargetRequests);
        mountTargetResults.forEach((mountTargetResult) => {
            const targetInVPC = mountTargetResult.MountTargets.filter((mountTarget: MountTarget) => mountTarget.VpcId == vpc_id);
            if (targetInVPC.length > 0) {
                fileSystemIDsAvailableForOnboardInVpc.push(targetInVPC[0].FileSystemId);
            }
        });
        return fileSystemIDsAvailableForOnboardInVpc;
    }

    async listFSxSystemsForOnboard(aws_region: string, vpc_id: string, onboardedFS: string[]): Promise<{ fsx_ontap: FSxONTAPFileSystem[]; fsx_lustre: FSxLUSTREFileSystem[] }> {
        const fileSystemsResult = await this.proxyClient.listFSx({AWSRegion: aws_region});
        const fileSystemForOnboard = fileSystemsResult.FileSystems.filter((fileSystem: FSx) => !onboardedFS.includes(fileSystem.FileSystemId) && fileSystem.VpcId === vpc_id && fileSystem.Lifecycle === "AVAILABLE");
        const lustreFileSystemForOnboard = fileSystemForOnboard
            .filter((fileSystem: FSx) => fileSystem.FileSystemType === "LUSTRE")
            .map((fileSystem: FSx): FSxLUSTREFileSystem => {
                return { filesystem: fileSystem };
            });
        const ontapFileSystemIdsForOnboard = fileSystemForOnboard.filter((fileSystem: FSx) => fileSystem.FileSystemType === "ONTAP").map((fileSystem: FSx) => fileSystem.FileSystemId);
        if (ontapFileSystemIdsForOnboard.length === 0) {
            return {
                fsx_ontap: [],
                fsx_lustre: lustreFileSystemForOnboard,
            };
        }
        const ontapSVMRequests = this.proxyClient.listFSxSVM({AWSRegion: aws_region, FileSystemIds: ontapFileSystemIdsForOnboard});
        const ontapVolumeRequests = this.proxyClient.listFSxVolumes({AWSRegion: aws_region, FileSystemIds: ontapFileSystemIdsForOnboard});
        const [ontapSVMResults, ontapVolumeResults] = await Promise.all([ontapSVMRequests, ontapVolumeRequests]);

        const fileSystemIdWithSVM = ontapSVMResults.StorageVirtualMachines.filter((svm: SVM) => svm.Lifecycle === Constants.FSX_CREATED_STATUS).map((svm: SVM) => svm.FileSystemId);
        const fileSystemIdWithSVMAndVolume = Array.from(new Set(ontapVolumeResults.Volumes.filter((volume: Volume) => volume.Lifecycle === Constants.FSX_CREATED_STATUS && fileSystemIdWithSVM.includes(volume.FileSystemId)).map((volume: Volume) => volume.FileSystemId)));

        const SVMByFileSystem = _.groupBy(ontapSVMResults.StorageVirtualMachines, "FileSystemId");
        const VolumeByFileSystem = _.groupBy(ontapVolumeResults.Volumes, "FileSystemId");

        const ontapFileSystemResult: FSxONTAPFileSystem[] = fileSystemIdWithSVMAndVolume.map((fileSystemId: string) => {
            return {
                filesystem: { FileSystemId: fileSystemId },
                svm: SVMByFileSystem[fileSystemId].map((svm: SVM) => {
                    return { storage_virtual_machine: svm };
                }),
                volume: VolumeByFileSystem[fileSystemId].map((volume: Volume) => {
                    return { volume };
                }),
            };
        });
        return Promise.resolve({
            fsx_ontap: ontapFileSystemResult,
            fsx_lustre: lustreFileSystemForOnboard,
        });
    }

    _getOnboardedFileSystemIds(sharedStorageModule: any) {
        const fileSystemTypes = [Constants.SHARED_STORAGE_PROVIDER_EFS, Constants.SHARED_STORAGE_PROVIDER_FSX_LUSTRE, Constants.SHARED_STORAGE_PROVIDER_FSX_NETAPP_ONTAP];
        const allFileSystemIds: string[] = [];
        for (const [key, value] of Object.entries(sharedStorageModule.settings)) {
            if (typeof value === "object" && value !== null) {
                for (const type of fileSystemTypes) {
                    const nestedPath = `${type}.file_system_id`;
                    if (_.has(value, nestedPath)) {
                        allFileSystemIds.push(_.get(value, nestedPath));
                    }
                }
            }
        }
        return allFileSystemIds;
    }
}

export default ProxyService;
