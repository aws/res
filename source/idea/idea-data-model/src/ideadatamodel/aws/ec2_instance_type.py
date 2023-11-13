#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

from ideadatamodel.model_utils import ModelUtils
from ideadatamodel import constants

from typing import Optional, Dict, List, Any


class EC2InstanceType:
    def __init__(self, data: Dict[str, Any]):
        self._instance_type = data

    def instance_type_data(self) -> Optional[Dict[str, Any]]:
        return self._instance_type

    @property
    def instance_type(self) -> Optional[str]:
        return ModelUtils.get_value_as_string('InstanceType', self.instance_type_data())

    @property
    def current_generation(self) -> Optional[bool]:
        return ModelUtils.get_value_as_bool('CurrentGeneration', self.instance_type_data())

    @property
    def free_tier_eligible(self) -> Optional[bool]:
        return ModelUtils.get_value_as_bool('FreeTierEligible', self.instance_type_data())

    @property
    def supported_usage_classes(self) -> Optional[List[str]]:
        return ModelUtils.get_value_as_list('SupportedUsageClasses', self.instance_type_data())

    @property
    def supported_root_device_types(self) -> Optional[List[str]]:
        return ModelUtils.get_value_as_list('SupportedRootDeviceTypes', self.instance_type_data())

    @property
    def supported_virtualization_types(self) -> Optional[List[str]]:
        return ModelUtils.get_value_as_list('SupportedVirtualizationTypes', self.instance_type_data())

    @property
    def bare_metal(self) -> Optional[bool]:
        return ModelUtils.get_value_as_bool('BareMetal', self.instance_type_data())

    @property
    def hypervisor(self) -> Optional[str]:
        return ModelUtils.get_value_as_string('Hypervisor', self.instance_type_data())

    @property
    def processor_info_supported_architectures(self) -> Optional[List[str]]:
        processor_info = ModelUtils.get_value_as_dict('ProcessorInfo', self.instance_type_data())
        return ModelUtils.get_value_as_list('SupportedArchitectures', processor_info)

    @property
    def processor_info_sustained_click_speed_in_ghz(self) -> Optional[float]:
        processor_info = ModelUtils.get_value_as_dict('ProcessorInfo', self.instance_type_data())
        return ModelUtils.get_value_as_float('SustainedClockSpeedInGhz', processor_info)

    @property
    def vcpu_info_default_vcpus(self) -> Optional[int]:
        vcpu_info = ModelUtils.get_value_as_dict('VCpuInfo', self.instance_type_data())
        return ModelUtils.get_value_as_int('DefaultVCpus', vcpu_info)

    @property
    def vcpu_info_default_cores(self) -> Optional[int]:
        vcpu_info = ModelUtils.get_value_as_dict('VCpuInfo', self.instance_type_data())
        return ModelUtils.get_value_as_int('DefaultCores', vcpu_info)

    @property
    def vcpu_info_default_threads_per_core(self) -> Optional[int]:
        vcpu_info = ModelUtils.get_value_as_dict('VCpuInfo', self.instance_type_data())
        return ModelUtils.get_value_as_int('DefaultThreadsPerCore', vcpu_info)

    @property
    def vcpu_info_valid_cores(self) -> Optional[List[int]]:
        vcpu_info = ModelUtils.get_value_as_dict('VCpuInfo', self.instance_type_data())
        return ModelUtils.get_value_as_list('ValidCores', vcpu_info)

    @property
    def vcpu_info_valid_threads_per_core(self) -> Optional[List[int]]:
        vcpu_info = ModelUtils.get_value_as_dict('VCpuInfo', self.instance_type_data())
        return ModelUtils.get_value_as_list('ValidThreadsPerCore', vcpu_info)

    @property
    def memory_info_size_in_mib(self) -> Optional[int]:
        memory_info = ModelUtils.get_value_as_dict('MemoryInfo', self.instance_type_data())
        return ModelUtils.get_value_as_int('SizeInMiB', memory_info)

    @property
    def instance_storage_supported(self) -> Optional[bool]:
        return ModelUtils.get_value_as_bool('InstanceStorageSupported', self.instance_type_data())

    @property
    def instance_storage_info_total_size_in_gb(self) -> Optional[int]:
        instance_storage_info = ModelUtils.get_value_as_dict('InstanceStorageInfo', self.instance_type_data())
        return ModelUtils.get_value_as_int('TotalSizeInGB', instance_storage_info)

    @property
    def instance_storage_info_disks(self) -> Optional[List[Dict]]:
        instance_storage_info = ModelUtils.get_value_as_dict('InstanceStorageInfo', self.instance_type_data())
        return ModelUtils.get_value_as_list('Disks', instance_storage_info)

    @property
    def instance_storage_info_nvme_support(self) -> Optional[str]:
        instance_storage_info = ModelUtils.get_value_as_dict('InstanceStorageInfo', self.instance_type_data())
        return ModelUtils.get_value_as_string('NvmeSupport', instance_storage_info)

    @property
    def instance_storage_info_encryption_support(self) -> Optional[str]:
        instance_storage_info = ModelUtils.get_value_as_dict('InstanceStorageInfo', self.instance_type_data())
        return ModelUtils.get_value_as_string('EncryptionSupport', instance_storage_info)

    @property
    def ebs_info_ebs_optimized_support(self) -> Optional[str]:
        ebs_info = ModelUtils.get_value_as_dict('EbsInfo', self.instance_type_data())
        return ModelUtils.get_value_as_string('EbsOptimizedSupport', ebs_info)

    @property
    def ebs_info_encryption_support(self) -> Optional[str]:
        ebs_info = ModelUtils.get_value_as_string('EbsInfo', self.instance_type_data())
        return ModelUtils.get_value_as_string('EncryptionSupport', ebs_info)

    @property
    def ebs_info_ebs_optimized_info(self) -> Optional[Dict]:
        ebs_info = ModelUtils.get_value_as_dict('EbsInfo', self.instance_type_data())
        return ModelUtils.get_value_as_dict('EbsOptimizedInfo', ebs_info)

    @property
    def ebs_info_nvme_support(self) -> Optional[str]:
        ebs_info = ModelUtils.get_value_as_dict('EbsInfo', self.instance_type_data())
        return ModelUtils.get_value_as_string('NvmeSupport', ebs_info)

    @property
    def network_info_network_performance(self) -> Optional[str]:
        network_info = ModelUtils.get_value_as_dict('NetworkInfo', self.instance_type_data())
        return ModelUtils.get_value_as_string('NetworkPerformance', network_info)

    @property
    def network_info_maximum_network_interfaces(self) -> Optional[int]:
        network_info = ModelUtils.get_value_as_dict('NetworkInfo', self.instance_type_data())
        return ModelUtils.get_value_as_int('MaximumNetworkInterfaces', network_info)

    @property
    def network_info_maximum_network_cards(self) -> Optional[int]:
        network_info = ModelUtils.get_value_as_dict('NetworkInfo', self.instance_type_data())
        return ModelUtils.get_value_as_int('MaximumNetworkCards', network_info)

    @property
    def network_info_default_network_card_index(self) -> Optional[int]:
        network_info = ModelUtils.get_value_as_dict('NetworkInfo', self.instance_type_data())
        return ModelUtils.get_value_as_int('DefaultNetworkCardIndex', network_info)

    @property
    def network_info_network_cards(self) -> Optional[List[Dict]]:
        network_info = ModelUtils.get_value_as_dict('NetworkInfo', self.instance_type_data())
        return ModelUtils.get_value_as_list('NetworkCards', network_info)

    @property
    def network_info_ipv4_addresses_per_interface(self) -> Optional[int]:
        network_info = ModelUtils.get_value_as_dict('NetworkInfo', self.instance_type_data())
        return ModelUtils.get_value_as_int('Ipv4AddressesPerInterface', network_info)

    @property
    def network_info_ipv6_addresses_per_interface(self) -> Optional[int]:
        network_info = ModelUtils.get_value_as_dict('NetworkInfo', self.instance_type_data())
        return ModelUtils.get_value_as_int('Ipv6AddressesPerInterface', network_info)

    @property
    def network_info_ipv6_supported(self) -> Optional[bool]:
        network_info = ModelUtils.get_value_as_dict('NetworkInfo', self.instance_type_data())
        return ModelUtils.get_value_as_bool('Ipv6Supported', network_info)

    @property
    def network_info_ena_supported(self) -> Optional[bool]:
        network_info = ModelUtils.get_value_as_dict('NetworkInfo', self.instance_type_data())
        return ModelUtils.get_value_as_bool('EnaSupport', network_info)

    @property
    def network_info_efa_supported(self) -> Optional[bool]:
        network_info = ModelUtils.get_value_as_dict('NetworkInfo', self.instance_type_data())
        return ModelUtils.get_value_as_bool('EfaSupported', network_info)

    @property
    def network_info_efa_info_max_efa_interfaces(self) -> Optional[int]:
        network_info = ModelUtils.get_value_as_dict('NetworkInfo', self.instance_type_data())
        efa_info = ModelUtils.get_value_as_dict('EfaInfo', network_info)
        return ModelUtils.get_value_as_int('MaximumEfaInterfaces', efa_info)

    @property
    def network_info_encryption_in_transit_supported(self) -> Optional[bool]:
        network_info = ModelUtils.get_value_as_dict('NetworkInfo', self.instance_type_data())
        return ModelUtils.get_value_as_bool('EncryptionInTransitSupported', network_info)

    @property
    def gpu_info_gpus(self) -> Optional[List[Dict]]:
        gpu_info = ModelUtils.get_value_as_dict('GpuInfo', self.instance_type_data())
        return ModelUtils.get_value_as_list('Gpus', gpu_info)

    @property
    def gpu_info_total_gpu_memory_in_mib(self) -> Optional[int]:
        gpu_info = ModelUtils.get_value_as_dict('GpuInfo', self.instance_type_data())
        return ModelUtils.get_value_as_int('TotalGpuMemoryInMiB', gpu_info)

    @property
    def fpga_info_fpgas(self) -> Optional[List[Dict]]:
        fpga_info = ModelUtils.get_value_as_dict('FpgaInfo', self.instance_type_data())
        return ModelUtils.get_value_as_list('Fpgas', fpga_info)

    @property
    def fpga_info_total_fpga_memory_in_mib(self) -> Optional[int]:
        fpga_info = ModelUtils.get_value_as_dict('FpgaInfo', self.instance_type_data())
        return ModelUtils.get_value_as_int('TotalFpgaMemoryInMiB', fpga_info)

    @property
    def placement_group_info_supported_strategies(self) -> Optional[List[str]]:
        placement_group_info = ModelUtils.get_value_as_dict('PlacementGroupInfo', self.instance_type_data())
        return ModelUtils.get_value_as_list('SupportedStrategies', placement_group_info)

    @property
    def inference_accelerator_info_accelerators(self) -> Optional[List[Dict]]:
        inference_accelerator_info = ModelUtils.get_value_as_dict('InferenceAcceleratorInfo', self.instance_type_data())
        return ModelUtils.get_value_as_list('Accelerators', inference_accelerator_info)

    @property
    def hibernation_supported(self) -> Optional[bool]:
        return ModelUtils.get_value_as_bool('HibernationSupported', self.instance_type_data())

    @property
    def burstable_performance_supported(self) -> Optional[bool]:
        return ModelUtils.get_value_as_bool('BurstablePerformanceSupported', self.instance_type_data())

    @property
    def dedicated_hosts_supported(self) -> Optional[bool]:
        return ModelUtils.get_value_as_bool('DedicatedHostsSupported', self.instance_type_data())

    @property
    def auto_recovery_supported(self) -> Optional[bool]:
        return ModelUtils.get_value_as_bool('AutoRecoverySupported', self.instance_type_data())

    @property
    def supported_boot_modes(self) -> Optional[List[str]]:
        return ModelUtils.get_value_as_list('SupportedBootModes', self.instance_type_data())

    @property
    def is_cpu_options_supported(self) -> Optional[bool]:
        # CpuOptions is not supported for all instances
        # it's not explicitly called out in aws docs, but this page does not list metal instances for CpuOptions:
        # https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/cpu-options-supported-instances-values.html
        family = self.instance_type.split('.')[0].lower()
        if (self.bare_metal is True) or (family.startswith(constants.EC2_SERVICE_CPU_OPTIONS_UNSUPPORTED_FAMILY)):
            return False
        else:
            return True
