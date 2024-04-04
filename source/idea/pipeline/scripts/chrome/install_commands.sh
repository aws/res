#!/usr/bin/env bash
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

set -ex

sudo apt-get -y install unzip curl jq

# Get latest stable chrome and chrome driver distros from google chrome labs.
url="https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json"
distros=$(curl ${url} | jq '.channels.Stable.downloads')

# Install chrome driver.
wget -qP /tmp/ $(echo $distros | jq --raw-output '.chromedriver | .[] | select(.platform=="linux64") | .url')
sudo unzip -oj /tmp/chromedriver-linux64.zip -d /usr/bin
sudo chmod 755 /usr/bin/chromedriver

# Install chrome.
wget -qP /tmp/ $(echo "$distros" | jq --raw-output '.chrome | .[] | select(.platform=="linux64") | .url')
sudo unzip -oj /tmp/chrome-linux64.zip -d /usr/bin
sudo chmod 755 /usr/bin/chrome
