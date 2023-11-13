#!/bin/bash

# If Viperlight is not installed on your system:
# > wget https://s3.amazonaws.com/viperlight-scanner/latest/viperlight.zip
# > unzip viperlight.zip
# > ./install.sh (require npm)
# based on https://github.com/hawkeyesec/scanner-cli

VIPERLIGHT=$(which viperlight)
cd ../
viperlight scan
