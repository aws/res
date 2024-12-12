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

import { IdeaSideNavigationProps } from "../../components/side-navigation";
import IdeaAppLayout, { IdeaAppLayoutProps } from "../../components/app-layout";
import { Button, ColumnLayout, Container, Header, SpaceBetween, TextContent, Toggle } from "@cloudscape-design/components";
import { withRouter } from "../../navigation/navigation-utils";
import Utils from "../../common/utils";
import { KeyValue } from "../../components/key-value";
import { AppContext } from "../../common";
import dot from "dot-object";
import IdeaForm from "../../components/form";
import { EnabledDisabledStatusIndicator } from "../../components/common";
import EnableSSOConfigForm from './enable-sso-form';
import { UpdateModuleSettingsRequestIdentityProvider } from "../../client/data-model";
import { EditADDomainForm } from "./edit-ad-domain-form";
import { UpdateModuleSettingsDirectoryService } from '../../client/data-model';

export interface IdentityManagementProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {}

export interface IdentityManagementState {
    identityProvider: any;
    directoryservice: any;
}

class IdentityManagement extends Component<IdentityManagementProps, IdentityManagementState> {
    enableSSOConfigForm: RefObject<IdeaForm>

    constructor(props: IdentityManagementProps) {
        super(props);
        this.enableSSOConfigForm = React.createRef()
        this.state = {
            identityProvider: {},
            directoryservice: {},
        };
    }

    async componentDidMount() {
        try {
            const clusterSettingsService = AppContext.get().getClusterSettingsService();
            const [directoryservice, identityProvider] = await Promise.all([
                clusterSettingsService.getDirectoryServiceSettings(),
                clusterSettingsService.getIdentityProviderSettings(),
            ]);
            this.setState({
                directoryservice,
                identityProvider,
            });
        } catch (error) {
            console.error('Error loading settings:', error);
        }
    }

    getEnableSSOConfigForm(): IdeaForm {
        return this.enableSSOConfigForm.current!
    }

    updateIdentityProviderState = (ssoEnabled: boolean) => {
        const identityProvider = {...this.state.identityProvider};
        dot.set("cognito.sso_enabled", ssoEnabled, identityProvider);
        this.setState({identityProvider: identityProvider});
    };

    buildEnableSSOConfigForm() {
        return (
            <EnableSSOConfigForm
                enableSSOConfigForm={this.enableSSOConfigForm}
                onFlashbarChange={this.props.onFlashbarChange}
                updateIdentityProviderState={this.updateIdentityProviderState}
            />
        );
    }

    updateDirectoryServiceState = (editFormData: UpdateModuleSettingsDirectoryService) => {
        const directoryservice = {...this.state.directoryservice};
        Object.keys(editFormData).forEach((key) => {
            if (typeof editFormData[key] === "object") {
                Object.keys(editFormData[key]).forEach((subKey) => {
                    dot.set(`${key}.${subKey}`, editFormData[key][subKey], directoryservice);
                });
            } else {
                dot.set(key, editFormData[key], directoryservice);
            }
        });
        this.setState({directoryservice: directoryservice});
    }

    buildEditADDomainForm() {
        return (
            <EditADDomainForm
                onFlashbarChange={this.props.onFlashbarChange}
                updateDirectoryServiceState={this.updateDirectoryServiceState}
            />
        )
    }

    render() {
        const isSingleSignOnEnabled = (): boolean => {
            return Utils.asBoolean(dot.pick("cognito.sso_enabled", this.state.identityProvider), false);
        };

        const handleCognitoToggleChange = async (newToggleStatus: boolean, settingToUpdate: string) => {
            const updateSettingsRequest: UpdateModuleSettingsRequestIdentityProvider = {
                module_id: "identity-provider",
                settings: {
                    cognito: {
                        [settingToUpdate]: newToggleStatus
                    }
                },
            };
            try {
                await AppContext.get().client().clusterSettings().updateModuleSettings(updateSettingsRequest);
                this.props.onFlashbarChange({
                    items: [
                        {
                            type: "success",
                            content: "Successfully updated Cognito identity provider setting.",
                            dismissible: true
                        }
                    ]
                })
                const identityProvider = {...this.state.identityProvider}
                const settingPath = "cognito." + settingToUpdate
                dot.set(settingPath , `${newToggleStatus}`, identityProvider)
                this.setState({identityProvider: identityProvider})
            } catch (error: any) {
                this.props.onFlashbarChange({
                    items: [
                        {
                            type: "error",
                            content: error.message,
                            dismissible: true
                        }
                    ]
                })
            }
        }

        return (
            <IdeaAppLayout
                ideaPageId={this.props.ideaPageId}
                toolsOpen={this.props.toolsOpen}
                tools={this.props.tools}
                onPageChange={this.props.onPageChange}
                sideNavHeader={this.props.sideNavHeader}
                sideNavItems={this.props.sideNavItems}
                onSideNavChange={this.props.onSideNavChange}
                onFlashbarChange={this.props.onFlashbarChange}
                flashbarItems={this.props.flashbarItems}
                breadcrumbItems={[
                    {
                        text: "RES",
                        href: "#/",
                    },
                    {
                        text: "Environment Management",
                        href: "#/cluster/status",
                    },
                    {
                        text: "Identity management",
                        href: "",
                    },
                ]}
                header={
                    <Header
                        variant={"h1"}
                        description={"Manage user identities"}
                    >
                        Identity management
                    </Header>
                }
                content={
                    <React.Fragment>
                        <SpaceBetween size="xxl">
                            <Container header={<Header variant={"h2"} description="Cognito user pool metadata. Use this for debugging issues related to the Cognito user pool.">AWS Cognito Directory</Header>}>
                                <SpaceBetween size="xxl">
                                    <ColumnLayout variant={"text-grid"} columns={3}>
                                        <KeyValue title="Provider Name" value={dot.pick("provider", this.state.identityProvider)} />
                                        <KeyValue title="User Pool Id" value={dot.pick("cognito.user_pool_id", this.state.identityProvider)} clipboard={true} type={"cognito:user-pool-id"} />
                                        <KeyValue title="Domain URL" value={dot.pick("cognito.domain_url", this.state.identityProvider)} clipboard={true} />
                                        <KeyValue title="Provider URL" value={dot.pick("cognito.provider_url", this.state.identityProvider)} clipboard={true} />
                                    </ColumnLayout>
                                    <KeyValue title="Use AWS Cognito as user directory">
                                        <div>
                                            <TextContent>
                                                <p><small>Enable this for small scale user cases involving 50 or less users. User sign in through their username and password.<br />Recommended for small teams or for demo purposes.</small></p>
                                            </TextContent>
                                            <div style={{display: 'flex', flexDirection: 'row', gap: '4px'}}>
                                                <EnabledDisabledStatusIndicator enabled={Utils.asBoolean(dot.pick("cognito.enable_native_user_login", this.state.identityProvider))} />
                                                <Toggle
                                                    checked={Utils.asBoolean(dot.pick("cognito.enable_native_user_login", this.state.identityProvider))}
                                                    onChange={async ({ detail }) => await handleCognitoToggleChange(detail.checked, "enable_native_user_login")}
                                                />
                                            </div>
                                        </div>
                                    </KeyValue>
                                    <KeyValue title="User self registration">
                                        <div>
                                            <TextContent>
                                                <p><small>Let anyone sign up for a Cognito user account through the UI</small></p>
                                            </TextContent>
                                            <div style={{display: 'flex', flexDirection: 'row', gap: '4px'}}>
                                                <EnabledDisabledStatusIndicator enabled={Utils.asBoolean(dot.pick("cognito.enable_self_sign_up", this.state.identityProvider))} />
                                                <Toggle
                                                    checked={Utils.asBoolean(dot.pick("cognito.enable_self_sign_up", this.state.identityProvider))}
                                                    onChange={async ({ detail }) => await handleCognitoToggleChange(detail.checked, "enable_self_sign_up")}
                                                />
                                            </div>
                                        </div>
                                    </KeyValue>
                                </SpaceBetween>
                            </Container>
                            <Container header={<Header variant={"h2"} description="AD connection information">Active Directory</Header>}>
                                <SpaceBetween size="xxl">
                                    <ColumnLayout variant={"text-grid"} columns={3}>
                                        <KeyValue title="Provider" value={Utils.getDirectoryServiceTitle(dot.pick("provider", this.state.directoryservice))} />
                                        <KeyValue title="Automation Directory" value={dot.pick("automation_dir", this.state.directoryservice)} clipboard={true} />
                                        <KeyValue title="AD Automation SQS Queue Url" value={dot.pick("ad_automation.sqs_queue_url", this.state.directoryservice)} clipboard={true} />
                                        <KeyValue title="AD Automation DynamoDB Table Name" value={`${AppContext.get().getClusterName()}.ad-automation`} clipboard={true} />
                                        <KeyValue title="Password Max Age" value={dot.pick("password_max_age", this.state.directoryservice)} suffix={"days"} />
                                    </ColumnLayout>
                                    <Container header={<Header variant={"h3"} description="Configuration setting for a specific AD domain">Active Directory Domain {this.buildEditADDomainForm()}</Header>}>
                                    <ColumnLayout variant={"text-grid"} columns={3}>
                                        <KeyValue title="Domain Name" value={dot.pick("name", this.state.directoryservice)}/>
                                        <KeyValue title="Short Name (NETBIOS)" value={dot.pick("ad_short_name", this.state.directoryservice)}/>
                                        <KeyValue title="LDAP Base" value={dot.pick("ldap_base", this.state.directoryservice)}/>
                                        <KeyValue title="LDAP Connection URI" value={dot.pick("ldap_connection_uri", this.state.directoryservice)}/>
                                        <KeyValue title="Service Account User DN" value={dot.pick("root_user_dn", this.state.directoryservice)} clipboard={true}/>
                                        <KeyValue title="Service Account Credentials Secret ARN" value={dot.pick("service_account_credentials_secret_arn", this.state.directoryservice)} clipboard={true} />
                                        <KeyValue title="Users OU" value={dot.pick("users.ou", this.state.directoryservice)}/>
                                        <KeyValue title="Users Filter" value={dot.pick("users_filter", this.state.directoryservice)}/>
                                        <KeyValue title="Groups OU" value={dot.pick("groups.ou", this.state.directoryservice)}/>
                                        <KeyValue title="Groups Filter" value={dot.pick("groups_filter", this.state.directoryservice)}/>
                                        <KeyValue title="Sudoers Group Name" value={dot.pick("sudoers.group_name", this.state.directoryservice)}/>
                                        <KeyValue title="Computers OU" value={dot.pick("computers.ou", this.state.directoryservice)}/>
                                        <KeyValue title="Enable LDAP ID Mapping" value={dot.pick("sssd.ldap_id_mapping", this.state.directoryservice)}/>
                                        <KeyValue title="Disable AD Join" value={dot.pick("disable_ad_join", this.state.directoryservice)}/>
                                        <KeyValue title="Domain TLS Certificate Secret ARN" value={dot.pick("tls_certificate_secret_arn", this.state.directoryservice)} clipboard={true}/>
                                    </ColumnLayout>
                                    </Container>
                                </SpaceBetween>
                            </Container>
                            <Container header={<Header variant={"h2"}>Single Sign-On</Header>}>
                                {this.buildEnableSSOConfigForm()}
                                <ColumnLayout variant={"text-grid"} columns={3}>
                                    <KeyValue title="Status" value={
                                        <div>
                                            <EnabledDisabledStatusIndicator enabled={isSingleSignOnEnabled()} />
                                            <Button iconName="edit" variant="link" onClick={() => this.getEnableSSOConfigForm().showModal()}></Button>
                                        </div>} type={"react-node"}
                                    />
                                    <KeyValue title="SAML Redirect URL" value={`${dot.pick('cognito.domain_url', this.state.identityProvider)}/saml2/idpresponse`} clipboard={true}/>
                                    <KeyValue title="OIDC Redirect URL" value={`${dot.pick('cognito.domain_url', this.state.identityProvider)}/oauth2/idpresponse`} clipboard={true} />
                                </ColumnLayout>
                            </Container>
                        </SpaceBetween>
                    </React.Fragment>
                }
            />
        )
    }
}


export default withRouter(IdentityManagement);
