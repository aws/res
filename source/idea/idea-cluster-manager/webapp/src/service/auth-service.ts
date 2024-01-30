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

import LocalStorageService from "./local-storage-service";
import { User } from "../client/data-model";
import IdeaException from "../common/exceptions";
import { AUTH_LOGIN_CHALLENGE, AUTH_PASSWORD_RESET_REQUIRED, UNAUTHORIZED_ACCESS } from "../common/error-codes";
import Utils from "../common/utils";
import { JwtTokenClaims } from "../common/token-utils";
import { Constants } from "../common/constants";
import { IdeaClients } from "../client";

export interface AuthServiceProps {
    localStorage: LocalStorageService;
    clients: IdeaClients;
}

const KEY_CHALLENGE_NAME = "challenge-name";
const KEY_CHALLENGE_SESSION = "challenge-session";
const KEY_CHALLENGE_PARAMS = "challenge-params";
const KEY_FORGOT_PASSWORD_USERNAME = "forgot-password-username";

class AuthService {
    private readonly props: AuthServiceProps;
    private claims: JwtTokenClaims | null;

    private onLogin?: () => Promise<boolean>;
    private onLogout?: () => Promise<boolean>;

    private activeIsLoggedInPromise: Promise<boolean> | null;

    constructor(props: AuthServiceProps) {
        this.props = props;
        this.claims = null;
        this.activeIsLoggedInPromise = null;
    }

    setHooks(onLogin: () => Promise<boolean>, onLogout: () => Promise<boolean>) {
        this.onLogin = onLogin;
        this.onLogout = onLogout;
    }

    /**
     * login using username and password. invokes Auth.Login API.
     * if Auth.Login is successful, saves the authentication result (accessToken, idToke, refreshToke and expiresIn)
     * in local storage.
     * if Auth.Login returns, a challenge, an exception is thrown with AUTH_LOGIN_CHALLENGE errorCode. invoking component
     * should redirect the user to respective challenge resolution UI
     * @param username
     * @param password
     */
    login(cognito_username: string, password: string): Promise<boolean> {
        return this.props.clients
            .auth()
            .initiateAuth({
                auth_flow: "USER_PASSWORD_AUTH",
                cognito_username: cognito_username,
                password: password,
            })
            .then((result) => {
                if (result.challenge_name) {
                    this.saveChallengeParams(result?.challenge_name!, result?.session!, result?.challenge_params!);
                    throw new IdeaException({
                        errorCode: AUTH_LOGIN_CHALLENGE,
                    });
                } else {
                    return this.props.clients
                        .auth()
                        .getClaims()
                        .then((claims) => {
                            this.claims = claims;
                            if (this.onLogin) {
                                return this.onLogin();
                            } else {
                                return true;
                            }
                        });
                }
            })
            .catch((error) => {
                if (error.errorCode === AUTH_PASSWORD_RESET_REQUIRED) {
                    this.props.localStorage.setItem(KEY_FORGOT_PASSWORD_USERNAME, cognito_username);
                }
                throw error;
            });
    }

    /**
     * login using SSO authorization code
     * if Auth.Login is successful, saves the authentication result (accessToken, idToke, refreshToken and expiresIn)
     * in local storage.
     * @param authorization_code
     */
    login_using_sso_auth_code(authorization_code: string): Promise<boolean> {
        return this.props.clients
            .auth()
            .initiateAuth({
                auth_flow: "SSO_AUTH",
                authorization_code: authorization_code,
            })
            .then((_) => {
                return true;
            })
            .catch((error) => {
                throw error;
            });
    }

    respondToAuthChallenge(newPassword: string): Promise<boolean> {
        const challengeParams = this.getChallengeParams();
        const username = challengeParams.params.USER_ID_FOR_SRP;
        return this.props.clients
            .auth()
            .respondToAuthChallenge({
                challenge_name: challengeParams.challenge_name,
                session: challengeParams.session,
                username: username,
                new_password: newPassword,
            })
            .then((_) => {
                this.props.localStorage.removeItem(KEY_CHALLENGE_NAME);
                this.props.localStorage.removeItem(KEY_CHALLENGE_SESSION);
                this.props.localStorage.removeItem(KEY_CHALLENGE_PARAMS);
                return this.login(username, newPassword);
            });
    }

    getCognitoUsername(): string {
        if (this.claims == null) {
            return "";
        }
        return this.claims.cognito_username;
    }

    /**
     * get user name from the JWT token.
     * the JWT token is not validated or verified.
     * synchronous invocation. to get all current details of the logged in user,
     * call getUser() which returns a Promise<User>
     *
     * this method is expected to be called after the user has logged in to render username
     * in the nav bar.
     */
    getUsername(): string {
        if (this.claims == null) {
            return "";
        }
        return this.claims.db_username;
    }

    getEmail(): string {
        if (this.claims == null) {
            return "";
        }
        return this.claims.email;
    }

    getPasswordLastSet(): Date | null {
        if (this.claims == null) {
            return null;
        }
        if (this.claims.password_last_set === -1) {
            return null;
        }
        return new Date(this.claims.password_last_set!);
    }

    getPasswordMaxAge(): number | null {
        if (this.claims == null) {
            return null;
        }
        if (this.claims.password_max_age === -1) {
            return null;
        }
        return this.claims.password_max_age!;
    }

    isPasswordExpirationApplicable(): boolean {
        return this.getPasswordLastSet() != null;
    }

    getPasswordExpiresInDays(): number {
        const maxAge = this.getPasswordMaxAge();
        const passwordLastSet = this.getPasswordLastSet();
        if (maxAge == null || passwordLastSet == null) {
            return -1;
        }
        const daysAgo = Utils.getDaysBetween(new Date(), passwordLastSet);
        const expiresIn = maxAge - daysAgo;
        if (expiresIn <= 0) {
            return 0;
        }
        return expiresIn;
    }

    getAccessToken(): Promise<string> {
        return this.props.clients.auth().getAccessToken();
    }

    debug() {
        this.props.clients.auth().debug();
    }

    isAdmin(): boolean {
        if (this.claims == null)
            return false
        return this.claims.role == Constants.ADMIN_ROLE
    }

    /**
     * returns the username last saved when user called forgotPassword.
     * this is used when user wants to resend verification email
     */
    getForgotPasswordUserName(): string | null {
        return this.props.localStorage.getItem(KEY_FORGOT_PASSWORD_USERNAME);
    }

    forgotPassword(username: string): Promise<boolean> {
        return this.props.clients
            .auth()
            .forgotPassword({
                username: username,
            })
            .then((_) => {
                this.props.localStorage.setItem(KEY_FORGOT_PASSWORD_USERNAME, username);
                return true;
            });
    }

    confirmForgotPassword(verificationCode: string, password: string): Promise<boolean> {
        const username = this.props.localStorage.getItem(KEY_FORGOT_PASSWORD_USERNAME);
        if (username == null) {
            return Promise.resolve(false);
        }
        return this.props.clients
            .auth()
            .confirmForgotPassword({
                confirmation_code: verificationCode,
                username: username,
                password: password,
            })
            .then((_) => {
                this.props.localStorage.removeItem(KEY_FORGOT_PASSWORD_USERNAME);
                return this.login(username, password);
            });
    }

    isLoggedIn(): Promise<boolean> {
        if (this.activeIsLoggedInPromise != null) {
            return this.activeIsLoggedInPromise;
        }

        this.activeIsLoggedInPromise = this.props.clients
            .auth()
            .isLoggedIn()
            .then((status) => {
                // if already logged in do, nothing
                if (status) {
                    return this.props.clients
                        .auth()
                        .getClaims()
                        .then((claims) => {
                            this.claims = claims;
                            return true;
                        });
                }

                if (typeof window.idea.app.sso === "undefined" || !window.idea.app.sso) {
                    return false;
                }

                // if SSO is enabled, check for SSO auth
                if (Utils.isSsoEnabled()) {
                    let authStatus = window.idea.app.sso_auth_status;
                    if (authStatus) {
                        if (authStatus === "SUCCESS" && window.idea.app.sso_auth_code) {
                            return this.login_using_sso_auth_code(window.idea.app.sso_auth_code).then((status) => {
                                // discard the sso_auth_code after use as auth code is one time use only.
                                // this also prevents re-triggering SSO auth flow after the user has logged out manually.
                                window.idea.app.sso_auth_code = null;
                                if (status) {
                                    return this.props.clients
                                        .auth()
                                        .getClaims()
                                        .then((claims) => {
                                            this.claims = claims;
                                            return true;
                                        });
                                } else {
                                    return false;
                                }
                            });
                        } else {
                            // redirect to login page
                            return false;
                        }
                    } else {
                        window.location.href = "/sso";
                    }
                }
                return false;
            })
            .finally(() => {
                this.activeIsLoggedInPromise = null;
            });

        return this.activeIsLoggedInPromise;
    }

    logout() {
        return this.props.clients
            .auth()
            .logout()
            .then(() => {
                this.claims = null;
            })
            .finally(() => {
                if (this.onLogout) {
                    return this.onLogout().finally();
                } else {
                    return true;
                }
            });
    }

    getUser(): Promise<User> {
        return this.props.clients
            .auth()
            .isLoggedIn()
            .then((status) => {
                if (status) {
                    return this.props.clients
                        .auth()
                        .getUser()
                        .then((result) => {
                            return result!.user!;
                        });
                } else {
                    this.claims = null;
                    throw new IdeaException({
                        errorCode: UNAUTHORIZED_ACCESS,
                    });
                }
            });
    }

    private saveChallengeParams(name: string, session: string, params: any) {
        this.props.localStorage.setItem(KEY_CHALLENGE_NAME, name);
        this.props.localStorage.setItem(KEY_CHALLENGE_SESSION, session);
        this.props.localStorage.setItem(KEY_CHALLENGE_PARAMS, JSON.stringify(params));
    }

    getChallengeParams(): any | null {
        let challengeName = this.props.localStorage.getItem(KEY_CHALLENGE_NAME);
        if (challengeName == null) {
            return null;
        }

        let session = this.props.localStorage.getItem(KEY_CHALLENGE_SESSION);

        let paramsStr = this.props.localStorage.getItem(KEY_CHALLENGE_PARAMS);
        let params = null;
        if (paramsStr != null) {
            params = JSON.parse(paramsStr);
        }
        return {
            challenge_name: challengeName,
            session: session,
            params: params,
        };
    }

    downloadPrivateKey(keyFormat: "pem" | "ppk") {
        return this.props.clients
            .auth()
            .getUserPrivateKey({
                key_format: keyFormat,
                platform: Utils.getPlatform(),
            })
            .then((result) => {
                const element = document.createElement("a");
                element.setAttribute("href", "data:text/plain;charset=utf-8," + result.key_material);
                element.setAttribute("download", result.name!);
                element.style.display = "none";
                document.body.appendChild(element);
                element.click();
                document.body.removeChild(element);
                return true;
            });
    }
}

export default AuthService;
