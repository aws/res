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

import { RefObject } from 'react';
import IdeaForm from '../../components/form';
import { AppContext } from '../../common';
import { OnFlashbarChangeEvent } from '../../App';

interface EnableSSOConfigFormProps {
    enableSSOConfigForm: RefObject<IdeaForm>;
    onFlashbarChange: (event: OnFlashbarChangeEvent) => void;
    updateIdentityProviderState: (ssoEnabled: boolean) => void;
}

export const EnableSSOConfigForm = (props: EnableSSOConfigFormProps) => {
    return (
        <IdeaForm
            ref={props.enableSSOConfigForm}
            name="enable-sso-config-form"
            title="Single Sign On Configuration"
            modal={true}
            modalSize="medium"
            onSubmit={async () => {
                if (!props.enableSSOConfigForm.current?.validate()) {
                    return false;
                }

                try {
                    const values: any = props.enableSSOConfigForm.current?.getValues();
                    await AppContext.get().client().auth().configureSSO(values);
                    
                    props.onFlashbarChange({
                        items: [
                            {
                                type: "success",
                                content: "Single sign on successfully enabled.",
                                dismissible: true,
                            },
                        ],
                    });

                    props.updateIdentityProviderState(true);
                    props.enableSSOConfigForm.current?.hideModal();
                    return true;
                } catch (error: any) {
                    props.enableSSOConfigForm.current?.setError(error.errorCode, error.message);
                    return false;
                }
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
    )
}


export default EnableSSOConfigForm;
