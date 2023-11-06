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

"""
IDEA Self-Signed Certificate.

Self-signed certificates are generated for below scenarios:
--------------------------------------------------------------------------------
1. Create a Self-signed certificate for the external ALB
This is executed only during the first installation of the IDEA cluster. If the self-signed certificate already exists in ACM for the
 cluster's default domain name: cluster-name.idea.default, a new certificate will not be created.
It is STRONGLY RECOMMENDED for you to upload your own certificate on ACM and update the Load balancer with your
personal/corporate certificate

2. Create a self-signed certificate for the internal ALB
This certificate is used by IDEA to configure the internal load-balancer using ACM.


Developer Notes:
--------------------------------------------------------------------------------

GetSecretValue does not support IAM condition keys based on Name of the secret. Since secrets are not deleted immediately, and are
scheduled for deletion at a later date, add additional res:SecretName tag is added to individual secrets. This allows for searching
for applicable secrets using the res:SecretName tag and also, individual permissions can be granted based on this tag.
"""
import datetime

from idea_lambda_commons import HttpClient, CfnResponse, CfnResponseStatus
import boto3
import botocore.exceptions
import logging
import json
import time

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.x509.oid import NameOID

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handle_delete(event: dict, context):
    resource_properties = event.get('ResourceProperties', {})
    certificate_name = resource_properties.get('certificate_name')
    domain_name = resource_properties.get('domain_name')

    client = HttpClient()
    try:

        certificate_secret_name = f'{certificate_name}-certificate'
        private_key_secret_name = f'{certificate_name}-private-key'

        secretsmanager_client = boto3.client('secretsmanager')
        list_secrets_result = secretsmanager_client.list_secrets(
            Filters=[
                {
                    'Key': 'tag-key',
                    'Values': ['res:SecretName']
                },
                {
                    'Key': 'tag-value',
                    'Values': [certificate_secret_name, private_key_secret_name]
                }
            ]
        )
        secret_list = list_secrets_result.get('SecretList', [])
        for secret in secret_list:
            secret_arn = secret.get('ARN')
            logger.info(f'deleting secret: {secret_arn} ...')
            secretsmanager_client.delete_secret(
                SecretId=secret_arn,
                ForceDeleteWithoutRecovery=True
            )

        acm_client = boto3.client('acm')
        result = acm_client.list_certificates(CertificateStatuses=['ISSUED'])

        certificate_summary_list = result.get('CertificateSummaryList', [])

        for cert in certificate_summary_list:
            if domain_name == cert.get('DomainName'):
                acm_certificate_arn = cert.get('CertificateArn')
                logger.info(f'deleting acm certificate: {acm_certificate_arn} ...')
                retry_count = 10
                current = 0
                sleep_interval = 5
                while current < retry_count:
                    try:
                        current += 1
                        logger.info(f'deleting certificate - attempt: {current}')
                        acm_client.delete_certificate(
                            CertificateArn=acm_certificate_arn
                        )
                        break
                    except botocore.exceptions.ClientError as e:
                        if e.response['Error']['Code'] == 'ResourceInUseException':
                            logger.warning(f'cannot delete certificate - {e}. wait till the applicable resource releases the certificate.')
                            time.sleep(sleep_interval)
                        else:
                            raise e

        client.send_cfn_response(CfnResponse(
            context=context,
            event=event,
            status=CfnResponseStatus.SUCCESS,
            data={},
            physical_resource_id=certificate_name
        ))
    except Exception as e:
        error_message = f'failed to delete certificate: {certificate_name} - {e}'
        logger.exception(error_message)
        client.send_cfn_response(CfnResponse(
            context=context,
            event=event,
            status=CfnResponseStatus.FAILED,
            data={},
            physical_resource_id=certificate_name,
            reason=error_message
        ))
    finally:
        client.destroy()


def handle_create_or_update(event: dict, context):
    resource_properties = event.get('ResourceProperties', {})
    domain_name = resource_properties.get('domain_name')
    certificate_name = resource_properties.get('certificate_name')
    create_acm_certificate = resource_properties.get('create_acm_certificate', False)
    kms_key_id = resource_properties.get('kms_key_id', None)
    tags = resource_properties.get('tags', {})

    client = HttpClient()

    try:

        common_tags = []
        for key, value in tags.items():
            common_tags.append({
                'Key': key,
                'Value': value
            })

        certificate_secret_name = f'{certificate_name}-certificate'
        private_key_secret_name = f'{certificate_name}-private-key'
        certificate_content = None
        private_key_content = None
        certificate_secret_arn = None
        private_key_secret_arn = None

        secretsmanager_client = boto3.client('secretsmanager')
        list_secrets_result = secretsmanager_client.list_secrets(
            Filters=[
                {
                    'Key': 'tag-key',
                    'Values': ['res:SecretName']
                },
                {
                    'Key': 'tag-value',
                    'Values': [certificate_secret_name, private_key_secret_name]
                }
            ]
        )
        secret_list = list_secrets_result.get('SecretList', [])
        for secret in secret_list:
            name = secret.get('Name')
            arn = secret.get('ARN')
            get_secret_result = secretsmanager_client.get_secret_value(
                SecretId=arn
            )
            secret_string = get_secret_result.get('SecretString')
            if name == certificate_secret_name:
                certificate_content = secret_string
                certificate_secret_arn = arn
                logger.info(f'found: {name}')
            elif name == private_key_secret_name:
                logger.info(f'found: {name}')
                private_key_content = secret_string
                private_key_secret_arn = arn

        if certificate_content is None and private_key_content is None:
            one_day = datetime.timedelta(1, 0, 0)
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend())
            public_key = private_key.public_key()
            subject = x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, 'US'),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, 'California'),
                x509.NameAttribute(NameOID.LOCALITY_NAME, 'Sunnyvale'),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, certificate_name),
                x509.NameAttribute(NameOID.COMMON_NAME, domain_name)
            ])

            certificate = x509.CertificateBuilder() \
                .subject_name(subject) \
                .issuer_name(subject) \
                .not_valid_before(datetime.datetime.today() - one_day) \
                .not_valid_after(datetime.datetime.today() + (one_day * 3650)) \
                .serial_number(x509.random_serial_number()) \
                .public_key(public_key) \
                .add_extension(
                    x509.SubjectAlternativeName([
                        x509.DNSName(domain_name)
                    ]), critical=False) \
                .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)\
                .sign(private_key=private_key, algorithm=hashes.SHA256(), backend=default_backend())

            certificate_content = certificate.public_bytes(serialization.Encoding.PEM).decode("utf-8")
            private_key_content = private_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.TraditionalOpenSSL,
                serialization.NoEncryption()
            ).decode("utf-8")

            # create certificate secret
            certificate_secret_tags = list(common_tags)
            certificate_secret_tags.append({
                'Key': 'res:SecretName',
                'Value': certificate_secret_name
            })
            create_secret_request = {
                'Name': f'{certificate_secret_name}',
                'Description': f'Self-Signed certificate for domain name: {domain_name}',
                'SecretString': certificate_content,
                'Tags': certificate_secret_tags
            }
            if kms_key_id is not None:
                create_secret_request['KmsKeyId'] = kms_key_id
            create_certificate_secret_result = secretsmanager_client.create_secret(**create_secret_request)
            certificate_secret_arn = create_certificate_secret_result.get('ARN')

            # create private key secret
            private_key_secret_tags = list(common_tags)
            private_key_secret_tags.append({
                'Key': 'res:SecretName',
                'Value': private_key_secret_name
            })
            create_secret_request = {
                'Name': f'{private_key_secret_name}',
                'Description': f'Self-Signed certificate private key for domain name: {domain_name}',
                'SecretString': private_key_content,
                'Tags': private_key_secret_tags
            }
            if kms_key_id is not None:
                create_secret_request['KmsKeyId'] = kms_key_id
            create_private_key_secret_result = secretsmanager_client.create_secret(**create_secret_request)
            private_key_secret_arn = create_private_key_secret_result.get('ARN')

        acm_certificate_arn = None
        if create_acm_certificate:
            acm_client = boto3.client('acm')
            result = acm_client.list_certificates(CertificateStatuses=['ISSUED'])

            certificate_summary_list = result.get('CertificateSummaryList', [])

            for cert in certificate_summary_list:
                if domain_name == cert.get('DomainName'):
                    acm_certificate_arn = cert.get('CertificateArn')

            if acm_certificate_arn is None:
                response = acm_client.import_certificate(
                    Certificate=certificate_content,
                    PrivateKey=private_key_content,
                    Tags=common_tags
                )
                acm_certificate_arn = response.get('CertificateArn')

        client.send_cfn_response(CfnResponse(
            context=context,
            event=event,
            status=CfnResponseStatus.SUCCESS,
            data={
                'certificate_secret_arn': certificate_secret_arn,
                'private_key_secret_arn': private_key_secret_arn,
                'acm_certificate_arn': acm_certificate_arn
            },
            physical_resource_id=certificate_name
        ))

    except Exception as e:
        error_message = f'failed to create certificate: {certificate_name} - {e}'
        logger.exception(error_message)
        client.send_cfn_response(CfnResponse(
            context=context,
            event=event,
            status=CfnResponseStatus.FAILED,
            data={},
            physical_resource_id=certificate_name,
            reason=error_message
        ))
    finally:
        client.destroy()


def handler(event: dict, context):
    logger.info(f'ReceivedEvent: {json.dumps(event)}')
    request_type = event.get('RequestType', None)
    if request_type == 'Delete':
        handle_delete(event, context)
    else:
        handle_create_or_update(event, context)
