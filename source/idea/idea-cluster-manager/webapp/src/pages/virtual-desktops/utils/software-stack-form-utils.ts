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

import { VirtualDesktopBaseOs, VirtualDesktopGpu, VirtualDesktopSoftwareStack } from "../../../client/generated/api";
import { SocaUserInputChoice } from "../../../client/data-model";
import Utils from "../../../common/utils";

// Default values for software stack registration
export const DEFAULT_SOFTWARE_STACK_BASE_OS = VirtualDesktopBaseOs.Amazonlinux2;
export const DEFAULT_SOFTWARE_STACK_GPU = VirtualDesktopGpu.NoGpu;
export const DEFAULT_SOFTWARE_STACK_TENANCY = "default";
export const DEFAULT_SOFTWARE_STACK_MIN_RAM = 10;
export const DEFAULT_SOFTWARE_STACK_MIN_STORAGE = 50;

// Debounce delay for text input fields (AMI ID, RAM, storage) to avoid excessive API calls while typing
// 800ms provides good balance between responsiveness and preventing API spam
export const INSTANCE_TYPE_UPDATE_DEBOUNCE_MS = 800;

/**
 * Fetches allowed instance types for a software stack and converts them to form choices
 * @param stack - The software stack configuration
 * @returns Promise resolving to array of instance type choices
 */
export async function fetchInstanceTypeChoices(
    stack: Partial<VirtualDesktopSoftwareStack>
): Promise<SocaUserInputChoice[]> {
    if (!stack.base_os || !stack.gpu || !stack.min_ram || !stack.min_storage) {
        return [];
    }

    const instanceTypes = await Utils.getAllowedInstanceTypesOptionsForSelectedSoftwareStack(
        stack as VirtualDesktopSoftwareStack
    );
    
    return instanceTypes.map(type => ({
        title: type,
        value: type,
    }));
}

/**
 * Field updater mapping for software stack form state changes
 * @param values - Current form values
 * @param stack - Current software stack state
 * @returns Record of field names to updater functions
 */
export function createFieldUpdaters(
    values: any,
    stack: Partial<VirtualDesktopSoftwareStack>
): Record<string, () => void> {
    return {
        ami_id: () => stack.ami_id = values.ami_id.toLowerCase().trim(),
        base_os: () => stack.base_os = values.base_os,
        gpu: () => stack.gpu = values.gpu,
        tenancy: () => stack.placement = { ...stack.placement, tenancy: values.tenancy },
        ram_size: () => stack.min_ram = { value: values.ram_size, unit: "gb" },
        root_storage_size: () => stack.min_storage = { value: values.root_storage_size, unit: "gb" },
        allowed_instance_types: () => stack.allowed_instance_types = values.allowed_instance_types || [],
    };
}

/**
 * Determines if a field change should trigger immediate instance type update
 * @param prevStack - Previous software stack state
 * @param currStack - Current software stack state
 * @returns true if immediate update is needed
 */
export function shouldUpdateImmediate(
    prevStack: Partial<VirtualDesktopSoftwareStack>,
    currStack: Partial<VirtualDesktopSoftwareStack>
): boolean {
    return (
        prevStack.base_os !== currStack.base_os ||
        prevStack.gpu !== currStack.gpu ||
        prevStack.placement?.tenancy !== currStack.placement?.tenancy
    );
}

/**
 * Determines if a field change should trigger debounced instance type update
 * @param prevStack - Previous software stack state
 * @param currStack - Current software stack state
 * @returns true if debounced update is needed
 */
export function shouldUpdateDebounced(
    prevStack: Partial<VirtualDesktopSoftwareStack>,
    currStack: Partial<VirtualDesktopSoftwareStack>
): boolean {
    return (
        prevStack.ami_id !== currStack.ami_id ||
        prevStack.min_ram?.value !== currStack.min_ram?.value ||
        prevStack.min_storage?.value !== currStack.min_storage?.value
    );
}

/**
 * Handles debounced instance type updates for software stack forms
 * @param params - Update parameters
 */
export async function handleInstanceTypeUpdate(params: {
    prevStack: Partial<VirtualDesktopSoftwareStack>;
    currStack: Partial<VirtualDesktopSoftwareStack>;
    debounceTimer: NodeJS.Timeout | null;
    clearTimer: () => void;
    setTimer: (timer: NodeJS.Timeout) => void;
    clearError: () => void;
    updateInstanceTypes: () => Promise<void>;
    updateStack: (stack: Partial<VirtualDesktopSoftwareStack>) => void;
}): Promise<void> {
    const immediateUpdate = shouldUpdateImmediate(params.prevStack, params.currStack);
    const debouncedUpdate = shouldUpdateDebounced(params.prevStack, params.currStack);

    if (immediateUpdate) {
        if (params.debounceTimer) {
            clearTimeout(params.debounceTimer);
            params.clearTimer();
        }
        params.clearError();
        await params.updateInstanceTypes();
        const updatedStack = { ...params.currStack, allowed_instance_types: [] };
        params.updateStack(updatedStack);
    } else if (debouncedUpdate) {
        if (params.debounceTimer) {
            clearTimeout(params.debounceTimer);
        }
        
        const timer = setTimeout(async () => {
            params.clearError();
            await params.updateInstanceTypes();
            const updatedStack = { ...params.currStack, allowed_instance_types: [] };
            params.updateStack(updatedStack);
            params.clearTimer();
        }, INSTANCE_TYPE_UPDATE_DEBOUNCE_MS);
        
        params.setTimer(timer);
    }
}
