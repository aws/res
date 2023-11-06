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

import Utils from "./utils";
import dot from "dot-object";

class ConfigUtils {
    static getInternalAlbDnsName(clusterSettings: any) {
        return dot.pick("load_balancers.internal_alb.load_balancer_dns_name", clusterSettings);
    }

    static getInternalAlbCustomDnsName(clusterSettings: any) {
        let customDnsName = dot.pick("load_balancers.internal_alb.certificates.custom_dns_name", clusterSettings);
        if (Utils.isEmpty(customDnsName)) {
            customDnsName = dot.pick("load_balancers.internal_alb.custom_dns_name", clusterSettings);
        }
        return customDnsName;
    }

    static getInternalAlbUrl(clusterSettings: any) {
        let dnsName = this.getInternalAlbCustomDnsName(clusterSettings);
        if (Utils.isEmpty(dnsName)) {
            dnsName = this.getInternalAlbDnsName(clusterSettings);
        }
        return `https://${Utils.asString(dnsName)}`;
    }

    static getInternalAlbArn(clusterSettings: any) {
        return dot.pick("load_balancers.internal_alb.load_balancer_arn", clusterSettings);
    }

    static getInternalAlbCertificateSecretArn(clusterSettings: any) {
        let secretArn = dot.pick("load_balancers.internal_alb.certificates.certificate_secret_arn", clusterSettings);
        if (Utils.isEmpty(secretArn)) {
            secretArn = dot.pick("load_balancers.internal_alb.certificate_secret_arn", clusterSettings);
        }
        return secretArn;
    }

    static getInternalAlbPrivateKeySecretArn(clusterSettings: any) {
        let secretArn = dot.pick("load_balancers.internal_alb.certificates.private_key_secret_arn", clusterSettings);
        if (Utils.isEmpty(secretArn)) {
            secretArn = dot.pick("load_balancers.internal_alb.private_key_secret_arn", clusterSettings);
        }
        return secretArn;
    }

    static getInternalAlbAcmCertificateArn(clusterSettings: any) {
        let certificateArn = dot.pick("load_balancers.internal_alb.certificates.acm_certificate_arn", clusterSettings);
        if (Utils.isEmpty(certificateArn)) {
            certificateArn = dot.pick("load_balancers.internal_alb.acm_certificate_arn", clusterSettings);
        }
        return certificateArn;
    }

    static getExternalAlbDnsName(clusterSettings: any) {
        return dot.pick("load_balancers.external_alb.load_balancer_dns_name", clusterSettings);
    }

    static getExternalAlbCustomDnsName(clusterSettings: any) {
        let customDnsName = dot.pick("load_balancers.external_alb.certificates.custom_dns_name", clusterSettings);
        if (Utils.isEmpty(customDnsName)) {
            customDnsName = dot.pick("load_balancers.external_alb.custom_dns_name", clusterSettings);
        }
        return customDnsName;
    }

    static getExternalAlbUrl(clusterSettings: any) {
        let dnsName = this.getExternalAlbCustomDnsName(clusterSettings);
        if (Utils.isEmpty(dnsName)) {
            dnsName = this.getExternalAlbDnsName(clusterSettings);
        }
        return `https://${dnsName}`;
    }

    static getExternalAlbArn(clusterSettings: any) {
        return dot.pick("load_balancers.external_alb.load_balancer_arn", clusterSettings);
    }

    static isExternalAlbPublic(clusterSettings: any): boolean {
        return Utils.asBoolean(dot.pick("load_balancers.external_alb.public", clusterSettings));
    }

    static getExternalAlbCertificateSecretArn(clusterSettings: any) {
        let secretArn = dot.pick("load_balancers.external_alb.certificates.certificate_secret_arn", clusterSettings);
        if (Utils.isEmpty(secretArn)) {
            secretArn = dot.pick("load_balancers.external_alb.certificate_secret_arn", clusterSettings);
        }
        return secretArn;
    }

    static getExternalAlbPrivateKeySecretArn(clusterSettings: any) {
        let secretArn = dot.pick("load_balancers.external_alb.certificates.private_key_secret_arn", clusterSettings);
        if (Utils.isEmpty(secretArn)) {
            secretArn = dot.pick("load_balancers.external_alb.private_key_secret_arn", clusterSettings);
        }
        return secretArn;
    }

    static getExternalAlbAcmCertificateArn(clusterSettings: any) {
        let certificateArn = dot.pick("load_balancers.external_alb.certificates.acm_certificate_arn", clusterSettings);
        if (Utils.isEmpty(certificateArn)) {
            certificateArn = dot.pick("load_balancers.external_alb.acm_certificate_arn", clusterSettings);
        }
        return certificateArn;
    }
}

export default ConfigUtils;
