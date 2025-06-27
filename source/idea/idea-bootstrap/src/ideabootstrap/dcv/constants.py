GL_DISPLAYS_VALUE = ":0.0"
X_SERVER_MAX_TIMEOUT_SEC = 120
GDM_CONFIG_RHEL_PATH = "/etc/gdm/custom.conf"
GDM_CONFIG_DEBIAN_PATH = "/etc/gdm3/custom.conf"
DCV_CONFIG_FILE_PATH = "/etc/dcv/dcv.conf"
DCV_AGENT_CONFIG_FILE_PATH = "/etc/dcv-session-manager-agent/agent.conf"
DCV_AGENT_TAGS_DIR = "/etc/dcv-session-manager-agent/tags/"
DCV_AGENT_TAGS_FILE_NAME = "idea_tags.toml"
DCV_AGENT_ARCHIVE_TAGS_DIR = "/etc/dcv-session-manager-agent/archive-tags/"
BROKER_CERTIFICATE_LOCATION_LOCAL = "/etc/dcv/dcv_broker/dcvsmbroker_ca.pem"
USB_DEVICES_CONF_FILE_PATH = "/etc/dcv/usb-devices.conf"
IDEA_SERVICES_LOGS_PATH = "/opt/idea/.services/logs"
RC_LOCAL_RHEL_PATH = "/etc/rc.d/rc.local"
RC_LOCAL_DEBIAN_PATH = "/etc/rc.local"
RC_LOCAL_SERVICE_PATH = "/etc/systemd/system/rc-local.service"
DCV_SERVER_SERVICE_PATH = "/usr/lib/systemd/system/dcvserver.service"
DCV_AGENT_SERVICE_PATH = "/usr/lib/systemd/system/dcv-session-manager-agent.service"

WINDOWS_DCV_EXECUTABLE_PATH = "C:\\Program Files\\NICE\\DCV\\Server\\bin\\dcv.exe"
DCV_REGISTRY_PATH = "S-1-5-18\\Software\\GSettings\\com\\nicesoftware\\dcv"
WINDOWS_DCV_REGISTRY_PATH = (
    f"Microsoft.PowerShell.Core\\Registry::\\HKEY_USERS\\{DCV_REGISTRY_PATH}"
)
WINDOWS_DCV_AGENT_CONFIG_FILE_PATH = (
    "C:\\Program Files\\NICE\\DCVSessionManagerAgent\\conf\\agent.conf"
)
WINDOWS_DCV_AGENT_TAGS_DIR = (
    "C:\\Program Files\\NICE\\DCVSessionManagerAgent\\conf\\tags"
)
WINDOWS_DCV_AGENT_ARCHIVE_TAGS_DIR = (
    "C:\\Program Files\\NICE\\DCVSessionManagerAgent\\conf\\archive-tags"
)
WINDOWS_USB_DEVICES_CONF_FILE_PATH = (
    "C:\\Program Files\\NICE\\DCV\\Server\\conf\\usb-devices.conf"
)
IDEA_SCRIPTS_DIR = "C:\\IDEA\\LocalScripts"
POST_REBOOT_SCRIPT_PATH = f"{IDEA_SCRIPTS_DIR}\\PostBootstrapRebootExecuteOnce.ps1"
WINDOWS_DCV_CERT_DIR = (
    "C:\\Windows\\system32\\config\\systemprofile\\AppData\\Local\\NICE\\dcv"
)

IDLE_TIMEOUT_KEY = "vdc.dcv_session.idle_timeout"
IDLE_TIMEOUT_WARNING_KEY = "vdc.dcv_session.idle_timeout_warning"
AGENT_COMMUNICATION_PORT_KEY = "vdc.dcv_broker.agent_communication_port"
USB_REMOTIZATION_KEY = "vdc.server.usb_remotization"
