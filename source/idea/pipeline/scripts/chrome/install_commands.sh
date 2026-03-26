#!/usr/bin/env bash
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

set -ex

export DEBIAN_FRONTEND=noninteractive
sudo apt-get update
sudo apt-get -y install unzip curl jq

# Require chromium-browser from the CodeBuild image
if ! command -v chromium-browser &> /dev/null; then
    echo "ERROR: chromium-browser not found in CodeBuild image. Use an image with Chromium pre-installed."
    exit 1
fi

# Remove any pre-existing chromedriver to avoid conflicts
sudo rm -f /usr/bin/chromedriver /usr/local/bin/chromedriver

# Get system Chromium major version
CHROME_MAJOR=$(chromium-browser --version | grep -oP '\d+' | head -1)
echo "System Chromium major version: ${CHROME_MAJOR}"

# Download matching ChromeDriver
MILESTONES_URL="https://googlechromelabs.github.io/chrome-for-testing/latest-versions-per-milestone-with-downloads.json"
CHROMEDRIVER_URL=$(curl -s "$MILESTONES_URL" \
  | jq -r ".milestones.\"${CHROME_MAJOR}\".downloads.chromedriver[] | select(.platform==\"linux64\") | .url // empty")

if [ -z "$CHROMEDRIVER_URL" ]; then
    echo "ERROR: No ChromeDriver available for Chromium ${CHROME_MAJOR}. Update the CodeBuild image or install a supported Chromium version."
    exit 1
fi

wget -qP /tmp/ "$CHROMEDRIVER_URL"
sudo unzip -oj /tmp/chromedriver-linux64.zip -d /usr/bin
sudo chmod 755 /usr/bin/chromedriver
