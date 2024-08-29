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

import {
  BatchPutRoleAssignmentRequest,
  BatchPutRoleAssignmentResponse,
  BatchDeleteRoleAssignmentRequest,
  BatchDeleteRoleAssignmentResponse,
  ListRoleAssignmentsRequest,
  ListRoleAssignmentsResponse,
  ListRolesRequest,
  ListRolesResponse,
  GetRoleRequest,
  GetRoleResponse,
  CreateRoleRequest,
  CreateRoleResponse,
  DeleteRoleRequest,
  DeleteRoleResponse,
  UpdateRoleRequest,
  UpdateRoleResponse,
} from "./data-model";

import IdeaBaseClient, { IdeaBaseClientProps } from "./base-client";

export interface AuthzClientProps extends IdeaBaseClientProps {
    baseUrl: string;
    apiContextPath: string;
    serviceWorkerRegistration?: ServiceWorkerRegistration;
}

class AuthzClient extends IdeaBaseClient<AuthzClientProps> {

  batchPutRoleAssignment(request: BatchPutRoleAssignmentRequest): Promise<BatchPutRoleAssignmentResponse> {
    return this.apiInvoker.invoke_alt<BatchPutRoleAssignmentRequest, BatchPutRoleAssignmentResponse>("Authz.BatchPutRoleAssignment", request);
  }

  batchDeleteRoleAssignment(request: BatchDeleteRoleAssignmentRequest): Promise<BatchDeleteRoleAssignmentResponse> {
      return this.apiInvoker.invoke_alt<BatchDeleteRoleAssignmentRequest, BatchDeleteRoleAssignmentResponse>("Authz.BatchDeleteRoleAssignment", request);
  }

  listRoleAssignments(request: ListRoleAssignmentsRequest): Promise<ListRoleAssignmentsResponse> {
    return this.apiInvoker.invoke_alt<ListRoleAssignmentsRequest, ListRoleAssignmentsResponse>("Authz.ListRoleAssignments", request);
  }

  listRoles(request: ListRolesRequest): Promise<ListRolesResponse> {
    return this.apiInvoker.invoke_alt<ListRolesRequest, ListRolesResponse>("Authz.ListRoles", request);
  }
  
  getRole(request: GetRoleRequest): Promise<GetRoleResponse> {
    return this.apiInvoker.invoke_alt<GetRoleRequest, GetRoleResponse>("Authz.GetRole", request);
  }

  createRole(request: CreateRoleRequest): Promise<CreateRoleResponse> {
    return this.apiInvoker.invoke_alt<CreateRoleRequest, CreateRoleResponse>("Authz.CreateRole", request);
  }

  deleteRole(request: DeleteRoleRequest): Promise<DeleteRoleResponse> {
    return this.apiInvoker.invoke_alt<DeleteRoleRequest, DeleteRoleResponse>("Authz.DeleteRole", request);
  }

  updateRole(request: UpdateRoleRequest): Promise<UpdateRoleResponse> {
    return this.apiInvoker.invoke_alt<UpdateRoleRequest, UpdateRoleResponse>("Authz.UpdateRole", request);
  }
}

export default AuthzClient;