#!/usr/bin/env bash
#
# Publish the RES sample templates to an S3 bucket and print the values a deployment needs.
#
# Usage:
#   ./publish-samples.sh --bucket my-bucket [--prefix res-samples] [--region us-west-2] [--profile p]
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

BUCKET=""
PREFIX="res-samples"
REGION=""
PROFILE=""
DRY_RUN="false"

usage() {
  sed -n '3,7p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  cat <<'EOF'

Options:
  --bucket NAME     Target S3 bucket. Required.
  --prefix PATH     Key prefix inside the bucket. Default: res-samples. Use "" for the root.
  --region NAME     Region for the AWS CLI calls. Defaults to the CLI's configured region.
  --profile NAME    AWS CLI profile.
  --dry-run         Validate and print the values without uploading.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --bucket) BUCKET="${2:-}"; shift 2 ;;
    --prefix) PREFIX="${2:-}"; shift 2 ;;
    --region) REGION="${2:-}"; shift 2 ;;
    --profile) PROFILE="${2:-}"; shift 2 ;;
    --dry-run) DRY_RUN="true"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "publish-samples: unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

die() { echo "publish-samples: $*" >&2; exit 1; }

[[ -n "${BUCKET}" ]] || { echo "publish-samples: --bucket is required" >&2; usage >&2; exit 2; }
command -v aws >/dev/null 2>&1 || die "the AWS CLI is not on PATH"

# Strip leading and trailing slashes so a prefix of "/a/b/" and "a/b" behave the same.
PREFIX="${PREFIX#/}"
PREFIX="${PREFIX%/}"

REQUIRED_FILES=(
  batteries-included/bi.yaml
  batteries-included/demo-managed-ad.yaml
  batteries-included/demo-managed-ad-windows-host.yaml
  batteries-included/network-large-scale.yaml
  batteries-included/public-certs.yaml
  batteries-included/efs-simple.yaml
  batteries-included/res.ldif
  batteries-included/service_account.ps1
  res-ready-ami/imagebuilder-infrastructure.yaml
  res-ready-ami/nested-imagebuilder-components.yaml
  res-ready-ami/components/research-and-engineering-studio-vdi-linux.yaml
  res-ready-ami/components/research-and-engineering-studio-vdi-windows.yaml
)

MISSING=()
for f in "${REQUIRED_FILES[@]}"; do
  [[ -f "${HERE}/${f}" ]] || MISSING+=("${f}")
done

if [[ ${#MISSING[@]} -gt 0 ]]; then
  echo "publish-samples: the sample tree is incomplete. Missing:" >&2
  printf '  %s\n' "${MISSING[@]}" >&2
  die "refusing to publish a partial tree"
fi

AWS_ARGS=()
[[ -n "${PROFILE}" ]] && AWS_ARGS+=(--profile "${PROFILE}")
[[ -n "${REGION}" ]] && AWS_ARGS+=(--region "${REGION}")

# The nested TemplateURL values must use the endpoint of the region the bucket actually lives in,
# which is not necessarily the region the CLI is configured for.
BUCKET_REGION="$(aws "${AWS_ARGS[@]}" s3api get-bucket-location --bucket "${BUCKET}" \
  --query 'LocationConstraint' --output text 2>/dev/null)" \
  || die "cannot read the location of bucket ${BUCKET}. Does it exist and is it accessible?"

case "${BUCKET_REGION}" in
  None|null|"") BUCKET_REGION="us-east-1" ;;
  EU) BUCKET_REGION="eu-west-1" ;;
esac

if [[ -n "${PREFIX}" ]]; then
  S3_URI="s3://${BUCKET}/${PREFIX}"
  SAMPLES_S3_BASE="https://${BUCKET}.s3.${BUCKET_REGION}.amazonaws.com/${PREFIX}"
  SAMPLES_S3_PATH="${BUCKET}/${PREFIX}"
else
  S3_URI="s3://${BUCKET}"
  SAMPLES_S3_BASE="https://${BUCKET}.s3.${BUCKET_REGION}.amazonaws.com"
  SAMPLES_S3_PATH="${BUCKET}"
fi

if [[ "${DRY_RUN}" == "true" ]]; then
  echo "publish-samples: dry run, nothing uploaded"
else
  aws "${AWS_ARGS[@]}" s3 cp "${HERE}/" "${S3_URI}/" \
    --recursive \
    --exclude '*' \
    --include 'batteries-included/*' \
    --include 'res-ready-ami/*' \
    --include 'PROVENANCE.md' \
    --only-show-errors
  echo "publish-samples: uploaded ${#REQUIRED_FILES[@]} files to ${S3_URI}/"
fi

cat <<EOF

Bucket region: ${BUCKET_REGION}

bi.yaml URL, pass as BIStackTemplateURL to the RES installation:

  ${SAMPLES_S3_BASE}/batteries-included/bi.yaml

bi.yaml parameters:

  SamplesS3Base   ${SAMPLES_S3_BASE}
  SamplesS3Path   ${SAMPLES_S3_PATH}

res-ready-ami/nested-imagebuilder-components.yaml parameter:

  SamplesS3Base   ${SAMPLES_S3_BASE}
EOF
