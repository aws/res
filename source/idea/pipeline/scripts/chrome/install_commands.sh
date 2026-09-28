#!/usr/bin/env bash
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

set -ex

export DEBIAN_FRONTEND=noninteractive
sudo apt-get update
sudo apt-get -y install unzip curl jq wget

# Remove pre-installed Chromium and ChromeDriver
sudo rm -f /usr/local/bin/chromium-browser /usr/local/bin/chromedriver

# Install latest stable Chromium and matching ChromeDriver from Chrome for Testing
LATEST_URL="https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json"

LATEST_JSON=$(curl -s "$LATEST_URL")
CHROME_URL=$(echo "$LATEST_JSON" | jq -r '.channels.Stable.downloads.chrome[] | select(.platform=="linux64") | .url')
CHROMEDRIVER_URL=$(echo "$LATEST_JSON" | jq -r '.channels.Stable.downloads.chromedriver[] | select(.platform=="linux64") | .url')

if [ -z "$CHROME_URL" ] || [ -z "$CHROMEDRIVER_URL" ]; then
    echo "ERROR: Failed to get download URLs from Chrome for Testing."
    exit 1
fi

# Install Chromium
wget -q -O /tmp/chrome-linux64.zip "$CHROME_URL"
sudo mkdir -p /opt/chromium
sudo unzip -o /tmp/chrome-linux64.zip -d /opt/chromium
sudo ln -sf /opt/chromium/chrome-linux64/chrome /usr/local/bin/chromium-browser
rm -f /tmp/chrome-linux64.zip

# Install ChromeDriver
wget -q -O /tmp/chromedriver-linux64.zip "$CHROMEDRIVER_URL"
sudo unzip -oj /tmp/chromedriver-linux64.zip -d /usr/local/bin
sudo chmod 755 /usr/local/bin/chromedriver
rm -f /tmp/chromedriver-linux64.zip

# Verify
echo "Chromium: $(chromium-browser --version)"
echo "ChromeDriver: $(chromedriver --version)"
