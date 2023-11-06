#!/bin/bash

pip3 install bandit
bandit -r ../ --exclude installer/resources/src/venv-py-installer,installer/resources/src/cdk.out -ll
