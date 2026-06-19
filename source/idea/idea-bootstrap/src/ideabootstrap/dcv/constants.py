GL_DISPLAYS_VALUE = ":0.0"
X_SERVER_MAX_TIMEOUT_SEC = 120
GDM_CONFIG_RHEL_PATH = "/etc/gdm/custom.conf"
GDM_CONFIG_DEBIAN_PATH = "/etc/gdm3/custom.conf"
DCV_CONFIG_FILE_PATH = "/etc/dcv/dcv.conf"
USB_DEVICES_CONF_FILE_PATH = "/etc/dcv/usb-devices.conf"
IDEA_SERVICES_LOGS_PATH = "/opt/idea/.services/logs"
RC_LOCAL_RHEL_PATH = "/etc/rc.d/rc.local"
RC_LOCAL_DEBIAN_PATH = "/etc/rc.local"
RC_LOCAL_SERVICE_PATH = "/etc/systemd/system/rc-local.service"
DCV_SERVER_SERVICE_PATH = "/usr/lib/systemd/system/dcvserver.service"

WINDOWS_DCV_EXECUTABLE_PATH = "C:\\Program Files\\NICE\\DCV\\Server\\bin\\dcv.exe"
DCV_REGISTRY_PATH = "S-1-5-18\\Software\\GSettings\\com\\nicesoftware\\dcv"
WINDOWS_DCV_REGISTRY_PATH = (
    f"Microsoft.PowerShell.Core\\Registry::\\HKEY_USERS\\{DCV_REGISTRY_PATH}"
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
USB_REMOTIZATION_KEY = "vdc.server.usb_remotization"

DCV_AUTOMATIC_CONSOLE_SESSION_ID = "console"

DCV_PERMISSIONS_FILE_NAME = "idea.perm"
DCV_PERMISSIONS_DIR = "/etc/dcv/console/"
WINDOWS_DCV_PERMISSIONS_DIR = "C:\\Program Files\\NICE\\DCV\\console\\"
