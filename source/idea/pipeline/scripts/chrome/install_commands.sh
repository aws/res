#!/usr/bin/env bash
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

set -ex

sudo apt-get -y install unzip

wget -qP /tmp/ "https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/120.0.6099.109/linux64/chromedriver-linux64.zip"
sudo unzip -oj /tmp/chromedriver-linux64.zip -d /usr/bin
sudo chmod 755 /usr/bin/chromedriver

echo 'debconf debconf/frontend select Noninteractive' | sudo debconf-set-selections
wget -qO- https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
sudo sh -c 'echo "deb https://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list'
sudo apt-get update
sudo apt-get -y install google-chrome-stable
