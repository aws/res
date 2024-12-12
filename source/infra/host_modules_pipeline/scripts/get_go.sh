#!/usr/bin/env bash
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

go_ver=22.3
os_type=$(uname -s)
arch_type=$(uname -m)

if [ "$os_type" == "Linux" ]; then
    if [ "$arch_type" == "x86_64" ]; then
        go_arch=linux-amd64
        expected_go_sha=8920ea521bad8f6b7bc377b4824982e011c19af27df88a815e3586ea895f1b36
    elif [ "$arch_type" == "aarch64" ]; then
        go_arch=linux-arm64
        expected_go_sha=6c33e52a5b26e7aa021b94475587fce80043a727a54ceb0eee2f9fc160646434
    else
        echo "Unsupported architecture: $arch_type"
        exit 1
    fi
elif [ "$os_type" == "Darwin" ]; then
    go_arch=darwin-amd64
    expected_go_sha=610e48c1df4d2f852de8bc2e7fd2dc1521aac216f0c0026625db12f67f192024
else
    echo "Unsupported OS: $os_type"
    exit 1
fi

go_archive=go1.${go_ver}.${go_arch}.tar.gz
echo "Downloading ${go_archive}..."
curl -0L -s https://go.dev/dl/${go_archive} -o ${go_archive}

# Calculate SHA-256 checksum
if [ "$os_type" == "Darwin" ]; then
    actual_sum=$(shasum -a 256 ./${go_archive} | cut -d" " -f1)
else
    actual_sum=$(sha256sum -b ./${go_archive} | cut -d" " -f1)
fi

# Verify checksum
if [ "$actual_sum" != "$expected_go_sha" ]; then
    echo "SHA sum does NOT match"
    exit 1
fi

# Extract and install Go
tar -xf ${go_archive}
mv go /usr/local/
ln -s /usr/local/go/bin/go /usr/local/bin
ln -s /usr/local/go/bin/gofmt /usr/local/bin

echo "Go installation successful!"
