Import-Module -Name ActiveDirectory

$service_account_name = "${ServiceAccount}"
$delegate_permissions_for_ou = "OU=Computers,OU=RES,OU=${OU},DC=${DC}"
$delegate_permissions_to_group = "RES Service Account"
$delegate_permissions_to_group_in_ou = "OU=Users,OU=${OU},DC=${DC}"

echo "Running script to add service account to write computers"

# Enter the Active Directory PowerShell
cd ad:

# Create Group for Managing Computers
try {
     New-ADGroup -Name "$delegate_permissions_to_group" -GroupCategory Security -GroupScope Global -DisplayName "$delegate_permissions_to_group" -Description "Members of this group are service accounts" -Path "$delegate_permissions_to_group_in_ou"
}
catch [Microsoft.ActiveDirectory.Management.ADException]{
    Switch ($_.Exception.Message){
        "already in use" {Write-Host "Group has already been created."}
        default{Write-Host "Unhandled ADException: $_"}
    }
}


try {
    # Add Service Account to Group that will have permission to write computers
    Add-ADGroupMember -Identity "CN=$delegate_permissions_to_group,$delegate_permissions_to_group_in_ou" -Members "$service_account_name"

    # Look up acl for Computers OU
    $computers_ou = Get-ADOrganizationalUnit -Identity "$delegate_permissions_for_ou"
    $acl = get-acl $computers_ou

    # Look up SID of the group that we are delegating permissions to
    $group = Get-ADGroup -Identity "CN=$delegate_permissions_to_group,$delegate_permissions_to_group_in_ou"
    $sid = new-object System.Security.Principal.SecurityIdentifier $group.SID


    # Allow writes to computers
    $computers_schema_id = new-object Guid bf967a86-0de6-11d0-a285-00aa003049e2
    $ace = new-object System.DirectoryServices.ActiveDirectoryAccessRule $sid,"GenericAll","Allow","All",$computers_schema_id
    $acl.AddAccessRule($ace)
    Set-Acl -AclObject $acl -Path "$delegate_permissions_for_ou"
    echo "Success."
}
catch {
    Write-Host "Failed to add SystemAccount to delegate computers."
}
