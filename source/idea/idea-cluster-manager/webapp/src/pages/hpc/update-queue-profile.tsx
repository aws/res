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

import React, { Component, RefObject } from "react";

import IdeaWizard from "../../components/wizard";
import Utils from "../../common/utils";
import { AppContext } from "../../common";
import { HpcQueueProfile, Project } from "../../client/data-model";
import { QueueUtils } from "./hpc-utils";
import dot from "dot-object";
import { SchedulerAdminClient } from "../../client";
import { IdeaSideNavigationProps } from "../../components/side-navigation";
import IdeaAppLayout, { IdeaAppLayoutProps } from "../../components/app-layout";
import { withRouter } from "../../navigation/navigation-utils";

export interface HpcUpdateQueueProfileProps extends IdeaAppLayoutProps, IdeaSideNavigationProps { }

export interface HpcUpdateQueueProfileState {
    queueProfile?: HpcQueueProfile;
    isCreate: boolean;
    queueProfileId?: string;
    projects: Project[];
}

class HpcUpdateQueueProfile extends Component<HpcUpdateQueueProfileProps, HpcUpdateQueueProfileState> {
    wizard: RefObject<IdeaWizard>;

    constructor(props: HpcUpdateQueueProfileProps) {
        super(props);
        this.wizard = React.createRef();
        this.state = {
            queueProfile: {},
            isCreate: this.props.location.pathname.startsWith("/soca/queues/create"),
            queueProfileId: "",
            projects: [],
        };
    }

    schedulerAdmin(): SchedulerAdminClient {
        return AppContext.get().client().schedulerAdmin();
    }

    getWizard(): IdeaWizard {
        return this.wizard.current!;
    }

    isCreate(): boolean {
        return this.state.isCreate;
    }

    isUpdate(): boolean {
        return !this.isCreate();
    }

    componentDidMount() {
        if (this.isUpdate()) {
            const query = new URLSearchParams(this.props.location.search);
            const queueProfileId = Utils.asString(query.get("id"));
            this.schedulerAdmin()
                .getQueueProfile({
                    queue_profile_id: queueProfileId,
                })
                .then((result) => {
                    this.setState({
                        queueProfile: result.queue_profile,
                        queueProfileId: queueProfileId,
                    });
                });
        }
    }

    isReady(): boolean {
        if (this.isCreate()) {
            return true;
        } else {
            return Utils.isNotEmpty(this.state.queueProfileId);
        }
    }

    getValues(): any {
        let project_ids: any = [];
        this.state.queueProfile?.projects?.forEach((project) => {
            project_ids.push(project.project_id);
        });
        return {
            ...this.state.queueProfile,
            project_ids: project_ids,
        };
    }

    render() {
        return (
            <IdeaAppLayout
                ideaPageId={this.props.ideaPageId}
                toolsOpen={this.props.toolsOpen}
                tools={this.props.tools}
                onToolsChange={this.props.onToolsChange}
                onPageChange={this.props.onPageChange}
                sideNavHeader={this.props.sideNavHeader}
                sideNavItems={this.props.sideNavItems}
                onSideNavChange={this.props.onSideNavChange}
                onFlashbarChange={this.props.onFlashbarChange}
                flashbarItems={this.props.flashbarItems}
                breadcrumbItems={[
                    {
                        text: "IDEA",
                        href: "#/",
                    },
                    {
                        text: "Scale-Out Computing",
                        href: "#/soca/active-jobs",
                    },
                    {
                        text: "Queues",
                        href: "#/soca/queues",
                    },
                    {
                        text: this.isCreate() ? "Create Queue Profile" : "Update Queue Profile",
                        href: "#",
                    },
                ]}
                contentType={"wizard"}
                content={
                    this.isReady() && (
                        <IdeaWizard
                            ref={this.wizard}
                            values={this.getValues()}
                            onFetchOptions={(request) => {
                                if (request.param === "project_ids") {
                                    return AppContext.get()
                                        .client()
                                        .projects()
                                        .listProjects({
                                            paginator: {
                                                page_size: 100,
                                            },
                                        })
                                        .then((result) => {
                                            let choices: any = [];
                                            result.listing?.forEach((project) => {
                                                choices.push({
                                                    title: project.title,
                                                    value: project.project_id,
                                                    description: `Project Code: ${project.name}`,
                                                });
                                            });
                                            return {
                                                listing: choices,
                                            };
                                        });
                                }
                                return Promise.resolve({});
                            }}
                            module={{
                                name: "queue-profile-wizard",
                                sections: [
                                    {
                                        name: "basic",
                                        title: "Queue Profile Settings",
                                        description: "Queue Profile encapsulates settings for multiple queues. These settings will be applicable for all jobs submitted to any queues applicable for this profile.",
                                        required: true,
                                        groups: [
                                            {
                                                title: "Basic Info",
                                                name: "basic-info",
                                                description: "Configure basic information for the queue profile.",
                                                params: [
                                                    {
                                                        name: "name",
                                                        title: "Name",
                                                        description: "Enter a name for the queue profile",
                                                        help_text: "Name can only use lowercase alphabets, numbers, and hyphens (-). Must be between 3 and 18 characters long. Name cannot be edited after creation.",
                                                        param_type: "text",
                                                        data_type: "str",
                                                        validate: {
                                                            required: true,
                                                            regex: "^([a-z0-9-]+){3,18}$",
                                                            message: "Only use lowercase alphabets, numbers, and hyphens (-). Must be between 3 and 18 characters long.",
                                                        },
                                                    },
                                                    {
                                                        name: "title",
                                                        title: "Title",
                                                        description: "Enter a user-friendly title for the Queue Profile",
                                                        param_type: "text",
                                                        data_type: "str",
                                                        validate: {
                                                            required: true,
                                                        },
                                                    },
                                                    {
                                                        name: "project_ids",
                                                        title: "Projects",
                                                        description: "Select applicable projects for the Queue Profile. Only the members of these projects are authorized to interact with the queues configured in this Queue Profile.",
                                                        param_type: "select",
                                                        multiple: true,
                                                        data_type: "str",
                                                        validate: {
                                                            required: true,
                                                        },
                                                        dynamic_choices: true,
                                                    },
                                                ],
                                            },
                                            {
                                                title: "Queue Settings",
                                                name: "queue-profile-info",
                                                params: [
                                                    {
                                                        name: "queues",
                                                        title: "Scheduler Queues",
                                                        description: "Enter scheduler queue names. The queues will be automatically created" + " if they do not already exist. When multiple queues are provided, jobs in the first queue will have a higher priority for provisioning than the last queue.",
                                                        param_type: "text",
                                                        data_type: "str",
                                                        multiple: true,
                                                        validate: {
                                                            required: true,
                                                        },
                                                    },
                                                    {
                                                        name: "queue_mode",
                                                        title: "Queue Mode",
                                                        description: "Select queue mode.",
                                                        param_type: "select",
                                                        data_type: "str",
                                                        default: "fifo",
                                                        choices: [
                                                            {
                                                                title: "First-In First-Out (FIFO)",
                                                                description: "Jobs will be provisioned based on the time the job was queued.",
                                                                value: "fifo",
                                                            },
                                                            // todo - add support after additional testing of these queue modes
                                                            // {
                                                            //     title: 'License Optimized',
                                                            //     value: 'license-optimized'
                                                            // },
                                                            // {
                                                            //     title: 'Fair Share',
                                                            //     value: 'fairshare'
                                                            // }
                                                        ],
                                                        validate: {
                                                            required: true,
                                                        },
                                                    },
                                                    {
                                                        name: "keep_forever",
                                                        title: "Keep Forever (Always-On Queue)",
                                                        description: "Indicates if the termination of AWS resources provisioned for the job will managed manually.",
                                                        param_type: "confirm",
                                                        data_type: "bool",
                                                        default: false,
                                                        validate: {
                                                            required: true,
                                                        },
                                                    },
                                                    {
                                                        name: "scaling_mode",
                                                        title: "Scaling Mode",
                                                        description: "Select scaling mode for the queue",
                                                        param_type: "select",
                                                        data_type: "str",
                                                        default: "single-job",
                                                        choices: [
                                                            {
                                                                title: "Single Job",
                                                                description: "New AWS resources will be provisioned for each job submitted.",
                                                                value: "single-job",
                                                            },
                                                            {
                                                                title: "Batch",
                                                                description: "Jobs submitted in close succession will be provisioned in batches. New jobs will reuse existing capacity if available. " + "Provisioned capacity will be dynamically adjusted based on new batches submitted.",
                                                                value: "batch",
                                                            },
                                                        ],
                                                        validate: {
                                                            required: true,
                                                        },
                                                        when: {
                                                            param: "keep_forever",
                                                            eq: false,
                                                        },
                                                    },
                                                    {
                                                        name: "terminate_when_idle",
                                                        title: "Terminate When Idle (in minutes)",
                                                        description: "Enter the idle duration in minutes, after which the provisioned AWS capacity will be terminated.",
                                                        help_text: "Terminate when idle is optional when Keep Forever is true but is required when scaling mode is Batch",
                                                        param_type: "text",
                                                        data_type: "int",
                                                        default: 0,
                                                        validate: {
                                                            required: true,
                                                            min: 0,
                                                        },
                                                        when: {
                                                            or: [
                                                                {
                                                                    param: "keep_forever",
                                                                    eq: true,
                                                                },
                                                                {
                                                                    param: "scaling_mode",
                                                                    not_eq: "single-job",
                                                                },
                                                            ],
                                                        },
                                                    },
                                                ],
                                            },
                                            {
                                                name: "queue-limits",
                                                title: "Queue Limits",
                                                params: [
                                                    {
                                                        name: "queue_management_params.max_running_jobs",
                                                        title: "Max Running Jobs",
                                                        description: "The maximum no. of jobs that can be running state for all the queues in this Queue Profile",
                                                        help_text: "0 implies no limits to max running jobs",
                                                        param_type: "text",
                                                        data_type: "int",
                                                        default: 0,
                                                        validate: {
                                                            required: true,
                                                            min: 0,
                                                        },
                                                    },
                                                    {
                                                        name: "queue_management_params.max_provisioned_instances",
                                                        title: "Max Provisioned Instances",
                                                        description: "The maximum no. of EC2 instances that can be in Running state for all the queues in this Queue Profile",
                                                        help_text: "0 implies no limits to max provisioned instances",
                                                        param_type: "text",
                                                        data_type: "int",
                                                        default: 0,
                                                        validate: {
                                                            required: true,
                                                            min: 0,
                                                        },
                                                    },
                                                ],
                                            },
                                            {
                                                name: "queue-acls",
                                                title: "Queue ACLs",
                                                description: "Configure access control lists for job provisioning parameters.",
                                                params: [
                                                    {
                                                        name: "queue_management_params.allowed_instance_types",
                                                        title: "Allowed Instance Types",
                                                        description: "List of instance type or instance families allowed to be provisioned by your users for their jobs",
                                                        param_type: "text",
                                                        data_type: "str",
                                                        multiple: true,
                                                    },
                                                    {
                                                        name: "queue_management_params.excluded_instance_types",
                                                        title: "Excluded Instance Types",
                                                        description: "List of instance type or instance families your users are not authorized to provision for their jobs",
                                                        param_type: "text",
                                                        data_type: "str",
                                                        multiple: true,
                                                    },
                                                    {
                                                        name: "queue_management_params.restricted_parameters",
                                                        title: "Restricted Parameters",
                                                        description: "List of jobs parameters your users are not able to customize",
                                                        param_type: "text",
                                                        data_type: "str",
                                                        multiple: true,
                                                    },
                                                    {
                                                        name: "queue_management_params.allowed_security_groups",
                                                        title: "Allowed Security Groups",
                                                        description: "List of additional security group(s) users can override via the security_groups parameter",
                                                        param_type: "text",
                                                        data_type: "str",
                                                        multiple: true,
                                                    },
                                                    {
                                                        name: "queue_management_params.allowed_instance_profiles",
                                                        title: "Allowed Instance Profiles",
                                                        description: "List of additional IAM instance profile(s) users can override via instance_profile parameter",
                                                        param_type: "text",
                                                        data_type: "str",
                                                        multiple: true,
                                                    },
                                                ],
                                            },
                                        ],
                                    },
                                    {
                                        title: "Default Compute Stack Parameters",
                                        name: "default-compute-stack",
                                        description: "Configure the default compute stack parameters for the jobs submitted to queues in this queue profile. Default parameters can be overriden during job submission.",
                                        required: true,
                                        groups: [
                                            {
                                                name: "instance-info",
                                                title: "Instance Info",
                                                params: [
                                                    {
                                                        name: "default_job_params.base_os",
                                                        title: "Compute Node OS",
                                                        description: "Select the default operating system for the compute nodes",
                                                        param_type: "select",
                                                        data_type: "str",
                                                        default: "amazonlinux2",
                                                        validate: {
                                                            required: true,
                                                        },
                                                        choices: [
                                                            {
                                                                title: "Amazon Linux 2",
                                                                value: "amazonlinux2",
                                                            }
                                                        ],
                                                    },
                                                    {
                                                        name: "default_job_params.instance_ami",
                                                        title: "Instance AMI",
                                                        description: "Enter the default instance AMI ID",
                                                        help_text: "The operating system of the AMI must match to that of Compute Node OS",
                                                        param_type: "text",
                                                        data_type: "str",
                                                    },
                                                    {
                                                        name: "default_job_params.instance_types",
                                                        title: "Instance Types",
                                                        description:
                                                            "Enter default instance types for the Job. When multiple instance types are provided, instances will be provisioned using weighted capacities. " +
                                                            "The order of instance types matters, where instance types must belong to the same instance family with increasing capacity. eg. c5.large -> c5.xlarge -> c5.2xlarge",
                                                        param_type: "text",
                                                        data_type: "str",
                                                        multiple: true,
                                                        validate: {
                                                            required: true,
                                                        },
                                                    },
                                                    {
                                                        name: "default_job_params.root_storage_size",
                                                        title: "Root Storage Size (in GB)",
                                                        description: "Enter the root EBS volume storage size.",
                                                        help_text: "The storage size must be >= the instance AMI storage size.",
                                                        param_type: "auto",
                                                        data_type: "memory",
                                                        default: {
                                                            value: 10,
                                                            unit: "gb",
                                                        },
                                                        validate: {
                                                            required: true,
                                                        },
                                                    },
                                                    {
                                                        name: "default_job_params.keep_ebs_volumes",
                                                        title: "Keep EBS Volumes?",
                                                        description: "Indicate if the EBS volumes provisioned must be retained after the job is completed.",
                                                        param_type: "confirm",
                                                        data_type: "bool",
                                                        default: false,
                                                    },
                                                    {
                                                        name: "default_job_params.enable_efa_support",
                                                        title: "Enable EFA Support?",
                                                        description: "Indicate if Amazon Elastic Fabric Adapter (EFA) drivers need to be installed on the instance.",
                                                        param_type: "confirm",
                                                        data_type: "bool",
                                                        default: false,
                                                    },
                                                    {
                                                        name: "default_job_params.enable_ht_support",
                                                        title: "Enable Hyper-Threading?",
                                                        description: "Indicate if hyper-threading should be enabled. When enabled, default vCPUs for a given instance type are used instead of no. of available threads per core.",
                                                        param_type: "confirm",
                                                        data_type: "bool",
                                                        default: false,
                                                    },
                                                    {
                                                        name: "default_job_params.force_reserved_instances",
                                                        title: "Force Reserved Instances?",
                                                        description: "Indicate of jobs must be provisioned using reserved instances if available. Job will remain queued, until reserved instances for given instance types become available.",
                                                        param_type: "confirm",
                                                        data_type: "bool",
                                                        default: false,
                                                    },
                                                ],
                                            },
                                            {
                                                name: "spot-fleet",
                                                title: "Spot Fleet",
                                                description: "Configure usage of spot fleet for provisioning the compute capacity.",
                                                params: [
                                                    {
                                                        name: "default_job_params.spot",
                                                        title: "Use Spot Fleet?",
                                                        description: "Indicate if spot instances can be used for provisioning the compute capacity.",
                                                        param_type: "confirm",
                                                        data_type: "bool",
                                                        default: false,
                                                        validate: {
                                                            required: true,
                                                        },
                                                    },
                                                    {
                                                        name: "default_job_params.spot_price",
                                                        title: "Spot Price",
                                                        description: "The maximum price per unit hour that you are willing to pay for a Spot Instance. We do not recommend using this parameter because it can lead to increased interruptions. If you do not specify this parameter, you will pay the current Spot price.",
                                                        help_text: "0 indicates current Spot price. If you specify a maximum price, your instances will be interrupted more frequently than if you do not specify this parameter.",
                                                        param_type: "auto",
                                                        data_type: "amount",
                                                        default: 0.0,
                                                        validate: {
                                                            required: true,
                                                        },
                                                        when: {
                                                            param: "default_job_params.spot",
                                                            eq: true,
                                                        },
                                                    },
                                                    {
                                                        name: "default_job_params.spot_allocation_count",
                                                        title: "Spot Allocation Count",
                                                        description: "Mixed instance policy will be used to provision a mix of On-Demand + Spot Instances. Cap the default no. of spot instances to be provisioned.",
                                                        help_text: "The total no. of nodes for the job must be greater than the spot allocation count.",
                                                        param_type: "text",
                                                        data_type: "int",
                                                        default: 0,
                                                        validate: {
                                                            required: true,
                                                        },
                                                        when: {
                                                            param: "default_job_params.spot",
                                                            eq: true,
                                                        },
                                                    },
                                                    {
                                                        name: "default_job_params.spot_allocation_strategy",
                                                        title: "Spot Allocation Strategy",
                                                        description: "Spot Fleet uses the allocation strategy that you specify to pick the specific pools from all possible spot capacity pools.",
                                                        param_type: "select",
                                                        data_type: "str",
                                                        default: "capacity-optimized",
                                                        validate: {
                                                            required: true,
                                                        },
                                                        when: {
                                                            param: "default_job_params.spot",
                                                            eq: true,
                                                        },
                                                        choices: [
                                                            {
                                                                title: "Capacity Optimized",
                                                                description: "Request SpotInstances from the pool that has the lowest chance of interruption in the near term.",
                                                                value: "capacity-optimized",
                                                            },
                                                            {
                                                                title: "Lowest Price",
                                                                description: "The Spot Instances come from the lowest priced pool that has available capacity.",
                                                                value: "lowest-price",
                                                            },
                                                            {
                                                                title: "Diversified",
                                                                description: "The Spot Instances are distributed across all pools.",
                                                                value: "diversified",
                                                            },
                                                        ],
                                                    },
                                                ],
                                            },
                                            {
                                                name: "network-and-security",
                                                title: "Network and Security",
                                                description: "Configure the default network, security group and IAM Role settings for the queue profile.",
                                                params: [
                                                    {
                                                        name: "default_job_params.subnet_ids",
                                                        title: "Subnet Ids",
                                                        description: "Enter Subnet Ids in which compute nodes can be launched. When multiple subnet ids are configured, one of the subnets is selected randomly.",
                                                        help_text: "If no subnets are configured, default private subnets configured in cluster settings will be used.",
                                                        param_type: "text",
                                                        data_type: "str",
                                                        multiple: true,
                                                    },
                                                    {
                                                        name: "default_job_params.security_groups",
                                                        title: "Security Groups",
                                                        description: "Enter security group Ids. ",
                                                        param_type: "text",
                                                        data_type: "str",
                                                        multiple: true,
                                                    },
                                                    {
                                                        name: "default_job_params.instance_profile",
                                                        title: "Instance Profile",
                                                        description: "Enter instance profile ARN.",
                                                        help_text: "A blank value will use the default instance profile for compute nodes",
                                                        param_type: "text",
                                                        data_type: "str",
                                                    },
                                                    {
                                                        name: "default_job_params.enable_placement_group",
                                                        title: "Enable Placement Group?",
                                                        param_type: "confirm",
                                                        data_type: "bool",
                                                        default: false,
                                                    },
                                                ],
                                            },
                                            {
                                                title: "Scratch Storage",
                                                name: "scratch-storage",
                                                params: [
                                                    {
                                                        name: "default_job_params.enable_scratch",
                                                        title: "Enable Scratch Storage",
                                                        param_type: "confirm",
                                                        data_type: "bool",
                                                        default: false,
                                                    },
                                                    {
                                                        name: "default_job_params.scratch_provider",
                                                        title: "Scratch Provider",
                                                        param_type: "select",
                                                        data_type: "str",
                                                        default: "ebs",
                                                        choices: [
                                                            {
                                                                title: "EBS",
                                                                value: "ebs",
                                                            },
                                                            {
                                                                title: "FSx for Lustre (Existing)",
                                                                value: "fsx-lustre-existing",
                                                            },
                                                            {
                                                                title: "FSx for Lustre (New)",
                                                                value: "fsx-lustre-new",
                                                            },
                                                        ],
                                                        when: {
                                                            param: "default_job_params.enable_scratch",
                                                            eq: true,
                                                        },
                                                    },
                                                    {
                                                        name: "default_job_params.scratch_storage_size",
                                                        title: "Scratch Storage Size",
                                                        param_type: "auto",
                                                        data_type: "memory",
                                                        default: {
                                                            value: 10,
                                                            unit: "gb",
                                                        },
                                                        when: {
                                                            and: [
                                                                {
                                                                    param: "default_job_params.scratch_provider",
                                                                    eq: "ebs",
                                                                },
                                                                {
                                                                    param: "default_job_params.enable_scratch",
                                                                    eq: true,
                                                                },
                                                            ],
                                                        },
                                                    },
                                                    {
                                                        name: "default_job_params.scratch_storage_iops",
                                                        title: "Scratch Storage Provisioned IOPS (GP3)",
                                                        param_type: "text",
                                                        data_type: "int",
                                                        default: 3000,
                                                        when: {
                                                            and: [
                                                                {
                                                                    param: "default_job_params.scratch_provider",
                                                                    eq: "ebs",
                                                                },
                                                                {
                                                                    param: "default_job_params.enable_scratch",
                                                                    eq: true,
                                                                },
                                                            ],
                                                        },
                                                    },
                                                    {
                                                        name: "default_job_params.fsx_lustre.existing_fsx",
                                                        title: "Existing FSx for Lustre",
                                                        param_type: "select",
                                                        data_type: "str",
                                                        when: {
                                                            and: [
                                                                {
                                                                    param: "default_job_params.scratch_provider",
                                                                    eq: "fsx-lustre-existing",
                                                                },
                                                                {
                                                                    param: "default_job_params.enable_scratch",
                                                                    eq: true,
                                                                },
                                                            ],
                                                        },
                                                    },
                                                    {
                                                        name: "default_job_params.fsx_lustre.s3_backend",
                                                        title: "S3 Backend",
                                                        param_type: "text",
                                                        data_type: "str",
                                                        when: {
                                                            and: [
                                                                {
                                                                    param: "default_job_params.scratch_provider",
                                                                    eq: "fsx-lustre-new",
                                                                },
                                                                {
                                                                    param: "default_job_params.enable_scratch",
                                                                    eq: true,
                                                                },
                                                            ],
                                                        },
                                                    },
                                                    {
                                                        name: "default_job_params.fsx_lustre.import_path",
                                                        title: "Import Path",
                                                        param_type: "text",
                                                        data_type: "str",
                                                        when: {
                                                            and: [
                                                                {
                                                                    param: "default_job_params.scratch_provider",
                                                                    eq: "fsx-lustre-new",
                                                                },
                                                                {
                                                                    param: "default_job_params.enable_scratch",
                                                                    eq: true,
                                                                },
                                                            ],
                                                        },
                                                    },
                                                    {
                                                        name: "default_job_params.fsx_lustre.export_path",
                                                        title: "Export Path",
                                                        param_type: "text",
                                                        data_type: "str",
                                                        when: {
                                                            and: [
                                                                {
                                                                    param: "default_job_params.scratch_provider",
                                                                    eq: "fsx-lustre-new",
                                                                },
                                                                {
                                                                    param: "default_job_params.enable_scratch",
                                                                    eq: true,
                                                                },
                                                            ],
                                                        },
                                                    },
                                                    {
                                                        name: "default_job_params.fsx_lustre.deployment_type",
                                                        title: "Deployment Type",
                                                        param_type: "select",
                                                        data_type: "str",
                                                        default: "scratch_1",
                                                        choices: [
                                                            {
                                                                title: "SCRATCH_1",
                                                                value: "scratch_1",
                                                            },
                                                            {
                                                                title: "SCRATCH_2",
                                                                value: "scratch_2",
                                                            },
                                                            {
                                                                title: "PERSISTENT_1",
                                                                value: "persistent_1",
                                                            },
                                                        ],
                                                        when: {
                                                            and: [
                                                                {
                                                                    param: "default_job_params.scratch_provider",
                                                                    eq: "fsx-lustre-new",
                                                                },
                                                                {
                                                                    param: "default_job_params.enable_scratch",
                                                                    eq: true,
                                                                },
                                                            ],
                                                        },
                                                    },
                                                    {
                                                        name: "default_job_params.fsx_lustre.per_unit_throughput",
                                                        title: "Per Unit Throughput",
                                                        param_type: "select",
                                                        data_type: "int",
                                                        default: "50",
                                                        choices: [
                                                            {
                                                                title: "50",
                                                                value: "50",
                                                            },
                                                            {
                                                                title: "100",
                                                                value: "100",
                                                            },
                                                            {
                                                                title: "200",
                                                                value: "200",
                                                            },
                                                        ],
                                                        when: {
                                                            and: [
                                                                {
                                                                    param: "default_job_params.scratch_provider",
                                                                    eq: "fsx-lustre-new",
                                                                },
                                                                {
                                                                    param: "default_job_params.enable_scratch",
                                                                    eq: true,
                                                                },
                                                            ],
                                                        },
                                                    },
                                                    {
                                                        name: "default_job_params.fsx_lustre.size",
                                                        title: "FSx Lustre Size (GB)",
                                                        param_type: "auto",
                                                        data_type: "memory",
                                                        help_text: "Allowed values: 1200, 2400, 3600, 7200, 10800",
                                                        default: {
                                                            value: 1200,
                                                            unit: "gb",
                                                        },
                                                        when: {
                                                            and: [
                                                                {
                                                                    param: "default_job_params.scratch_provider",
                                                                    eq: "fsx-lustre-new",
                                                                },
                                                                {
                                                                    param: "default_job_params.enable_scratch",
                                                                    eq: true,
                                                                },
                                                            ],
                                                        },
                                                    },
                                                ],
                                            },
                                            {
                                                name: "metrics",
                                                title: "Metrics",
                                                params: [
                                                    {
                                                        name: "default_job_params.enable_system_metrics",
                                                        title: "Enable System Metrics?",
                                                        param_type: "confirm",
                                                        data_type: "bool",
                                                        default: false,
                                                    },
                                                    {
                                                        name: "default_job_params.enable_anonymous_metrics",
                                                        title: "Enable Anonymous Metrics?",
                                                        param_type: "confirm",
                                                        data_type: "bool",
                                                        default: true,
                                                    },
                                                ],
                                            },
                                        ],
                                    },
                                ],
                            }}
                            wizard={{
                                steps: [],
                                i18nStrings: {
                                    stepNumberLabel: (stepNumber: number) => `Step ${stepNumber}`,
                                    collapsedStepsLabel: (stepNumber, stepsCount) => `Step ${stepNumber} of ${stepsCount}`,
                                    cancelButton: "Cancel",
                                    previousButton: "Previous",
                                    nextButton: "Next",
                                    submitButton: this.isCreate() ? "Create Queue Profile" : "Update Queue Profile",
                                    optional: "optional",
                                },
                            }}
                            reviewStep={{
                                title: "Review Queue Profile",
                                description: "Review your queue profile settings",
                            }}
                            onCancel={() => {
                                this.props.navigate("/soca/queues");
                            }}
                            onSubmit={() => {
                                const queueProfile = this.getWizard().getValues();
                                const project_ids = dot.pick("project_ids", queueProfile, true);
                                let projects: any = [];
                                queueProfile.projects = projects;
                                project_ids.forEach((project_id: string) => {
                                    projects.push({
                                        project_id: project_id,
                                    });
                                });
                                const utils = new QueueUtils(queueProfile);

                                let keep_forever = Utils.asBoolean(dot.pick("keep_forever", queueProfile), false);
                                if (keep_forever) {
                                    dot.del("scaling_mode", queueProfile);
                                } else {
                                    const scalingMode = dot.pick("scaling_mode", queueProfile);
                                    if (scalingMode === "single-job") {
                                        queueProfile.terminate_when_idle = 0;
                                    }
                                }

                                if (utils.isScratchStorageEnabled()) {
                                    if (utils.isScratchEBS()) {
                                        dot.del("default_job_params.fsx_lustre", queueProfile);
                                    } else if (utils.isScratchFsxLustre()) {
                                        dot.del("default_job_params.scratch_storage_size", queueProfile);
                                        dot.del("default_job_params.scratch_storage_iops", queueProfile);
                                        dot.str("default_job_params.fsx_lustre.enabled", true, queueProfile);
                                    }
                                } else {
                                    dot.del("default_job_params.scratch_provider", queueProfile);
                                    dot.del("default_job_params.scratch_storage_size", queueProfile);
                                    dot.del("default_job_params.scratch_storage_iops", queueProfile);
                                    dot.del("default_job_params.fsx_lustre", queueProfile);
                                    dot.str(
                                        "default_job_params.fsx_lustre",
                                        {
                                            enabled: false,
                                        },
                                        queueProfile
                                    );
                                }
                                if (!utils.isEnableSpot()) {
                                    dot.del("default_job_params.spot_price", queueProfile);
                                    dot.del("default_job_params.spot_allocation_count", queueProfile);
                                    dot.del("default_job_params.spot_allocation_strategy", queueProfile);
                                }

                                let invoke;
                                if (this.isCreate()) {
                                    invoke = (params: any) => this.schedulerAdmin().createQueueProfile(params);
                                } else {
                                    invoke = (params: any) => this.schedulerAdmin().updateQueueProfile(params);
                                }

                                return invoke({
                                    queue_profile: queueProfile,
                                }).then(
                                    (_) => {
                                        this.props.navigate("/soca/queues");
                                        return true;
                                    },
                                    (error) => {
                                        let message: React.ReactNode;
                                        if (error.payload && error.payload.validation_errors) {
                                            message = (
                                                <div>
                                                    <div>
                                                        <b>{error.message}</b>
                                                    </div>
                                                    {error.payload.validation_errors.results.map((entry: any) => {
                                                        return (
                                                            <li>
                                                                ({entry.error_code}) {entry.message}
                                                            </li>
                                                        );
                                                    })}
                                                </div>
                                            );
                                        } else {
                                            message = <div>{error.message}</div>;
                                        }
                                        this.getWizard().setError(error.errorCode, message);
                                        return false;
                                    }
                                );
                            }}
                        />
                    )
                }
            />
        );
    }
}

export default withRouter(HpcUpdateQueueProfile);
