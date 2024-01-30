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

export class JwtTokenUtils {
    static parseJwtToken(token: string): any {
        let base64Url = token.split(".")[1];
        let base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
        let jsonPayload = decodeURIComponent(
            atob(base64)
                .split("")
                .map(function (c) {
                    return "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2);
                })
                .join("")
        );
        return JSON.parse(jsonPayload);
    }
}

export class JwtTokenClaimsProvider {
    private readonly accessToken: any;
    private readonly idToken: any;
    private readonly dbUsername: any;
    private readonly role: any;

    constructor(accessToken: string, idToken: string, dbUsername: string, role: string) {
        this.accessToken = JwtTokenUtils.parseJwtToken(accessToken);
        this.idToken = JwtTokenUtils.parseJwtToken(idToken);
        this.dbUsername = dbUsername
        this.role = role
    }

    getRole(): string {
        return this.role;
    }

    getDbUsername(): string {
        return this.dbUsername;
    }

    getClientId(): string {
        return this.accessToken.client_id;
    }

    getCognitoUsername(): string {
        return this.accessToken.username;
    }

    getIssuedAt(): number {
        return this.accessToken.iat * 1000;
    }

    getExpiresAt(): number {
        return this.accessToken.exp * 1000;
    }

    getAuthTime(): number {
        return this.accessToken.auth_time * 1000;
    }

    getScope(): string[] {
        let scope = this.accessToken.scope;
        if (scope == null) {
            return [];
        }
        return scope.split(" ");
    }

    getEmail(): string {
        return this.idToken.email;
    }

    getPasswordLastSet(): number {
        let passwordLastSet = this.idToken["custom:password_last_set"];
        if (passwordLastSet == null) {
            return -1;
        }
        return parseInt(passwordLastSet, 10);
    }

    getPasswordMaxAge(): number {
        let passwordLastSet = this.idToken["custom:password_max_age"];
        if (passwordLastSet == null) {
            return -1;
        }
        return parseInt(passwordLastSet, 10);
    }

    getEmailVerified(): boolean {
        return this.idToken["email_verified"];
    }

    getClaims(): JwtTokenClaims {
        return {
            cognito_username: this.getCognitoUsername(),
            db_username: this.getDbUsername(),
            role: this.getRole(),
            issued_at: this.getIssuedAt(),
            expires_at: this.getExpiresAt(),
            auth_time: this.getAuthTime(),
            scope: this.getScope(),
            email: this.getEmail(),
            password_last_set: this.getPasswordLastSet(),
            password_max_age: this.getPasswordMaxAge(),
            email_verified: this.getEmailVerified(),
        };
    }
}

export interface JwtTokenClaims {
    cognito_username: string;
    db_username: string;
    role: string;
    issued_at: number;
    expires_at: number;
    auth_time: number;
    scope: string[];
    email: string;
    password_last_set?: number;
    password_max_age?: number;
    email_verified: boolean;
}
