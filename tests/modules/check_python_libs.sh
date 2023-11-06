#!/bin/bash

REQUIREMENTS_FILE=${1:-"soca.txt"}
REL_REQUIREMENTS_FILE="../../requirements/${REQUIREMENTS_FILE}"

requirements=()
while read pkg; do
  if [[ "$pkg" == *"#"* || -z "$pkg" ]]; then
      echo -n ""
  else
      PACKAGE_NAME=$(echo $pkg | cut -d"=" -f1)
      CURRENT_VERSION=$(echo $pkg | cut -d"=" -f3)
      echo "checking $PACKAGE_NAME ..."
      INSTALLED_VERSION=$(pip3 show $PACKAGE_NAME | grep "Version:" | awk '{print $2}')
      if [[ "$CURRENT_VERSION" != "$INSTALLED_VERSION" ]]; then
        if [[ -z "$INSTALLED_VERSION" ]]; then
            message="${CURRENT_VERSION} -> (not installed)"
        else
            message="${CURRENT_VERSION} -> $INSTALLED_VERSION"
        fi
        echo "- ${message}"
        requirements+=("$PACKAGE_NAME: ${message}")
      else
        echo "- $CURRENT_VERSION (in sync)"
      fi
  fi
done <"${REL_REQUIREMENTS_FILE}"

if [[ ${#requirements[@]} == 0 ]]; then
    echo "✓ All requirements are in sync."
else
    echo ""
    echo "----------------------------------------------------------------------------"
    echo " Updates Required: (requirements.txt) -> (installed version)"
    echo "----------------------------------------------------------------------------"
    for requirement in "${requirements[@]}"
    do
        echo $requirement
    done
    echo "----------------------------------------------------------------------------"
    exit 1
fi

