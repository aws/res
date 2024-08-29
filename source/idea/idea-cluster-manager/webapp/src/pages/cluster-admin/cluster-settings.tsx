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
import { Box, Button, ColumnLayout, Container, Header, Link, SpaceBetween, Tabs } from "@cloudscape-design/components";
import { KeyValue } from "../../components/key-value";
import IdeaForm from "../../components/form";
import { AppContext } from "../../common";
import dot from "dot-object";
import Utils from "../../common/utils";
import { EnabledDisabledStatusIndicator } from "../../components/common";
import { Constants } from "../../common/constants";
import { withRouter } from "../../navigation/navigation-utils";
import ConfigUtils from "../../common/config-utils";
import { UpdateModuleSettingsRequestWebPortal, UpdateModuleSettingsValuesWebPortal } from "../../client/data-model";

export interface ClusterSettingsProps extends IdeaAppLayoutProps, IdeaSideNavigationProps {}

export interface ClusterSettingsState {
    cluster: any;
    identityProvider: any;
    directoryservice: any;
    clusterManager: any;
    activeTabId: string;
}

const DEFAULT_ACTIVE_TAB_ID = "general";

class ClusterSettings extends Component<ClusterSettingsProps, ClusterSettingsState> {
    updateWebPortalSettingsForm: RefObject<IdeaForm>;
    enableSSOConfigForm: RefObject<IdeaForm>

    constructor(props: ClusterSettingsProps) {
        super(props);
        this.enableSSOConfigForm = React.createRef()
        this.state = {
            cluster: {},
            identityProvider: {},
            directoryservice: {},
            clusterManager: {},
            activeTabId: DEFAULT_ACTIVE_TAB_ID,
        };
        this.updateWebPortalSettingsForm = React.createRef();
    }

    buildUpdateWebPortalSettingsForm() {
        return (
            <IdeaForm
                ref={this.updateWebPortalSettingsForm}
                name="update-web-portal-settings"
                modal={true}
                title="Update Web Portal Settings"
                onSubmit={() => {
                    if (!this.updateWebPortalSettingsForm.current?.validate()) {
                        return;
                    }
                    const values = this.updateWebPortalSettingsForm.current?.getValues();
                    const updateSettings: UpdateModuleSettingsRequestWebPortal = {
                        module_id: 'cluster-manager',
                        settings : {
                            web_portal: {
                            }
                        }
                    }
                    if (values.title !== dot.pick("web_portal.title", this.state.clusterManager)) {
                        updateSettings.settings.web_portal[UpdateModuleSettingsValuesWebPortal.TITLE] = values.title;
                    }
                    if (values.subtitle !== dot.pick("web_portal.subtitle", this.state.clusterManager)) {
                        updateSettings.settings.web_portal[UpdateModuleSettingsValuesWebPortal.SUBTITLE] = values.subtitle;
                    }
                    if (Object.keys(updateSettings.settings.web_portal).length > 0) {
                        AppContext.get()
                            .client()
                            .clusterSettings()
                            .updateModuleSettings(updateSettings)
                            .then(() => {
                                this.props.onFlashbarChange({
                                    items: [
                                        {
                                            type: "success",
                                            content: "Web portal settings updated successfully.",
                                            dismissible: true,
                                        },
                                    ],
                                });
                                this.loadSettings();
                                this.updateWebPortalSettingsForm.current?.hideModal();
                            })
                            .catch((error) => {
                                this.updateWebPortalSettingsForm.current?.setError(error.errorCode, error.message);
                            });
                    } else {
                        this.updateWebPortalSettingsForm.current?.setError("400", "No settings updated.");
                    }
                }}
                onCancel={() => {
                    this.updateWebPortalSettingsForm.current?.hideModal();
                }}
                params={[
                    {
                        name: "title",
                        title: "Title",
                        validate: {
                            required: true,
                        },
                        default: dot.pick("web_portal.title", this.state.clusterManager),
                    },
                    {
                        name: "subtitle",
                        title: "Subtitle",
                        validate: {
                            required: true,
                        },
                        default: dot.pick("web_portal.subtitle", this.state.clusterManager),
                    },
                ]}
            />
        );
    }

    componentDidMount() {
        this.loadSettings();
    }

    loadSettings() {
        let promises: Promise<any>[] = [];
        const clusterSettingsService = AppContext.get().getClusterSettingsService();
        // 0
        promises.push(clusterSettingsService.getClusterSettings());
        // 1
        promises.push(clusterSettingsService.getIdentityProviderSettings());
        // 2
        promises.push(clusterSettingsService.getDirectoryServiceSettings());
        // 3
        promises.push(clusterSettingsService.getClusterManagerSettings(false));
        const queryParams = new URLSearchParams(this.props.location.search);
        const activeTabId = Utils.asString(queryParams.get("tab"), DEFAULT_ACTIVE_TAB_ID);
        Promise.all(promises).then((result) => {
            this.setState({
                cluster: result[0],
                identityProvider: result[1],
                directoryservice: result[2],
                clusterManager: result[3],
                activeTabId: activeTabId,
            }, () => {
                this.updateWebPortalSettingsForm.current?.registry.list().map((field) => {
                    field.setState({default: field.props.param.default});
                });
                this.updateWebPortalSettingsForm.current?.reset();
            });
        });
    }

    getEnableSSOConfigForm(): IdeaForm {
        return this.enableSSOConfigForm.current!
    }

    buildEnableSSOConfigForm() {
        return <IdeaForm
            ref={this.enableSSOConfigForm}
            name="enable-sso-config-form"
            title="Single Sign On Configuration"
            modal={true}
            modalSize="medium"
            onSubmit={() => {
                if (!this.getEnableSSOConfigForm().validate()) {
                    return Promise.resolve(false);
                }
                let values: any = this.getEnableSSOConfigForm().getValues();
                AppContext.get().client().auth().configureSSO(values)
                    .then(() => {
                        this.props.onFlashbarChange({
                            items: [
                                {
                                    type: "success",
                                    content: "Single sign on successfully enabled.",
                                    dismissible: true,
                                },
                            ],
                        })
                        this.loadSettings();
                        this.enableSSOConfigForm.current?.hideModal();
                    })
                    .catch((error) => {
                        this.getEnableSSOConfigForm().setError(error.errorCode, error.message);
                        return false;
                    });
            }}
            params={[
                {
                    name: 'provider_type',
                    title: 'Identity Provider',
                    description: 'Choose the third-party identity provider that you would like to configure.',
                    param_type: 'tiles',
                    data_type: "str",
                    choices: [
                        {
                            title: 'SAML',
                            value: 'SAML',
                            description: 'Configure trust between Cognito and a SAML 2.0-compatible identity provider.'
                        },
                        {
                            title: 'OIDC',
                            value: 'OIDC',
                            description: 'Configure trust between Cognito and an OIDC identity provider,'
                        }
                    ],
                    validate: {
                        required: true
                    }
                },
                {
                    name: 'provider_name',
                    title: 'Provider Name',
                    description: "Name used for the provider in cognito",
                    validate: {
                        required: true
                    },
                    when: {or: [
                        {
                            param: "provider_type",
                            eq: "SAML"
                        },
                        {
                            param: "provider_type",
                            eq: "OIDC"
                        }
                    ]},
                },
                {
                    name: 'metadata_source',
                    title: 'Metadata Document Source',
                    description: 'Provide a SAML metadata document. This document is issued by your SAML provider.',
                    param_type: 'radio-group',
                    data_type: "str",
                    default: "upload",
                    choices: [
                        {
                            title: 'Upload metadata document',
                            value: 'upload'
                        },
                        {
                            title: 'Enter metadata document endpoint URL',
                            value: 'url'
                        }
                    ],
                    when: {
                        param: 'provider_type',
                        eq: 'SAML'
                    },
                    validate: {
                        required: true
                    }
                },
                {
                    name: 'saml_metadata_file',
                    title: 'Metadata document',
                    param_type: 'file-upload',
                    validate: {
                        required: true
                    },
                    when: { and: [
                        {
                            param: 'metadata_source',
                            eq: 'upload',
                        },
                        {
                            param: 'provider_type',
                            eq: 'SAML'
                        }
                    ]},
                },
                {
                    name: 'saml_metadata_url',
                    title: 'Enter metadata document endpoint URL',
                    default: 'https://',
                    when: { and: [
                        {
                            param: 'metadata_source',
                            eq: 'url',
                        },
                        {
                            param: 'provider_type',
                            eq: 'SAML'
                        }
                    ]},
                    validate: {
                        required: true
                    }
                },
                {
                    name: 'oidc_client_id',
                    title: 'Client ID',
                    description: 'Enter the client ID provided by OpenID Connect identity provider.',
                    when: {
                            param: "provider_type",
                            eq: "OIDC"
                        },
                    validate: {
                        required: true
                    }
                },
                {
                    name: 'oidc_client_secret',
                    title: 'Client Secret',
                    description: 'Enter the client secret provided by OpenID Connect identity provider.',
                    when: {
                            param: "provider_type",
                            eq: "OIDC"
                        },
                    validate: {
                        required: true
                    }
                },
                {
                    name: 'oidc_authorize_scopes',
                    title: 'Authorized scopes',
                    param_type: "text",
                    description: 'Choose the OAuth 2.0 scopes that you will request from OpenID Connect. Separate scopes with spaces',
                    when: {
                            param: "provider_type",
                            eq: "OIDC"
                        },
                    validate: {
                        required: true
                    }
                },
                {
                    name: 'oidc_attributes_request_method',
                    title: 'Attribute request method',
                    description: 'The request method is configured in the provider application.',
                    param_type: 'radio-group',
                    data_type: "str",
                    default: "GET",
                    choices: [
                        {
                            title: 'GET',
                            value: 'GET'
                        },
                        {
                            title: 'POST',
                            value: 'POST'
                        }
                    ],
                    when: {
                        param: 'provider_type',
                        eq: 'OIDC'
                    },
                    validate: {
                        required: true
                    }
                },
                {
                    name: 'oidc_issuer',
                    title: 'Issuer URL',
                    description: 'Enter the issuer URL you received from the OIDC provider.',
                    default: 'https://',
                    when: {
                            param: 'provider_type',
                            eq: 'OIDC'
                        },
                    validate: {
                        required: true
                    }
                },
                {
                    name: 'oidc_authorize_url',
                    title: 'Authorization endpoint',
                    description: 'The authorization endpoint is used by Cognito to redirect app users to your provider to sign in.',
                    default: 'https://',
                    when: {
                            param: 'provider_type',
                            eq: 'OIDC'
                        },
                    validate: {
                        required: true
                    }
                },
                {
                    name: 'oidc_token_url',
                    title: 'Token endpoint',
                    description: 'The token endpoint is used by Cognito to exchange OIDC authorization codes for tokens.',
                    default: 'https://',
                    when: {
                            param: 'provider_type',
                            eq: 'OIDC'
                        },
                    validate: {
                        required: true
                    }
                },
                {
                    name: 'oidc_attributes_url',
                    title: 'UserInfo endpoint',
                    description: 'The userInfo endpoint is used by Cognito to retrieve information about the authenticated user.',
                    default: 'https://',
                    when: {
                            param: 'provider_type',
                            eq: 'OIDC'
                        },
                    validate: {
                        required: true
                    }
                },
                {
                    name: 'oidc_jwks_uri',
                    title: 'Jwks_uri endpoint',
                    description: 'The JSON Web Key Set URI (jwks_uri) endpoint provides cryptographic information necessary to validate the provider\'s tokens.',
                    default: 'https://',
                    when: {
                            param: 'provider_type',
                            eq: 'OIDC'
                        },
                    validate: {
                        required: true
                    }
                },
                {
                    name: 'provider_email_attribute',
                    title: 'Provider Email Attribute',
                    description: "The Email attribute used to map email between your idp and the Amazon Cognito user pool",
                    validate: {
                        required: true
                    },
                    when: {or: [
                        {
                            param: "provider_type",
                            eq: "SAML"
                        },
                        {
                            param: "provider_type",
                            eq: "OIDC"
                        }
                    ]}
                },
                {
                    name: "refresh_token_validity_Hours",
                    title: "Refresh Token Expiration (hours)",
                    description: "Must be between 1 and 87600 (10 years)",
                    data_type: "int",
                    param_type: "text",
                    default: 12,
                    validate: {
                        required: true,
                        min: 1,
                        max: 87600
                    },
                    when: {or: [
                        {
                            param: "provider_type",
                            eq: "SAML"
                        },
                        {
                            param: "provider_type",
                            eq: "OIDC"
                        }
                    ]}
                }
            ]}
        />
    }

    render() {
        const isExternalAlbCertSelfSigned = (): boolean => {
            return !Utils.asBoolean(dot.pick("load_balancers.external_alb.certificates.provided", this.state.cluster), false);
        };

        const isSingleSignOnEnabled = (): boolean => {
            return Utils.asBoolean(dot.pick("cognito.sso_enabled", this.state.identityProvider), false);
        };

        const isDirectoryServiceOpenLDAP = (): boolean => {
            return dot.pick("provider", this.state.directoryservice) === "openldap";
        };

        const isDirectoryServiceActiveDirectory = (): boolean => {
            let provider = dot.pick("provider", this.state.directoryservice);
            return provider === "activedirectory" || provider === "aws_managed_activedirectory";
        };

        const getClusterManagerOpenAPISpecUrl = () => {
            return `${AppContext.get().getHttpEndpoint()}${Utils.getApiContextPath(Constants.MODULE_CLUSTER_MANAGER)}/openapi.yml`;
        };

        const getClusterManagerSwaggerEditorUrl = () => {
            return `https://editor.swagger.io/?url=${getClusterManagerOpenAPISpecUrl()}`;
        };

        const isBackupEnabled = () => {
            return Utils.asBoolean(dot.pick("backups.enabled", this.state.cluster));
        };

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
                        text: "RES",
                        href: "#/",
                    },
                    {
                        text: "Environment Management",
                        href: "#/cluster/status",
                    },
                    {
                        text: "Settings",
                        href: "",
                    },
                ]}
                header={
                    <Header
                        variant={"h1"}
                        description={"View and manage environment settings."}
                        actions={
                            <SpaceBetween size={"s"}>
                                <Button variant={"primary"} onClick={() => this.props.navigate("/cluster/status")}>
                                    View Environment Status
                                </Button>
                            </SpaceBetween>
                        }
                    >
                        Environment Settings
                    </Header>
                }
                contentType={"default"}
                content={
                    <SpaceBetween size={"l"}>
                        {this.buildUpdateWebPortalSettingsForm()}
                        <Container>
                            <ColumnLayout variant={"text-grid"} columns={3}>
                                <KeyValue title="Environment Name" value={dot.pick("cluster_name", this.state.cluster)} clipboard={true} />
                                <KeyValue title="AWS Region" value={dot.pick("aws.region", this.state.cluster)} />
                                <KeyValue title="S3 Bucket" value={dot.pick("cluster_s3_bucket", this.state.cluster)} clipboard={true} type={"s3:bucket-name"} />
                            </ColumnLayout>
                        </Container>
                        <Tabs
                            activeTabId={this.state.activeTabId}
                            onChange={(event) => {
                                this.setState(
                                    {
                                        activeTabId: event.detail.activeTabId,
                                    },
                                    () => {
                                        this.props.searchParams.set("tab", event.detail.activeTabId);
                                        this.props.setSearchParams(this.props.searchParams);
                                    }
                                );
                            }}
                            tabs={[
                                {
                                    label: "General",
                                    id: "general",
                                    content: (
                                        <SpaceBetween size="m">
                                            <Container header={<Header variant={"h2"}>General Settings</Header>}>
                                                <ColumnLayout variant={"text-grid"} columns={3}>
                                                    <KeyValue title="Administrator Username" value={dot.pick("administrator_username", this.state.cluster)} />
                                                    <KeyValue title="Administrator Email" value={dot.pick("administrator_email", this.state.cluster)} clipboard={true} />
                                                    <KeyValue title="Home Directory" value={dot.pick("home_dir", this.state.cluster)} clipboard={true} />
                                                    <KeyValue title="Locale" value={dot.pick("locale", this.state.cluster)} />
                                                    <KeyValue title="Timezone" value={dot.pick("timezone", this.state.cluster)} />
                                                    <KeyValue title="Default Encoding" value={dot.pick("encoding", this.state.cluster)} />
                                                </ColumnLayout>
                                            </Container>
                                            <Container
                                                header={
                                                    <Header
                                                        variant={"h2"}
                                                        actions={
                                                            <Button
                                                                iconName="edit"
                                                                onClick={() => {
                                                                    this.updateWebPortalSettingsForm.current?.showModal();
                                                                }}
                                                            />
                                                        }
                                                    >
                                                        Web Portal
                                                    </Header>
                                                }
                                            >
                                                <ColumnLayout variant={"text-grid"} columns={3}>
                                                    <KeyValue title="Title" value={dot.pick("web_portal.title", this.state.clusterManager)}/>
                                                    <KeyValue title="Subtitle" value={dot.pick("web_portal.subtitle", this.state.clusterManager)}/>
                                                    <KeyValue title="Copyright Text" value={dot.pick("web_portal.copyright_text", this.state.clusterManager)}/>
                                                </ColumnLayout>
                                            </Container>
                                            <Container
                                                header={
                                                    <Header
                                                        variant={"h2"}
                                                        info={
                                                            <Link external={true} href={"https://spec.openapis.org/oas/v3.1.0"}>
                                                                Info
                                                            </Link>
                                                        }
                                                    >
                                                        OpenAPI Specification
                                                    </Header>
                                                }
                                            >
                                                <ColumnLayout variant={"text-grid"} columns={1}>
                                                    <KeyValue title="Environment Manager API Spec" value={getClusterManagerOpenAPISpecUrl()} type={"external-link"} clipboard />
                                                </ColumnLayout>
                                            </Container>
                                        </SpaceBetween>
                                    ),
                                },
                                {
                                    label: "Network",
                                    id: "network",
                                    content: (
                                        <SpaceBetween size={"l"}>
                                            <Container header={<Header variant={"h2"}>VPC</Header>}>
                                                <ColumnLayout variant={"text-grid"} columns={3}>
                                                    <KeyValue title="VPC Id" value={dot.pick("network.vpc_id", this.state.cluster)} clipboard={true} />
                                                    <KeyValue title="Private Subnets" value={dot.pick("network.private_subnets", this.state.cluster)} clipboard={true} />
                                                    <KeyValue title="Public Subnets" value={dot.pick("network.public_subnets", this.state.cluster)} clipboard={true} />
                                                    <KeyValue title="Cluster Prefix List Id" value={dot.pick("network.cluster_prefix_list_id", this.state.cluster)} clipboard={true} />
                                                    <KeyValue title="Existing VPC?" value={dot.pick("network.use_existing_vpc", this.state.cluster)} type={"boolean"} />
                                                </ColumnLayout>
                                            </Container>
                                            <Container header={<Header variant={"h2"}>Security Groups</Header>}>
                                                <ColumnLayout variant={"text-grid"} columns={3}>
                                                    <KeyValue title="Bastion Host" value={dot.pick("network.security_groups.bastion-host", this.state.cluster)} clipboard={true} type={"ec2:security-group-id"} />
                                                    <KeyValue title="External Load Balancer" value={dot.pick("network.security_groups.external-load-balancer", this.state.cluster)} clipboard={true} type={"ec2:security-group-id"} />
                                                    <KeyValue title="Internal Load Balancer" value={dot.pick("network.security_groups.internal-load-balancer", this.state.cluster)} clipboard={true} type={"ec2:security-group-id"} />
                                                    <KeyValue title="Default Security Group" value={dot.pick("network.security_groups.cluster", this.state.cluster)} clipboard={true} type={"ec2:security-group-id"} />
                                                </ColumnLayout>
                                            </Container>
                                            <Container header={<Header variant={"h2"}>External Load Balancer</Header>}>
                                                <SpaceBetween size={"m"}>
                                                    <ColumnLayout variant={"text-grid"} columns={2}>
                                                        <KeyValue title="Load Balancer DNS Name" value={ConfigUtils.getExternalAlbDnsName(this.state.cluster)} clipboard={true} />
                                                        <KeyValue title="Custom DNS Name" value={ConfigUtils.getExternalAlbCustomDnsName(this.state.cluster)} clipboard={true} />
                                                        <KeyValue title="Load Balancer ARN" value={ConfigUtils.getExternalAlbArn(this.state.cluster)} clipboard={true} />
                                                        <KeyValue title="Deploy in Public Subnets?" value={dot.pick("load_balancers.external_alb.public", this.state.cluster)} type={"boolean"} />
                                                    </ColumnLayout>
                                                    <Box>
                                                        <h3>SSL/TLS Settings</h3>
                                                        <ColumnLayout variant={"text-grid"} columns={2}>
                                                            <KeyValue title="Certificates" value={isExternalAlbCertSelfSigned() ? "Self-Signed" : "ACM"} />
                                                            {isExternalAlbCertSelfSigned() && <KeyValue title="Certificate Secret ARN" value={ConfigUtils.getExternalAlbCertificateSecretArn(this.state.cluster)} clipboard={true} />}
                                                            {isExternalAlbCertSelfSigned() && <KeyValue title="Certificate Private Key Secret ARN" value={ConfigUtils.getExternalAlbPrivateKeySecretArn(this.state.cluster)} clipboard={true} />}
                                                            <KeyValue title="ACM Certificate ARN" value={ConfigUtils.getExternalAlbAcmCertificateArn(this.state.cluster)} clipboard={true} />
                                                        </ColumnLayout>
                                                    </Box>
                                                </SpaceBetween>
                                            </Container>
                                            <Container header={<Header variant={"h2"}>Internal Load Balancer</Header>}>
                                                <SpaceBetween size={"m"}>
                                                    <ColumnLayout variant={"text-grid"} columns={2}>
                                                        <KeyValue title="Load Balancer DNS Name" value={ConfigUtils.getInternalAlbDnsName(this.state.cluster)} clipboard={true} />
                                                        <KeyValue title="Custom DNS Name" value={ConfigUtils.getInternalAlbCustomDnsName(this.state.cluster)} clipboard={true} />
                                                        <KeyValue title="Load Balancer ARN" value={ConfigUtils.getInternalAlbArn(this.state.cluster)} clipboard={true} />
                                                    </ColumnLayout>
                                                    <Box>
                                                        <h3>SSL/TLS Settings</h3>
                                                        <ColumnLayout variant={"text-grid"} columns={2}>
                                                            <KeyValue title="Certificates" value="Self-Signed" />
                                                            <KeyValue title="Certificate Secret ARN" value={ConfigUtils.getInternalAlbCertificateSecretArn(this.state.cluster)} clipboard={true} />
                                                            <KeyValue title="Certificate Private Key Secret ARN" value={ConfigUtils.getInternalAlbPrivateKeySecretArn(this.state.cluster)} clipboard={true} />
                                                            <KeyValue title="ACM Certificate ARN" value={ConfigUtils.getInternalAlbAcmCertificateArn(this.state.cluster)} clipboard={true} />
                                                        </ColumnLayout>
                                                    </Box>
                                                </SpaceBetween>
                                            </Container>
                                        </SpaceBetween>
                                    ),
                                },
                                {
                                    label: "Identity Provider",
                                    id: "identity-provider",
                                    content: (
                                        <SpaceBetween size={"l"}>
                                            <Container header={<Header variant={"h2"}>Identity Provider</Header>}>
                                                <ColumnLayout variant={"text-grid"} columns={3}>
                                                    <KeyValue title="Provider Name" value={dot.pick("provider", this.state.identityProvider)} />
                                                    <KeyValue title="User Pool Id" value={dot.pick("cognito.user_pool_id", this.state.identityProvider)} clipboard={true} type={"cognito:user-pool-id"} />
                                                    <KeyValue title="Domain URL" value={dot.pick("cognito.domain_url", this.state.identityProvider)} clipboard={true} />
                                                    <KeyValue title="Provider URL" value={dot.pick("cognito.provider_url", this.state.identityProvider)} clipboard={true} />
                                                </ColumnLayout>
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
                                    ),
                                },
                                {
                                    label: "Directory Service",
                                    id: "directory-service",
                                    content: (
                                        <SpaceBetween size={"l"}>
                                            <Container header={<Header variant={"h2"}>Directory Service</Header>}>
                                                <ColumnLayout variant={"text-grid"} columns={2}>
                                                    <KeyValue title="Provider" value={Utils.getDirectoryServiceTitle(dot.pick("provider", this.state.directoryservice))} />
                                                    <KeyValue title="Automation Directory" value={dot.pick("automation_dir", this.state.directoryservice)} clipboard={true} />
                                                    <KeyValue title="Root Username Secret ARN" value={dot.pick("root_username_secret_arn", this.state.directoryservice)} clipboard={true} />
                                                    <KeyValue title="Root Password Secret ARN" value={dot.pick("root_password_secret_arn", this.state.directoryservice)} clipboard={true} />
                                                </ColumnLayout>
                                            </Container>
                                            {isDirectoryServiceOpenLDAP() && (
                                                <Container header={<Header variant={"h2"}>OpenLDAP Settings</Header>}>
                                                    <SpaceBetween size={"m"}>
                                                        <ColumnLayout variant={"text-grid"} columns={3}>
                                                            <KeyValue title="Name" value={dot.pick("name", this.state.directoryservice)} clipboard={true} />
                                                            <KeyValue title="LDAP Base" value={dot.pick("ldap_base", this.state.directoryservice)} clipboard={true} />
                                                            <KeyValue title="LDAP Connection URI" value={dot.pick("ldap_connection_uri", this.state.directoryservice)} clipboard={true} />
                                                        </ColumnLayout>
                                                        <Box>
                                                            <h3>EC2 Instance Details</h3>
                                                            <ColumnLayout variant={"text-grid"} columns={3}>
                                                                <KeyValue title="Hostname" value={dot.pick("hostname", this.state.directoryservice)} clipboard={true} />
                                                                <KeyValue title="Private IP" value={dot.pick("private_ip", this.state.directoryservice)} clipboard={true} />
                                                                <KeyValue title="Instance Id" value={dot.pick("instance_id", this.state.directoryservice)} clipboard={true} type={"ec2:instance-id"} />
                                                                <KeyValue title="Instance Type" value={dot.pick("instance_type", this.state.directoryservice)} />
                                                                <KeyValue title="Security Group Id" value={dot.pick("security_group_id", this.state.directoryservice)} clipboard={true} type={"ec2:security-group-id"} />
                                                                <KeyValue title="Base OS" value={Utils.getOsTitle(dot.pick("base_os", this.state.directoryservice))} />
                                                                <KeyValue title="CloudWatch Logs Enabled" value={<EnabledDisabledStatusIndicator enabled={Utils.asBoolean(dot.pick("cloudwatch_logs.enabled", this.state.directoryservice), false)} />} type={"react-node"} />
                                                                <KeyValue title="Is Public?" value={dot.pick("public", this.state.directoryservice)} type={"boolean"} />
                                                                <KeyValue title="Public IP" value={dot.pick("public_ip", this.state.directoryservice)} />
                                                            </ColumnLayout>
                                                        </Box>
                                                    </SpaceBetween>
                                                </Container>
                                            )}
                                            {isDirectoryServiceActiveDirectory() && (
                                                <Container header={<Header variant={"h2"}>Microsoft AD Settings</Header>}>
                                                    <ColumnLayout variant={"text-grid"} columns={2}>
                                                        <KeyValue title="Directory Id" value={dot.pick("directory_id", this.state.directoryservice)} />
                                                        <KeyValue title="Short Name (NETBIOS)" value={dot.pick("ad_short_name", this.state.directoryservice)} />
                                                        <KeyValue title="Edition" value={dot.pick("ad_edition", this.state.directoryservice)} />
                                                        <KeyValue title="Domain Name" value={dot.pick("name", this.state.directoryservice)} clipboard={true} />
                                                        <KeyValue title="Password Max Age" value={dot.pick("password_max_age", this.state.directoryservice)} suffix={"days"} />
                                                        <KeyValue title="AD Automation SQS Queue Url" value={dot.pick("ad_automation.sqs_queue_url", this.state.directoryservice)} clipboard={true} />
                                                        <KeyValue title="AD Automation DynamoDB Table Name" value={`${AppContext.get().getClusterName()}.ad-automation`} clipboard={true} />
                                                    </ColumnLayout>
                                                </Container>
                                            )}
                                        </SpaceBetween>
                                    ),
                                },
                                {
                                    label: "CloudWatch Logs",
                                    id: "cloudwatch-logs",
                                    content: (
                                        <Container header={<Header variant={"h2"}>CloudWatch Logs</Header>}>
                                            <ColumnLayout variant={"text-grid"} columns={3}>
                                                <KeyValue title="Status" value={<EnabledDisabledStatusIndicator enabled={Utils.asBoolean(dot.pick("cloudwatch_logs.enabled", this.state.cluster), false)} />} type={"react-node"} />
                                                <KeyValue title="Force Flush Interval" value={dot.pick("cloudwatch_logs.force_flush_interval", this.state.cluster)} suffix={"seconds"} />
                                                <KeyValue title="Log Retention" value={dot.pick("cloudwatch_logs.retention_in_days", this.state.cluster)} suffix={"days"} />
                                            </ColumnLayout>
                                        </Container>
                                    ),
                                },
                                {
                                    label: "SES",
                                    id: "ses",
                                    content: (
                                        <Container header={<Header variant={"h2"}>Simple Email Service (SES)</Header>}>
                                            <ColumnLayout variant={"text-grid"} columns={3}>
                                                <KeyValue title="Status" value={<EnabledDisabledStatusIndicator enabled={Utils.asBoolean(dot.pick("ses.enabled", this.state.cluster), false)} />} type={"react-node"} />
                                                <KeyValue title="AWS Account ID" value={dot.pick("ses.account_id", this.state.cluster)} clipboard={true} />
                                                <KeyValue title="AWS Region" value={dot.pick("ses.region", this.state.cluster)} />
                                                <KeyValue title="Sender Email" value={dot.pick("ses.sender_email", this.state.cluster)} clipboard={true} />
                                                <KeyValue title="Max Sending Rate" value={dot.pick("ses.max_sending_rate", this.state.cluster)} suffix={" / second"} />
                                            </ColumnLayout>
                                        </Container>
                                    ),
                                },
                                {
                                    label: "EC2",
                                    id: "ec2",
                                    content: (
                                        <Container header={<Header variant={"h2"}>EC2</Header>}>
                                            <ColumnLayout variant={"text-grid"} columns={1}>
                                                <KeyValue title="SSH Key Pair" value={dot.pick("network.ssh_key_pair", this.state.cluster)} clipboard={true} />
                                                <KeyValue title="Custom EC2 Managed Policy ARNs" value={dot.pick("iam.ec2_managed_policy_arns", this.state.cluster)} clipboard={true} />
                                            </ColumnLayout>
                                        </Container>
                                    ),
                                },
                                {
                                    label: "Backup",
                                    id: "backups",
                                    content: (
                                        <SpaceBetween size={"l"}>
                                            <Container header={<Header variant={"h2"}>AWS Backup</Header>}>
                                                <ColumnLayout variant={"text-grid"} columns={2}>
                                                    <KeyValue title="Status" value={<EnabledDisabledStatusIndicator enabled={isBackupEnabled()} />} type={"react-node"} />
                                                </ColumnLayout>
                                            </Container>
                                            {isBackupEnabled() && (
                                                <Container header={<Header variant={"h2"}>Backup Vault</Header>}>
                                                    <ColumnLayout variant={"text-grid"} columns={2}>
                                                        <KeyValue title="ARN" value={dot.pick("backups.backup_vault.arn", this.state.cluster)} clipboard={true} />
                                                        <KeyValue title="KMS Key Id (CMK)" value={dot.pick("backups.backup_vault.kms_key_id", this.state.cluster)} clipboard={true} />
                                                    </ColumnLayout>
                                                </Container>
                                            )}
                                            {isBackupEnabled() && (
                                                <Container header={<Header variant={"h2"}>Backup Plan</Header>}>
                                                    <ColumnLayout variant={"text-grid"} columns={2}>
                                                        <KeyValue title="ARN" value={dot.pick("backups.backup_plan.arn", this.state.cluster)} clipboard={true} />
                                                        <KeyValue title="Selection" value={dot.pick("backups.backup_plan.selection.tags", this.state.cluster)} />
                                                    </ColumnLayout>
                                                </Container>
                                            )}
                                        </SpaceBetween>
                                    ),
                                },
                                {
                                    label: "Route 53",
                                    id: "route-53",
                                    content: (
                                        <SpaceBetween size={"l"}>
                                            <Container header={<Header variant={"h2"}>Private Hosted Zone</Header>}>
                                                <ColumnLayout variant={"text-grid"} columns={2}>
                                                    <KeyValue title="Hosted Zone Name" value={dot.pick("route53.private_hosted_zone_name", this.state.cluster)} clipboard={true} />
                                                    <KeyValue title="Hosted Zone ID" value={dot.pick("route53.private_hosted_zone_id", this.state.cluster)} clipboard={true} />
                                                    <KeyValue title="Hosted Zone ARN" value={dot.pick("route53.private_hosted_zone_arn", this.state.cluster)} clipboard={true} />
                                                </ColumnLayout>
                                            </Container>
                                        </SpaceBetween>
                                    ),
                                },
                                {
                                    label: "AWS Account",
                                    id: "aws-account",
                                    content: (
                                        <Container header={<Header variant={"h2"}>AWS Account Settings</Header>}>
                                            <ColumnLayout variant={"text-grid"} columns={3}>
                                                <KeyValue title="AWS Account ID" value={dot.pick("aws.account_id", this.state.cluster)} clipboard={true} />
                                                <KeyValue title="AWS Region" value={dot.pick("aws.region", this.state.cluster)} clipboard={true} />
                                                <KeyValue title="AWS Partition" value={dot.pick("aws.partition", this.state.cluster)} />
                                                <KeyValue title="AWS DNS Suffix" value={dot.pick("aws.dns_suffix", this.state.cluster)} />
                                            </ColumnLayout>
                                        </Container>
                                    ),
                                },
                            ]}
                        />
                    </SpaceBetween>
                }
            />
        );
    }
}

export default withRouter(ClusterSettings);
