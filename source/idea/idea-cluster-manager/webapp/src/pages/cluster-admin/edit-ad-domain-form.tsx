import { useEffect, useState } from 'react';
import { AppContext } from "../../common";
import { UpdateModuleSettingsDirectoryService } from '../../client/data-model';
import { OnFlashbarChangeEvent } from '../../App';
import { Modal, Header, Box, SpaceBetween, Button, Form, ColumnLayout, FormField, Input, Checkbox, ExpandableSection } from '@cloudscape-design/components';

interface EditADDomainFormProps {
    onFlashbarChange: (event: OnFlashbarChangeEvent) => void;
    updateDirectoryServiceState: (editFormData: UpdateModuleSettingsDirectoryService) => void;
}

const OPTIONAL_LABELS = [
    "LDAP Filters",
    "Domain TLS Certificate Secret ARN",
]

const OPTIONAL_FIELDS = [
    "users_filter",
    "groups_filter",
    "tls_certificate_secret_arn",
]

const FIELD_VALIDATION_PATTERNS = {
    "name": "^$|(?=^.{4,253}$)(^((?!-)[a-zA-Z0-9-]{1,63}(?<!-)\.)+[a-zA-Z]{2,63}$)",
    "ad_short_name": ".+",
    "root_user_dn": ".+",
    "users.ou": ".+",
    "ldap_base": ".+",
    "ldap_connection_uri": ".+",
    "service_account_credentials_secret_arn": "^(?:arn:(?:aws|aws-us-gov|aws-cn):secretsmanager:[a-z0-9-]+:[0-9]{12}:secret:[A-Za-z0-9\\-\\_\\+\\=\\/\\.\\@]{1,519})?$",
    "sudoers.group_name": ".+",
    "computers.ou": ".+",
    "groups.ou": ".+",
    "tls_certificate_secret_arn": "^(?:arn:(?:aws|aws-us-gov|aws-cn):secretsmanager:[a-z0-9-]+:[0-9]{12}:secret:[A-Za-z0-9\\-\\_\\+\\=\\/\\.\\@]{1,519})?$",
}

export const EditADDomainForm = (props: EditADDomainFormProps) => {
    const [visible, setVisible] = useState(false);
    const [formData, setFormData] = useState<UpdateModuleSettingsDirectoryService>(initializeFormData({}));
    // When component mounts - prepopulate form with existing directoryservice module settings data
    useEffect(() => {
        const fetchExistingAdDomainData = async () => {
            const adDomain = await AppContext.get().client().clusterSettings().getModuleSettings({module_id: "directoryservice"});
            setFormData(initializeFormData(adDomain.settings));
        }
        fetchExistingAdDomainData();
    }, []);
    const updateFormData = (key: string, value: string) => {
        setKeyValueOnObj(formData, key, value);
        setFormData({...formData});
    }
    // record error strings in object structure matching formData to simplify validation updates
    const [formFieldValidationErrors, setFormFieldValidationErrors] = useState<UpdateModuleSettingsDirectoryService>({
        ...formData, 
        users: {...formData.users}, 
        sudoers: {...formData.sudoers}, 
        sssd: {...formData.sssd}, 
        computers: {...formData.computers}, 
        groups: {...formData.groups}
    });
    const updateFormFieldValidationError = (key: string, value: string) => {
        setKeyValueOnObj(formFieldValidationErrors, key, value);
        setFormFieldValidationErrors({...formFieldValidationErrors});
    }
    const [formError, setFormError] = useState("");
    const hideForm = () => visible ? setVisible(false) : null;
    const showForm = () => visible ? null : setVisible(true);
    const clusterSettingsClient = AppContext.get().client().clusterSettings();
    const onFormSubmit = async () => {
        setFormFieldValidationErrors({...formFieldValidationErrors, name: "Test"});
        if (!validateFormFields(formData, updateFormFieldValidationError)) {
            setFormError("Please fill out all required fields.");
            return;
        }
        try {
            await clusterSettingsClient.updateModuleSettings({
                module_id: "directoryservice",
                settings: formData
            });

            props.onFlashbarChange({
                items: [
                    {
                        type: "success",
                        content: "Active Directory successfully modified.",
                        dismissible: true,
                    },
                ],
            });

            props.updateDirectoryServiceState(formData);
            setFormError("");
            hideForm();
        } catch (e: any) {
            setFormError(e.message);
            console.error(e);
        }
    }
    return (
        <Button iconName="edit" variant="link" onClick={showForm}>
            <Modal
                onDismiss={hideForm}
                visible={visible}
                header={<Header variant="h3">Active Directory Synchronization</Header>}
                footer={
                    <Box float="right">
                        <SpaceBetween direction="horizontal" size="xs">
                            <Button variant="link" onClick={hideForm}>Cancel</Button>
                            <Button variant="primary" onClick={onFormSubmit}>Submit</Button>
                        </SpaceBetween>
                    </Box>
                }
            >
                <form onSubmit={(e) => e.preventDefault()}>
                    <Form
                        errorText={formError}
                    >
                        <SpaceBetween size="l" direction="vertical">
                            <ColumnLayout columns={1}>
                                <FormField
                                    label={createFormLabel("Active Directory Name")}
                                    description="Type the name for the Active Directory. It does not need to match the portal domain name."
                                    errorText={formFieldValidationErrors.name}
                                >
                                    <Input
                                        value={formData.name}
                                        placeholder="corp.res.com"
                                        onChange={(e) => handleFormInputChange(updateFormData, updateFormFieldValidationError, "name", e.detail.value)}
                                    />
                                </FormField>
                                <FormField
                                    label={createFormLabel("Short Name (NETBIOS)")}
                                    description="Provide the short name for the Active Directory. This is also called the netBIOS name."
                                    errorText={formFieldValidationErrors.ad_short_name}
                                >
                                    <Input
                                        value={formData.ad_short_name}
                                        placeholder="CORP"
                                        onChange={(e) => handleFormInputChange(updateFormData, updateFormFieldValidationError, "ad_short_name", e.detail.value)}
                                    />
                                </FormField>
                                <FormField
                                    label={createFormLabel("Service Account User DN")}
                                    description="Provide the distinguished name (DN) of the service account user in Directory."
                                    errorText={formFieldValidationErrors.root_user_dn}
                                >
                                    <Input
                                        value={formData.root_user_dn}
                                        placeholder='CN=ServiceAccount,OU=Users,OU=CORP,DC=corp,DC=res,DC=com'
                                        onChange={(e) => handleFormInputChange(updateFormData, updateFormFieldValidationError, "root_user_dn", e.detail.value)}
                                    />
                                </FormField>
                                <FormField
                                    label={createFormLabel("Service Account Credentials Secret ARN")}
                                    description="Provide a Secret ARN which contains the username and password for the Active Directory ServiceAccount user, formatted as a username:password key/value pair."
                                    errorText={formFieldValidationErrors.service_account_credentials_secret_arn}
                                    constraintText="The secret should contain the username and password in the format username:password."
                                >
                                    <Input
                                        value={formData.service_account_credentials_secret_arn}
                                        onChange={(e) => handleFormInputChange(updateFormData, updateFormFieldValidationError, "service_account_credentials_secret_arn", e.detail.value)}
                                        placeholder='arn:aws:secretsmanager:us-west-2:123456789012:secret:my-secret-123456'
                                    />
                                </FormField>
                                <FormField
                                    label={createFormLabel("LDAP Connection URI")}
                                    description="Specify the connection URI for the Active Directory server."
                                    errorText={formFieldValidationErrors.ldap_connection_uri}
                                >
                                    <Input
                                        value={formData.ldap_connection_uri}
                                        placeholder="ldap://corp.res.com"
                                        onChange={(e) => handleFormInputChange(updateFormData, updateFormFieldValidationError, "ldap_connection_uri", e.detail.value)}
                                    />
                                </FormField>
                                <FormField
                                    label={createFormLabel("LDAP Base")}
                                    description="Specify the LDAP path within the directory hierarchy."
                                    errorText={formFieldValidationErrors.ldap_base}
                                >
                                    <Input
                                        value={formData.ldap_base}
                                        placeholder="dc=corp,dc=res,dc=com"
                                        onChange={(e) => handleFormInputChange(updateFormData, updateFormFieldValidationError, "ldap_base", e.detail.value)}
                                    />
                                </FormField>
                                <Checkbox
                                        checked={formData.disable_ad_join === "True"}
                                        onChange={(e) => handleFormInputChange(updateFormData, updateFormFieldValidationError, "disable_ad_join", e.detail.checked ? "True" : "False")}
                                >
                                    <FormField
                                        label="Disable Active Directory Join"
                                        description="To prevent Linux hosts from joining the directory domain, check the box. Otherwise, leave in the default setting of unchecked."
                                    />
                                </Checkbox>
                                <Checkbox
                                    checked={formData.sssd.ldap_id_mapping === "True"}
                                    onChange={(e) => handleFormInputChange(updateFormData, updateFormFieldValidationError, "sssd.ldap_id_mapping", e.detail.checked ? "True" : "False")}
                                >
                                    <FormField
                                        label="Enable LDAP ID Mapping"
                                        description="Determines if UID and GID numbers are generated by SSSD or if the numbers provided by the AD are used. Check to use SSSD generated UID and GID, or uncheck to use UID and GID provided by the AD. For most cases this parameter should be checked."
                                    />
                                </Checkbox>
                                <FormField
                                    label={createFormLabel("Organizational Units (OU)")}
                                    description="Provide the Organizational Unit within AD that will sync."
                                >
                                    <Box padding="l">
                                        <ColumnLayout columns={1}>
                                            <FormField
                                                label={createFormLabel("Users OU")}
                                                errorText={formFieldValidationErrors.users.ou}
                                            >
                                                <Input
                                                    value={formData.users.ou}
                                                    placeholder="OU=Users,OU=RES,OU=CORP,DC=corp,DC=res,DC=com"
                                                    onChange={(e) => handleFormInputChange(updateFormData, updateFormFieldValidationError, "users.ou", e.detail.value)}
                                                />
                                            </FormField>
                                            <FormField
                                                label={createFormLabel("Groups OU")}
                                                errorText={formFieldValidationErrors.groups.ou}
                                            >
                                                <Input
                                                    value={formData.groups.ou}
                                                    placeholder="OU=Groups,OU=RES,OU=CORP,DC=corp,DC=res,DC=com"
                                                    onChange={(e) => handleFormInputChange(updateFormData, updateFormFieldValidationError, "groups.ou", e.detail.value)}
                                                />
                                            </FormField>
                                            <FormField
                                                label={createFormLabel("Computers OU")}
                                                errorText={formFieldValidationErrors.computers.ou}
                                            >
                                                <Input
                                                    value = {formData.computers.ou} 
                                                    placeholder="OU=Computers,OU=RES,OU=CORP,DC=corp,DC=res,DC=com" 
                                                    onChange={(e) => handleFormInputChange(updateFormData, updateFormFieldValidationError, "computers.ou", e.detail.value)}
                                                />
                                            </FormField>
                                        </ColumnLayout>
                                    </Box>
                                </FormField>
                                <FormField
                                    label={createFormLabel("Sudoers Group Name")}
                                    description="Provide the group name that contains all users with sudoer access on instances at install and administrator access on RES."
                                    errorText={formFieldValidationErrors.sudoers.group_name}
                                >
                                    <Input
                                        value={formData.sudoers.group_name}
                                        placeholder="RESAdministrators"
                                        onChange={(e) => handleFormInputChange(updateFormData, updateFormFieldValidationError, "sudoers.group_name", e.detail.value)}
                                    />
                                </FormField>
                                <ExpandableSection
                                    headerText="Additional Settings"
                                >
                                    <FormField
                                        label={createFormLabel("LDAP Filters")}
                                        description="Provide the preferred LDAP filters."
                                    >
                                        <Box padding="l">
                                            <ColumnLayout columns={1}>
                                                <FormField
                                                    label={createFormLabel("Users Filter")}
                                                    errorText={formFieldValidationErrors.users_filter}
                                                >
                                                    <Input
                                                        value={formData.users_filter ?? ""}
                                                        placeholder="(objectClass=user)"
                                                        onChange={(e) => handleFormInputChange(updateFormData, updateFormFieldValidationError, "users_filter", e.detail.value)}
                                                    />
                                                </FormField>
                                                <FormField
                                                    label={createFormLabel("Groups Filter")}
                                                    errorText={formFieldValidationErrors.groups_filter}
                                                >
                                                    <Input
                                                        value={formData.groups_filter ?? ""}
                                                        placeholder="(objectClass=group)"
                                                        onChange={(e) => handleFormInputChange(updateFormData, updateFormFieldValidationError, "groups_filter", e.detail.value)}
                                                    />
                                                </FormField>
                                            </ColumnLayout>
                                        </Box>
                                    </FormField>              
                                    <FormField
                                        label={createFormLabel("Domain TLS Certificate Secret ARN")}
                                        description="Provide the ARN for the domain TLS certificate secret."
                                        errorText={formFieldValidationErrors.tls_certificate_secret_arn}
                                    >
                                        <Input
                                            value={formData.tls_certificate_secret_arn ?? ""}
                                            onChange={(e) => handleFormInputChange(updateFormData, updateFormFieldValidationError, "tls_certificate_secret_arn", e.detail.value)}
                                        />
                                    </FormField>
                                </ExpandableSection>
                            </ColumnLayout>
                        </SpaceBetween>
                    </Form>
                </form>
            </Modal>
        </Button>
    )
}

const createFormLabel = (label: string) => {
    if (OPTIONAL_LABELS.includes(label)) {
        return (
            <span>
                {label} <i>- optional</i>{""}
            </span>
        )
    } else {
        return label;
    }
}

// Helper function to handle setting nested object values
const setKeyValueOnObj = (obj: any, key: string, value: string) => {
    if (key.includes(".")) {
        const keys = key.split(".");
        const firstKey = keys[0];
        const remainingKeys = keys.slice(1).join(".");
        if (!obj[firstKey]) {
            obj[firstKey] = {};
        }
        obj = setKeyValueOnObj(obj[firstKey], remainingKeys, value);
    } else {
        obj[key] = value;
        return obj;
    }
}

const handleFormInputChange = (updateFormData: any, updateFormFieldValidationError: any, key: string, value: string) => {
     try {
        validateFormInput(key, value);
        updateFormFieldValidationError(key, "");
     } catch (e: any) {
        updateFormFieldValidationError(key, e.message);
     }
    updateFormData(key, value);
}

const validateFormInput = (key: string, value: string) => {
    if (!OPTIONAL_FIELDS.includes(key) && !value) {
        throw new Error("This field is required.");
    }
    if (key in FIELD_VALIDATION_PATTERNS) {
        const pattern = new RegExp(FIELD_VALIDATION_PATTERNS[key as keyof typeof FIELD_VALIDATION_PATTERNS]);
        if (!pattern.test(value)) {
            throw new Error("Invalid input. Field does not match the required pattern: " + FIELD_VALIDATION_PATTERNS[key as keyof typeof FIELD_VALIDATION_PATTERNS]);
        }
    }
}

const validateFormFields = (formData: any, updateFormFieldValidationError: any) => {
    let validated = true;
    const stack = [{formData, prevKey: ""}];
    while (stack?.length > 0) {
      const currentObj = stack.pop();
      if (currentObj === null || typeof currentObj !== 'object') {
        return;
      }
      Object.keys(currentObj.formData).forEach(key => {
        const fullPathKey = currentObj.prevKey ? `${currentObj.prevKey}.${key}` : key;
        if (!OPTIONAL_FIELDS.includes(fullPathKey)) {
            const formValue = currentObj.formData[key];
            // Continue to iterate through nested objects else validate the field
            if (formValue !== null && typeof formValue === 'object') {
                stack.push({formData: formValue, prevKey: fullPathKey});
            } else {
                // Validate the field value
                try {
                    validateFormInput(fullPathKey, formValue);
                    updateFormFieldValidationError(fullPathKey, "");
                } catch (e: any) {
                    validated = false;
                    updateFormFieldValidationError(fullPathKey, e.message);
                }
            }
        }
      });
    }
    return validated;
  };

  const initializeFormData = (formData: any): UpdateModuleSettingsDirectoryService => {
    return {
        root_user_dn: formData.root_user_dn ?? "",
        users: {
            ou: formData.users ? formData.users.ou : "",
        },
        disable_ad_join: formData.disable_ad_join ?? "False",
        ad_short_name: formData.ad_short_name ?? "",
        ldap_base: formData.ldap_base ?? "",
        ldap_connection_uri: formData.ldap_connection_uri ?? "",
        service_account_credentials_secret_arn: formData.service_account_credentials_secret_arn ?? "",
        users_filter: formData.users_filter ?? "",
        groups_filter: formData.groups_filter ?? "",
        sudoers: {
            group_name: formData.sudoers ? formData.sudoers.group_name : "",
        },
        sssd: {
            ldap_id_mapping: formData.sssd ? formData.sssd.ldap_id_mapping : "True",
        },
        computers: {
            ou: formData.computers ? formData.computers.ou : "",
        },
        groups: {
            ou: formData.groups ? formData.groups.ou : "",
        },
        name: formData.name ?? "",
    }
  }