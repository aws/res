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
import { THROTTLE_ERROR } from "../common/error-codes";

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
        const onboardedFileSystemIdentifiers: string[] = this._getOnboardedFileSystemIdentifiers(sharedStorageSettings);

        const [listEFSResult, ontapFileSystems, lustreFileSystems] = await Promise.all([
            this.listEFSFileSystemsForOnboard(aws_region, vpc_id, [...onboardedFileSystemIdentifiers, ...justOnboardedFS]),
            this.listOntapFileSystemsForOnboard(aws_region, vpc_id, [...onboardedFileSystemIdentifiers, ...justOnboardedFS]),
            this.listLustreFileSystemsForOnboard(aws_region, vpc_id, [...onboardedFileSystemIdentifiers, ...justOnboardedFS])
        ]);

        const efs = listEFSResult.map((id: string) => {
            return { efs: { FileSystemId: id } };
        });

        return {
            fsx_ontap: ontapFileSystems,
            fsx_lustre: lustreFileSystems,
            efs,
        };
    }

    async listEFSFileSystemsForOnboard(aws_region: string, vpc_id: string, onboardedFS: string[]): Promise<string[]> {
        const fileSystemsResult = await this.proxyClient.listEFS({AWSRegion: aws_region});
        const onboardedFilesystemIds = onboardedFS.filter(id => !id.includes(':'));
        const fileSystemForOnboard = fileSystemsResult.FileSystems.filter((fileSystem: EFS) => !onboardedFilesystemIds.includes(fileSystem.FileSystemId));
        const fileSystemIDsAvailableForOnboard = fileSystemForOnboard.filter((fileSystem: EFS) => fileSystem.LifeCycleState == "available").map((fileSystem: EFS) => fileSystem.FileSystemId);

        const fileSystemIDsAvailableForOnboardInVpc: string[] = [];

        const describeMountTargetWithRetry = async (fileSystemId: string): Promise<DescribeMountTargetResult | null> => {
            const maxRetries = 5;
            const baseDelay = 100;

            for (let attempt = 0; attempt < maxRetries; attempt++) {
                try {
                    const backoffDelay = baseDelay * Math.pow(2, attempt) + (Math.random() * 100);
                    await new Promise(resolve => setTimeout(resolve, backoffDelay));
                    const response: any = await this.proxyClient.describeEFSMountTarget({
                        AWSRegion: aws_region,
                        FileSystemId: fileSystemId
                    });

                    if (response && response.success === false) {
                        if (response.error_code !== THROTTLE_ERROR) {
                            console.error(`Failed to describe mount target for ${fileSystemId}:`, response);
                            return null;
                        }
                        else if (attempt === maxRetries - 1) {
                            console.error(`Failed to describe mount target for ${fileSystemId} after ${maxRetries} attempts:`, response);
                            return null;
                        } else {
                            console.info(`Hitting throttling when describe mount target for ${fileSystemId}, retrying...`);
                            continue;
                        }
                    } else {
                        return response
                    }
                } catch (error: any) {
                    console.error(`Failed to describe mount target for ${fileSystemId}:`, error);
                    return null;
                }
            }
            return null;
        };

        // describeMountTarget for EFS file systems in batches with retry
        const batchSize = 5;
        for (let i = 0; i < fileSystemIDsAvailableForOnboard.length; i += batchSize) {
            const batch = fileSystemIDsAvailableForOnboard.slice(i, i + batchSize);

            // Process current batch in parallel
            const batchResults = await Promise.all(
                batch.map(fileSystemId => describeMountTargetWithRetry(fileSystemId))
            );

            // Process current batch results
            batchResults.forEach((mountTargetResult) => {
                if (mountTargetResult) {
                    const targetInVPC = mountTargetResult.MountTargets.filter(
                        (mountTarget: MountTarget) => mountTarget.VpcId == vpc_id
                    );

                    if (targetInVPC.length > 0) {
                        fileSystemIDsAvailableForOnboardInVpc.push(targetInVPC[0].FileSystemId);
                    }
                }
            });
        }

        return fileSystemIDsAvailableForOnboardInVpc;
    }

    async listOntapFileSystemsForOnboard(aws_region: string, vpc_id: string, onboardedFS: string[]): Promise<FSxONTAPFileSystem[]> {
        const availableOntapFileSystems = await this._getAvailableFsxFileSystems(aws_region, vpc_id, "ONTAP");

        const ontapFileSystemIds = availableOntapFileSystems.map((fileSystem: FSx) => fileSystem.FileSystemId);

        if (ontapFileSystemIds.length === 0) {
            return [];
        }

        const [ontapSVMResults, ontapVolumeResults] = await Promise.all([
            this.proxyClient.listFSxSVM({AWSRegion: aws_region, FileSystemIds: ontapFileSystemIds}),
            this.proxyClient.listFSxVolumes({AWSRegion: aws_region, FileSystemIds: ontapFileSystemIds})
        ]);

        const fileSystemIdWithSVM = ontapSVMResults.StorageVirtualMachines
            .filter((svm: SVM) => svm.Lifecycle === Constants.FSX_CREATED_STATUS)
            .map((svm: SVM) => svm.FileSystemId);

        const allOnboardedVolumeIdentifiers = new Set(
            onboardedFS.filter(id => id.includes(':'))
        );

        // Filter out volumes that are already onboarded using volume-level checking
        const availableVolumes = ontapVolumeResults.Volumes.filter((volume: Volume) => {
            if (volume.Lifecycle !== Constants.FSX_CREATED_STATUS || !fileSystemIdWithSVM.includes(volume.FileSystemId)) {
                return false;
            }
            const volumeIdentifier = `${volume.FileSystemId}:${volume.VolumeId}`;
            return !allOnboardedVolumeIdentifiers.has(volumeIdentifier);
        });

        const availableOntapFileSystemIds = Array.from(new Set(availableVolumes.map((volume: Volume) => volume.FileSystemId)));

        const SVMByFileSystem = _.groupBy(ontapSVMResults.StorageVirtualMachines, "FileSystemId");
        const VolumeByFileSystem = _.groupBy(availableVolumes, "FileSystemId");

        return availableOntapFileSystemIds.map((fileSystemId: string) => {
            const availableVolumesForFS = VolumeByFileSystem[fileSystemId];
            const svmIdsWithAvailableVolumes = new Set(
                availableVolumesForFS.map(volume => {
                    const svmId = (volume as any).OntapConfiguration?.StorageVirtualMachineId;
                    return svmId;
                }).filter(svmId => svmId)
            );

            // Only include SVMs that have available volumes
            const filteredSVMs = SVMByFileSystem[fileSystemId].filter((svm: SVM) =>
                svmIdsWithAvailableVolumes.has(svm.StorageVirtualMachineId)
            );

            return {
                filesystem: { FileSystemId: fileSystemId },
                svm: filteredSVMs.map((svm: SVM) => ({ storage_virtual_machine: svm })),
                volume: availableVolumesForFS.map((volume: Volume) => ({ volume })),
            };
        });
    }

    async listLustreFileSystemsForOnboard(aws_region: string, vpc_id: string, onboardedFS: string[]): Promise<FSxLUSTREFileSystem[]> {
        const onboardedFilesystemIds = onboardedFS.filter(id => !id.includes(':'));
        const availableLustreFileSystems = await this._getAvailableFsxFileSystems(aws_region, vpc_id, "LUSTRE", onboardedFilesystemIds);
        return availableLustreFileSystems.map((fileSystem: FSx): FSxLUSTREFileSystem => ({ filesystem: fileSystem }));
    }

    private async _getAvailableFsxFileSystems(aws_region: string, vpc_id: string, fileSystemType: string, onboardedFS?: string[]): Promise<FSx[]> {
        const fileSystemsResult = await this.proxyClient.listFSx({AWSRegion: aws_region});
        return fileSystemsResult.FileSystems.filter(
            (fileSystem: FSx) => {
                const matchesType = fileSystem.FileSystemType === fileSystemType;
                const inVPC = fileSystem.VpcId === vpc_id;
                const isAvailable = fileSystem.Lifecycle === "AVAILABLE";
                const notOnboarded = !onboardedFS || !onboardedFS.includes(fileSystem.FileSystemId);

                return matchesType && inVPC && isAvailable && notOnboarded;
            }
        );
    }

    _getOnboardedFileSystemIdentifiers(sharedStorageModule: any): string[] {
        const allIdentifiers: string[] = [];

        for (const [key, value] of Object.entries(sharedStorageModule.settings)) {
            if (typeof value === "object" && value !== null) {
                // EFS and Lustre - use filesystem IDs
                const efsConfig = _.get(value, Constants.SHARED_STORAGE_PROVIDER_EFS);
                if (efsConfig && efsConfig.file_system_id) {
                    allIdentifiers.push(efsConfig.file_system_id);
                }

                const lustreConfig = _.get(value, Constants.SHARED_STORAGE_PROVIDER_FSX_LUSTRE);
                if (lustreConfig && lustreConfig.file_system_id) {
                    allIdentifiers.push(lustreConfig.file_system_id);
                }

                // ONTAP - use volume identifiers
                const ontapConfig = _.get(value, Constants.SHARED_STORAGE_PROVIDER_FSX_NETAPP_ONTAP);
                if (ontapConfig) {
                    const fileSystemId = _.get(ontapConfig, 'file_system_id');
                    const volumeId = _.get(ontapConfig, 'volume.volume_id');
                    if (fileSystemId && volumeId) {
                        allIdentifiers.push(`${fileSystemId}:${volumeId}`);
                    }
                }
            }
        }

        return allIdentifiers;
    }
}

export default ProxyService;
