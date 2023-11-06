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

export interface LocalStorageServiceProps {
    prefix: string;
}

class LocalStorageService {
    private props: LocalStorageServiceProps;

    constructor(props: LocalStorageServiceProps) {
        this.props = props;
    }

    buildKey(key: string): string {
        return `${this.props.prefix}.${key}`;
    }

    getItem(key: string): string | null {
        return localStorage.getItem(this.buildKey(key));
    }

    removeItem(key: string) {
        localStorage.removeItem(this.buildKey(key));
    }

    setItem(key: string, value: string) {
        localStorage.setItem(this.buildKey(key), value);
    }
}

export default LocalStorageService;
