import { useEffect, useState } from 'react';
import { AppContext } from "../../common";
import { UpdateModuleSettingsDirectoryService } from '../../client/data-model';
import { OnFlashbarChangeEvent } from '../../App';
import { Modal, Header, Box, SpaceBetween, Button, Form, ColumnLayout, FormField, Input, ExpandableSection, AttributeEditor, Select, Toggle } from '@cloudscape-design/components';

interface EditADDomainFormProps {
    onFlashbarChange: (event: OnFlashbarChangeEvent) => void;
    updateDirectoryServiceState: (editFormData: UpdateModuleSettingsDirectoryService) => void;
}

const OPTIONAL_LABELS = [
    "LDAP Filters",
    "Domain TLS Certificate Secret ARN",
    "Additional SSSD Configuration",
]

const OPTIONAL_FIELDS = [
    "users_filter",
    "groups_filter",
    "tls_certificate_secret_arn",
    "sssd.additional_sssd_configs",
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

const DEFAULT_BOOLEAN_CONFIG = "ldap_id_mapping"

export const EditADDomainForm = (props: EditADDomainFormProps) => {
    const [visible, setVisible] = useState(false);
    const [additionalConfigs, setAdditionalConfigs] = useState<any[]>([])
    const [formData, setFormData] = useState<UpdateModuleSettingsDirectoryService>(initializeFormData({}));
    // When component mounts - prepopulate form with existing directoryservice module settings data
    useEffect(() => {
        const fetchExistingAdDomainData = async () => {
            AppContext.get().client().clusterSettings().getModuleSettings({module_id: "directoryservice"})
            .then((adDomain) => {
                const initialFormData = initializeFormData(adDomain.settings);
                setFormData(initialFormData);
                const disableADJoin = initialFormData.disable_ad_join;
                const ladpIdMapping = initialFormData.sssd.ldap_id_mapping;
                const additionConfigsDict = initialFormData.sssd.additional_sssd_configs
                    ? JSON.parse(initialFormData.sssd.additional_sssd_configs)
                    : {};
                initializeAdditionalConfigs(additionConfigsDict, disableADJoin, ladpIdMapping);
            })
        }
        const initializeAdditionalConfigs = (additionalConfigsDict: any, disableADJoin: string, ladpIdMapping: string) => {
            const configsKeys = Object.keys(additionalConfigsDict);
            let additionalConfigsList = Object.entries(additionalConfigsDict).map(([key, value]) => ({ key: key, value: value }))
            // Add ldap_id_mapping if not in additional_sssd_configs
            if (!configsKeys.includes("ldap_id_mapping")) {
                additionalConfigsList = [{ key: "ldap_id_mapping", value: ladpIdMapping }, ...additionalConfigsList];
            }
            setAdditionalConfigs(additionalConfigsList)
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
    const [additionalConfigsValidationErrors, setAdditionalConfigsValidationErrors] = useState<any[]>([
        ...additionalConfigs
    ]);
    const updateFormFieldValidationError = (key: string, value: string) => {
        setKeyValueOnObj(formFieldValidationErrors, key, value);
        setFormFieldValidationErrors({...formFieldValidationErrors});
    }

    const updateAdditionalConfigsValidationError = (index: number, inputKey: string, value: string) => {
        const currentError = {...additionalConfigsValidationErrors[index], [inputKey]: value}
        additionalConfigsValidationErrors[index] = currentError;
        setAdditionalConfigsValidationErrors([...additionalConfigsValidationErrors]);
    }
    const [formError, setFormError] = useState("");
    const hideForm = () => visible ? setVisible(false) : null;
    const showForm = () => visible ? null : setVisible(true);
    const clusterSettingsClient = AppContext.get().client().clusterSettings();
    const onFormSubmit = async () => {
        setFormFieldValidationErrors({...formFieldValidationErrors, name: "Test"});
        setAdditionalConfigsValidationErrors([...additionalConfigsValidationErrors]);
        if (!validateFormFields(formData, updateFormFieldValidationError)) {
            setFormError("Please fill out all required fields.");
            return;
        }
        if (!validateAdditionalConfigsInputs(additionalConfigs, updateAdditionalConfigsValidationError)) {
            setFormError("Additional parameter cannot be empty and parameter key must be unique.");
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

    const buildAdditionalConfigSection = () => {
        return (
            <Box padding="l">
                <AttributeEditor
                    key="AdditionalConfigsAttributeEditor"
                    onAddButtonClick={() => {
                        const newConfigs = [...additionalConfigs, { key: "", value: "" }];
                        handleAdditionalConfigsChange(setAdditionalConfigs, updateFormData, updateAdditionalConfigsValidationError, newConfigs, newConfigs.length-1)
                    }}
                    onRemoveButtonClick={({detail: { itemIndex }}) => {
                        const newConfigs = [...additionalConfigs];
                        newConfigs.splice(itemIndex, 1);
                        handleAdditionalConfigsChange(setAdditionalConfigs, updateFormData, updateAdditionalConfigsValidationError, newConfigs, itemIndex)
                    }}
                    items={additionalConfigs}
                    addButtonText="Add Parameter"
                    removeButtonText="Remove"
                    empty="No additional configuration attached. Click 'Add Parameter' below to get started."
                    definition={[
                        {
                            label: "Key",
                            control: (item, itemIndex) => (
                                <Input
                                    value={item.key}
                                    disabled={item.key === DEFAULT_BOOLEAN_CONFIG}
                                    onChange={({ detail }) => {
                                        const newConfigs = [...additionalConfigs];
                                        newConfigs[itemIndex].key = detail.value;
                                        handleAdditionalConfigsChange(setAdditionalConfigs, updateFormData, updateAdditionalConfigsValidationError, newConfigs, itemIndex, "key")
                                    }}
                                />
                            ),
                            errorText: (item, itemIndex) => (
                                additionalConfigsValidationErrors[itemIndex]?.key ?? undefined
                            )
                        },
                        {
                            label: "Value",
                            control: (item, itemIndex) => (
                                item.key === DEFAULT_BOOLEAN_CONFIG
                                ? (
                                    <Select
                                        options={[
                                            { value: "true"},
                                            { value: "false"}
                                        ]}
                                        selectedOption={{value: item.value}}
                                        onChange={({ detail }) => {
                                            const newConfigs = [...additionalConfigs];
                                            newConfigs[itemIndex].value = detail.selectedOption.value;
                                            handleAdditionalConfigsChange(setAdditionalConfigs, updateFormData, updateAdditionalConfigsValidationError, newConfigs, itemIndex, "value")
                                        }}
                                    />
                                ) :
                                <Input
                                    value={item.value}
                                    onChange={({ detail }) => {
                                        const newConfigs = [...additionalConfigs];
                                        newConfigs[itemIndex].value = detail.value;
                                        handleAdditionalConfigsChange(setAdditionalConfigs, updateFormData, updateAdditionalConfigsValidationError, newConfigs, itemIndex, "value")
                                    }}
                                />
                            ),
                            errorText: (item, itemIndex) => (
                                additionalConfigsValidationErrors[itemIndex]?.value ?? undefined
                            )
                        }
                    ]}
                    isItemRemovable={item =>
                        item.key === DEFAULT_BOOLEAN_CONFIG ? false : true
                      }
                    />
            </Box>
        )
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
                                <Toggle
                                    checked={formData.disable_ad_join === "false"}
                                    onChange={(e) => handleFormInputChange(updateFormData, updateFormFieldValidationError, "disable_ad_join", e.detail.checked ? "false" : "true")}
                                >
                                    <FormField
                                        label="Join Active Directory"
                                        description="Turn on Linux integration with your directory domain."
                                    />
                                </Toggle>
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
                                    <SpaceBetween size="l" direction="vertical">
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
                                        <FormField
                                            label={createFormLabel("Additional SSSD Configuration")}
                                            description="Provide additional SSSD configs for your AD domain."
                                            errorText={formFieldValidationErrors.sssd.additional_sssd_configs}
                                            >
                                            {buildAdditionalConfigSection()}
                                        </FormField>
                                    </SpaceBetween>
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

const handleAdditionalConfigsChange = (setAdditionalConfigs: any, updateFormData: any, updateAdditionalConfigsValidationError: any, additionalConfigs: any[], index: number, inputKey?: string) => {
    if (inputKey) {
        updateAdditionalConfigsValidationError(index, inputKey, "");
    }
    setAdditionalConfigs(additionalConfigs);
    let configObject: { [key: string]: string } = {};
    additionalConfigs.forEach((config) => {
        if (config.key === DEFAULT_BOOLEAN_CONFIG) {
            updateFormData(`sssd.${config.key}`, config.value)
        } else {
            configObject[config.key] = config.value;
        }
    })
    const configsString = JSON.stringify(configObject);
    updateFormData("sssd.additional_sssd_configs", configsString);
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

  const validateAdditionalConfigsInputs = (additionalConfigs: any[], updateAdditionalConfigsValidationError: any) => {
    const isDuplicateKey = (key: string, currentIndex: number) => {
        return additionalConfigs.some((config, index) =>
            index < currentIndex && config.key === key
        );
    };

    let validated = true;
    additionalConfigs.forEach((config, index) => {
        if (isDuplicateKey(config.key, index) || !config.key) {
            validated = false;
            updateAdditionalConfigsValidationError(index, "key", "Additional Configuration key must be non-empty unique value.");
        }
        if (!config.value) {
            validated = false;
            updateAdditionalConfigsValidationError(index, "value", "Additional Configuration value must be non-empty value.");
        }
    });
    return validated;
  }

  const initializeFormData = (formData: any): UpdateModuleSettingsDirectoryService => {
    return {
        root_user_dn: formData.root_user_dn ?? "",
        users: {
            ou: formData.users ? formData.users.ou : "",
        },
        disable_ad_join: formData.disable_ad_join ?? "false",
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
            ldap_id_mapping: formData.sssd?.ldap_id_mapping ?? "true",
            additional_sssd_configs: formData.sssd? formData.sssd.additional_sssd_configs : "",
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
