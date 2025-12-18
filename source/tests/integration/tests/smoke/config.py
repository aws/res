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

from ideadatamodel import (  # type: ignore
    SocaMemory,
    SocaMemoryUnit,
    VirtualDesktopArchitecture,
    VirtualDesktopBaseOS,
    VirtualDesktopGPU,
    VirtualDesktopSoftwareStack,
)

MIN_LINUX_STORAGE = SocaMemory(value=50, unit=SocaMemoryUnit.GB)
MIN_WINDOWS_STORAGE = SocaMemory(value=50, unit=SocaMemoryUnit.GB)
MIN_RAM = SocaMemory(value=4, unit=SocaMemoryUnit.GB)

BASE_OS = [
    "amazonlinux2",
    "amzn2023",
    "rhel8",
    "rhel9",
    "ubuntu2204",
    "ubuntu2404",
    "windows",
    "rocky9",
]

AL2023_SOFTWARE_STACK = VirtualDesktopSoftwareStack(
    name=f"res-integ-test-stack-{VirtualDesktopBaseOS.AMAZON_LINUX2023}-{VirtualDesktopArchitecture.X86_64}",
    description="RES integ test software stack",
    base_os=VirtualDesktopBaseOS.AMAZON_LINUX2023,
    architecture=VirtualDesktopArchitecture.X86_64,
    min_storage=MIN_LINUX_STORAGE,
    min_ram=MIN_RAM,
    gpu=VirtualDesktopGPU.NO_GPU,
    allowed_instance_types=["t3", "m6a"],
)
LINUX_SOFTWARE_STACKS = [
    # Stack 0
    VirtualDesktopSoftwareStack(
        name=f"res-integ-test-stack-{VirtualDesktopBaseOS.AMAZON_LINUX2}-{VirtualDesktopArchitecture.X86_64}",
        description="RES integ test software stack",
        base_os=VirtualDesktopBaseOS.AMAZON_LINUX2,
        architecture=VirtualDesktopArchitecture.X86_64,
        min_storage=MIN_LINUX_STORAGE,
        min_ram=MIN_RAM,
        gpu=VirtualDesktopGPU.NO_GPU,
        allowed_instance_types=["t3", "m6a"],
    ),
    # Stack 1
    VirtualDesktopSoftwareStack(
        name=f"res-integ-test-stack-{VirtualDesktopBaseOS.AMAZON_LINUX2}-{VirtualDesktopArchitecture.ARM64}",
        description="RES integ test software stack",
        base_os=VirtualDesktopBaseOS.AMAZON_LINUX2,
        architecture=VirtualDesktopArchitecture.ARM64,
        min_storage=MIN_LINUX_STORAGE,
        min_ram=MIN_RAM,
        gpu=VirtualDesktopGPU.NO_GPU,
        allowed_instance_types=["m6g"],
    ),
    # Stack 2
    VirtualDesktopSoftwareStack(
        name=f"res-integ-test-stack-{VirtualDesktopBaseOS.RHEL8}-{VirtualDesktopArchitecture.X86_64}",
        description="RES integ test software stack",
        base_os=VirtualDesktopBaseOS.RHEL8,
        architecture=VirtualDesktopArchitecture.X86_64,
        min_storage=MIN_LINUX_STORAGE,
        min_ram=MIN_RAM,
        gpu=VirtualDesktopGPU.NO_GPU,
        allowed_instance_types=["t3", "m6a"],
    ),
    # Stack 3
    VirtualDesktopSoftwareStack(
        name=f"res-integ-test-stack-{VirtualDesktopBaseOS.RHEL9}-{VirtualDesktopArchitecture.X86_64}",
        description="RES integ test software stack",
        base_os=VirtualDesktopBaseOS.RHEL9,
        architecture=VirtualDesktopArchitecture.X86_64,
        min_storage=MIN_LINUX_STORAGE,
        min_ram=MIN_RAM,
        gpu=VirtualDesktopGPU.NO_GPU,
        allowed_instance_types=["t3", "m6a"],
    ),
    # Stack 4
    VirtualDesktopSoftwareStack(
        name=f"res-integ-test-stack-{VirtualDesktopBaseOS.UBUNTU2204}-{VirtualDesktopArchitecture.X86_64}",
        description="RES integ test software stack",
        base_os=VirtualDesktopBaseOS.UBUNTU2204,
        architecture=VirtualDesktopArchitecture.X86_64,
        min_storage=MIN_LINUX_STORAGE,
        min_ram=MIN_RAM,
        gpu=VirtualDesktopGPU.NO_GPU,
        allowed_instance_types=["t3", "m6a"],
    ),
    # Stack 5
    VirtualDesktopSoftwareStack(
        name=f"res-integ-test-stack-{VirtualDesktopBaseOS.UBUNTU2404}-{VirtualDesktopArchitecture.X86_64}",
        description="RES integ test software stack",
        base_os=VirtualDesktopBaseOS.UBUNTU2404,
        architecture=VirtualDesktopArchitecture.X86_64,
        min_storage=MIN_LINUX_STORAGE,
        min_ram=MIN_RAM,
        gpu=VirtualDesktopGPU.NO_GPU,
        allowed_instance_types=["t3", "m6a"],
    ),
    # Stack 6
    AL2023_SOFTWARE_STACK,
    # Stack 7
    VirtualDesktopSoftwareStack(
        name=f"res-integ-test-stack-{VirtualDesktopBaseOS.AMAZON_LINUX2023}-{VirtualDesktopArchitecture.ARM64}",
        description="RES integ test software stack",
        base_os=VirtualDesktopBaseOS.AMAZON_LINUX2023,
        architecture=VirtualDesktopArchitecture.ARM64,
        min_storage=MIN_LINUX_STORAGE,
        min_ram=MIN_RAM,
        gpu=VirtualDesktopGPU.NO_GPU,
        allowed_instance_types=["m6g"],
    ),
    # Stack 8
    VirtualDesktopSoftwareStack(
        name=f"res-integ-test-stack-{VirtualDesktopBaseOS.ROCKY_LINUX9}-{VirtualDesktopArchitecture.X86_64}",
        description="RES integ test software stack",
        base_os=VirtualDesktopBaseOS.ROCKY_LINUX9,
        architecture=VirtualDesktopArchitecture.X86_64,
        min_storage=MIN_LINUX_STORAGE,
        min_ram=MIN_RAM,
        gpu=VirtualDesktopGPU.NO_GPU,
        allowed_instance_types=["t3", "m6a"],
    ),
]

TEST_SOFTWARE_STACKS = LINUX_SOFTWARE_STACKS + [
    # Stack 9
    VirtualDesktopSoftwareStack(
        name=f"res-integ-test-stack-{VirtualDesktopBaseOS.WINDOWS}-{VirtualDesktopArchitecture.X86_64}",
        description="RES integ test software stack",
        base_os=VirtualDesktopBaseOS.WINDOWS,
        architecture=VirtualDesktopArchitecture.X86_64,
        min_storage=MIN_WINDOWS_STORAGE,
        min_ram=MIN_RAM,
        gpu=VirtualDesktopGPU.NO_GPU,
        allowed_instance_types=["t3", "m6a"],
    ),
    # Stack 10
    VirtualDesktopSoftwareStack(
        name=f"res-integ-test-stack-{VirtualDesktopBaseOS.WINDOWS}-{VirtualDesktopArchitecture.X86_64}-{VirtualDesktopGPU.NVIDIA}",
        description="RES integ test software stack",
        base_os=VirtualDesktopBaseOS.WINDOWS,
        architecture=VirtualDesktopArchitecture.X86_64,
        min_storage=MIN_WINDOWS_STORAGE,
        min_ram=MIN_RAM,
        gpu=VirtualDesktopGPU.NVIDIA,
        allowed_instance_types=["g4dn", "g5"],
    ),
    # Stack 11
    VirtualDesktopSoftwareStack(
        name=f"res-integ-test-stack-{VirtualDesktopBaseOS.WINDOWS}-{VirtualDesktopArchitecture.X86_64}-{VirtualDesktopGPU.AMD}",
        description="RES integ test software stack",
        base_os=VirtualDesktopBaseOS.WINDOWS,
        architecture=VirtualDesktopArchitecture.X86_64,
        min_storage=MIN_WINDOWS_STORAGE,
        min_ram=MIN_RAM,
        gpu=VirtualDesktopGPU.AMD,
        allowed_instance_types=["g4ad"],
    ),
]

TEST_SOFTWARE_STACKS_GOVCLOUD = [
    f"res-integ-test-stack-{VirtualDesktopBaseOS.AMAZON_LINUX2}-{VirtualDesktopArchitecture.X86_64}",
    f"res-integ-test-stack-{VirtualDesktopBaseOS.AMAZON_LINUX2}-{VirtualDesktopArchitecture.ARM64}",
    f"res-integ-test-stack-{VirtualDesktopBaseOS.RHEL8}-{VirtualDesktopArchitecture.X86_64}",
    f"res-integ-test-stack-{VirtualDesktopBaseOS.RHEL9}-{VirtualDesktopArchitecture.X86_64}",
]
