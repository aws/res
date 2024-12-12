#!/bin/bash -e
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

# set up the OU structure so that there's an OU to put the res users under
echo "Adding Org-level resources"
ldapadd -x -D "cn=Admin,dc=corp,dc=res,dc=com" -w ${admin_password} -f /opt/res-adsync/resources/org.ldif

echo "Adding RES users and groups"
# add our demo users
ldapadd -x -D "cn=Admin,dc=corp,dc=res,dc=com" -w secret -f /opt/res-adsync/resources/res.ldif

export hash_pw=$(slappasswd -s ${service_account_password})

echo "Adding ServiceAccount user."

# Create the service account with the appropriate name
cat /opt/res-adsync/resources/service_account.ldif | username=${service_account_name} hash_pw=${hash_pw} envsubst > /tmp/sa.ldif && ldapadd -x -D 'cn=Admin,dc=corp,dc=res,dc=com' -w secret -f /tmp/sa.ldif

echo "Giving ServiceAccount user suitable permissions to search."

echo "Performing a search test with the ServiceAccount user with a DN."

# perform a search
ldapsearch -x -D "cn=ServiceAccount,dc=corp,dc=res,dc=com" -w ${service_account_password} "(objectClass=user)" -b "ou=users,ou=res,ou=corp,dc=corp,dc=res,dc=com"

echo "Done setting up slap"
