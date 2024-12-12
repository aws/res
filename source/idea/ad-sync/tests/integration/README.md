# Run AD Sync Integration Test
The following steps assume that you run the tests under the package root directory.
## 1. Launch LDAP Server

To create the LDAP server, ensure you have docker installed and run
`source/idea/ad-sync/tests/integration/scripts/run_slapd.sh`. This will start SLAPD in a container and
configure the schema so that it looks like an AD.

Next you will need to be able to interact with an LDAP server at the location
specified by the `cluster-settings.ldap_connection_uri`. This is set to `ldap://corp.res.com` in the integration test
so add the following entry to your `/etc/hosts` file in order to interact with the SLAPD container:
```
127.0.0.1       corp.res.com
```

## 2. Run Integration Tests
you can run the following from the integration test directory:

```
pytest -s source/idea/ad-sync/tests/integration/test_adsync.py
```
