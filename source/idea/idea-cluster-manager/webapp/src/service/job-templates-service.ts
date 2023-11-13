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

import { openDB, DBSchema } from "idb";
import { IDBPDatabase } from "idb/build/entry";
import Utils from "../common/utils";
import IdeaException from "../common/exceptions";

export interface JobTemplatesServiceProps {}

export interface JobTemplate {
    id?: string;
    title?: string;
    description?: string;
    template_data: string;
    created_on?: number;
    updated_on?: number;
}

interface JobTemplatesDB extends DBSchema {
    job_templates: {
        value: JobTemplate;
        key: string;
        indexes: {
            by_title: string;
            by_description: string;
            by_updated_on: number;
        };
    };
}

class JobTemplatesService {
    private readonly props: JobTemplatesServiceProps;
    private db: IDBPDatabase<JobTemplatesDB> | null;

    constructor(props: JobTemplatesServiceProps) {
        this.props = props;
        this.db = null;
        this.initialize().finally();
    }

    async initialize() {
        this.db = await openDB<JobTemplatesDB>("local-db", 1, {
            upgrade(db) {
                const jobTemplatesStore = db.createObjectStore("job_templates", {
                    keyPath: "id",
                });
                jobTemplatesStore.createIndex("by_title", "title");
                jobTemplatesStore.createIndex("by_description", "description");
                jobTemplatesStore.createIndex("by_updated_on", "updated_on");
            },
        });
    }

    createJobTemplate(jobTemplate: JobTemplate): Promise<JobTemplate> {
        if (this.db) {
            const created = {
                id: Utils.getUUID(),
                title: jobTemplate.title,
                description: jobTemplate.description,
                template_data: jobTemplate.template_data,
                created_on: new Date().getTime(),
                updated_on: new Date().getTime(),
            };
            return this.db.put("job_templates", created).then(() => {
                return created;
            });
        } else {
            return Promise.reject(
                new IdeaException({
                    errorCode: "LOCAL_DB_NOT_INITIALIZED",
                    message: "Local Storage DB not yet initialized",
                })
            );
        }
    }

    updateJobTemplate(jobTemplate: JobTemplate) {
        if (this.db) {
            const db = this.db;
            if (jobTemplate.id == null || Utils.isEmpty(jobTemplate.id)) {
                return Promise.reject(
                    new IdeaException({
                        errorCode: "INVALID_PARAMS",
                        message: "id is required",
                    })
                );
            }
            return db
                .get("job_templates", jobTemplate.id)
                .then((existing) => {
                    if (!existing) {
                        throw new IdeaException({
                            errorCode: "JOB_TEMPLATE_NOT_FOUND",
                            message: `Job Template not found for id: ${jobTemplate.id}`,
                        });
                    }
                    return {
                        id: existing.id,
                        title: jobTemplate.title ? jobTemplate.title : existing.title,
                        description: jobTemplate.description ? jobTemplate.description : existing.description,
                        template_data: jobTemplate.template_data ? jobTemplate.template_data : existing.template_data,
                        created_on: existing.created_on,
                        updated_on: new Date().getTime(),
                    };
                })
                .then((toUpdate) => {
                    return db.put("job_templates", toUpdate).then(() => {
                        return toUpdate;
                    });
                });
        } else {
            return Promise.reject(
                new IdeaException({
                    errorCode: "LOCAL_DB_NOT_INITIALIZED",
                    message: "Local Storage DB not yet initialized",
                })
            );
        }
    }

    getJobTemplate(id: string): Promise<JobTemplate> {
        if (this.db == null) {
            return Promise.reject(
                new IdeaException({
                    errorCode: "LOCAL_DB_NOT_INITIALIZED",
                    message: "Local Storage DB not yet initialized",
                })
            );
        }
        return this.db.get("job_templates", id).then((result) => {
            if (!result) {
                throw new IdeaException({
                    errorCode: "JOB_TEMPLATE_NOT_FOUND",
                    message: `Job Template not found for id: ${id}`,
                });
            }
            return result;
        });
    }

    deleteJobTemplate(id: string): Promise<boolean> {
        if (this.db == null) {
            return Promise.reject(
                new IdeaException({
                    errorCode: "LOCAL_DB_NOT_INITIALIZED",
                    message: "Local Storage DB not yet initialized",
                })
            );
        }
        return this.db.delete("job_templates", id).then(() => {
            return true;
        });
    }

    listJobTemplates(): Promise<JobTemplate[]> {
        if (this.db == null) {
            return Promise.reject(
                new IdeaException({
                    errorCode: "LOCAL_DB_NOT_INITIALIZED",
                    message: "Local Storage DB not yet initialized",
                })
            );
        }
        return this.db.getAll("job_templates");
    }
}

export default JobTemplatesService;
