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

import { HpcQueueProfile, SocaJobParams, SocaJob, SocaCapacityType, SocaInstanceTypeOptions } from "../../client/data-model";
import Utils from "../../common/utils";

export class JobParamUtils {
    params: SocaJobParams;

    constructor(params: SocaJobParams) {
        this.params = params;
    }

    isEnableSpot(): boolean {
        if (this.params.spot != null) {
            return this.params.spot;
        }
        return false;
    }

    isScratchStorageEnabled(): boolean {
        if (this.params == null) {
            return false;
        }
        if (this.params.enable_scratch == null) {
            return false;
        }
        return this.params.enable_scratch;
    }

    getScratchStorageProvider(): string | null {
        if (!this.isScratchStorageEnabled()) {
            return null;
        }
        if (this.params.scratch_provider != null) {
            return this.params.scratch_provider;
        }
        return null;
    }

    isScratchEBS(): boolean {
        const scratchProvider = this.getScratchStorageProvider();
        if (scratchProvider == null) {
            return false;
        }
        return scratchProvider === "ebs";
    }

    isScratchFsxLustre(): boolean {
        const scratchProvider = this.getScratchStorageProvider();
        if (scratchProvider == null) {
            return false;
        }
        return scratchProvider === "fsx-lustre-existing" || scratchProvider === "fsx-lustre-new";
    }

    isScratchExistingFsxLustre(): boolean {
        const scratchProvider = this.getScratchStorageProvider();
        if (scratchProvider == null) {
            return false;
        }
        return scratchProvider === "fsx-lustre-existing";
    }

    isScratchNewFsxLustre(): boolean {
        const scratchProvider = this.getScratchStorageProvider();
        if (scratchProvider == null) {
            return false;
        }
        return scratchProvider === "fsx-lustre-new";
    }
}

export class QueueUtils extends JobParamUtils {
    queue: HpcQueueProfile;

    constructor(queue: HpcQueueProfile) {
        super(queue.default_job_params ? queue.default_job_params : {});
        this.queue = queue;
    }

    hasMetrics(): boolean {
        return false;
    }

    getQueueMetric(name: string): number {
        return 0;
    }

    getActiveJobs(): number {
        return this.getQueueMetric("active_jobs");
    }

    getDesiredCapacity(): number {
        return this.getQueueMetric("desired_capacity");
    }

    getOnDemandCapacity(): number {
        return this.getQueueMetric("ondemand_capacity");
    }

    getOnDemandNodes(): number {
        return this.getQueueMetric("ondemand_nodes");
    }

    getSpotCapacity(): number {
        return this.getQueueMetric("spot_capacity");
    }

    getSpotNodes(): number {
        return this.getQueueMetric("spot_nodes");
    }
}

export class JobUtils extends JobParamUtils {
    job: SocaJob;

    constructor(job: SocaJob) {
        super(job.params ? job.params : {});
        this.job = job;
    }

    getCapacityType(): SocaCapacityType | null {
        if (this.job.params == null) {
            return null;
        }
        if (Utils.isTrue(this.job.params.spot)) {
            const spotAllocationCount = Utils.asNumber(this.job.params.spot_allocation_count, 0);
            if (spotAllocationCount === 0) {
                return "spot";
            } else {
                return "mixed";
            }
        } else {
            return "on-demand";
        }
    }

    isSpotCapacity(): boolean {
        const capacityType = this.getCapacityType();
        if (capacityType == null) {
            return false;
        }
        return capacityType === "spot";
    }

    isOnDemandCapacity(): boolean {
        const capacityType = this.getCapacityType();
        if (capacityType == null) {
            return false;
        }
        return capacityType === "on-demand";
    }

    isMixedCapacity(): boolean {
        const capacityType = this.getCapacityType();
        if (capacityType == null) {
            return false;
        }
        return capacityType === "mixed";
    }

    getOnDemandNodes(): number {
        if (this.job.params == null) {
            return 0;
        }
        if (this.isSpotCapacity()) {
            return 0;
        }
        const nodes = Utils.asNumber(this.job.params.nodes, 0);
        const spotAllocationCount = Utils.asNumber(this.job.params.spot_allocation_count, 0);
        return nodes - spotAllocationCount;
    }

    getOnDemandCapacity(): number {
        return this.getOnDemandNodes() * this.getWeightedCapacity();
    }

    getDesiredNodes(): number {
        if (this.job.params == null) {
            return 0;
        }
        return Utils.asNumber(this.job.params.nodes, 0);
    }

    getDesiredCapacity(instanceType?: string): number {
        if (this.job.params == null) {
            return 0;
        }
        if (this.isSharedCapacity()) {
            return this.getDesiredNodes() * Utils.asNumber(this.job.params.cpus, 1);
        } else {
            return this.getDesiredNodes() * this.getWeightedCapacity(instanceType);
        }
    }

    getSpotNodes(): number {
        if (this.isSpotCapacity()) {
            return this.getDesiredNodes();
        } else if (this.isMixedCapacity()) {
            return Utils.asNumber(this.job.params?.spot_allocation_count, 0);
        }
        return 0;
    }

    getSpotCapacity(): number {
        return this.getSpotNodes() * this.getWeightedCapacity();
    }

    getDefaultInstanceTypeOption(): SocaInstanceTypeOptions | null {
        if (this.job.provisioning_options == null) {
            return null;
        }
        if (this.job.provisioning_options.instance_types == null || this.job.provisioning_options.instance_types.length === 0) {
            return null;
        }
        return this.job.provisioning_options.instance_types[0];
    }

    getInstanceTypeOption(instanceType: string): SocaInstanceTypeOptions | null {
        if (this.job.provisioning_options == null) {
            return null;
        }
        if (this.job.provisioning_options.instance_types == null || this.job.provisioning_options.instance_types.length === 0) {
            return null;
        }
        const found = this.job.provisioning_options.instance_types.find((option) => option.name === instanceType);
        if (found) {
            return found;
        }
        return null;
    }

    getWeightedCapacity(instanceType?: string): number {
        let option;
        if (Utils.isNotEmpty(instanceType)) {
            option = this.getInstanceTypeOption(instanceType!);
        } else {
            option = this.getDefaultInstanceTypeOption();
        }
        if (option == null) {
            return 0;
        }
        return Utils.asNumber(option.default_vcpu_count, 0);
    }

    getInstanceTypeCpuCount(instanceType?: string): number {
        const instanceTypeOption = !instanceType ? this.getDefaultInstanceTypeOption() : this.getInstanceTypeOption(instanceType);
        return Utils.asNumber(instanceTypeOption?.threads_per_core, 0) * Utils.asNumber(instanceTypeOption?.default_core_count, 0);
    }

    isEphemeralCapacity(): boolean {
        if (this.job.provisioning_options == null) {
            return false;
        }
        if (Utils.isTrue(this.job.provisioning_options.keep_forever)) {
            return false;
        }
        const terminateWhenIdle = Utils.asNumber(this.job.provisioning_options.terminate_when_idle, 0);
        if (terminateWhenIdle > 0) {
            return false;
        }
        return true;
    }

    isSharedCapacity(): boolean {
        return !this.isEphemeralCapacity();
    }

    isPersistentCapacity(): boolean {
        if (this.job.provisioning_options == null) {
            return false;
        }
        return Utils.isTrue(this.job.provisioning_options.keep_forever);
    }

    getFormattedSpotPrice(): string {
        if (this.params == null) {
            return "-";
        }
        if (!this.isSpotCapacity() && !this.isMixedCapacity()) {
            return "-";
        }
        if (this.params.spot_price != null) {
            return `${this.params.spot_price.amount} ${this.params.spot_price.unit}`;
        } else {
            return "auto";
        }
    }
}
