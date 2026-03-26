#!/bin/bash

# Script to inject authentication parameters into controller function signatures and docstrings
# This script modifies generated controller files to add user and token_info parameters

GENERATED_DIR="$1"

if [ -z "$GENERATED_DIR" ]; then
    echo "Usage: $0 <generated_directory>"
    exit 1
fi

if [ ! -d "$GENERATED_DIR" ]; then
    echo "Error: Directory $GENERATED_DIR does not exist"
    exit 1
fi

echo "Injecting authentication parameters into controller functions..."

# Fix invalid security function names with dots (OpenAPI Generator bug)
find "$GENERATED_DIR" -name "*security_controller*.py" -exec sed -i '' 's/def info_from_[^(]*/def bearer_auth/g' {} \;

# Fix bearer_auth function signature to add request parameter while keeping token parameter
find "$GENERATED_DIR" -name "*security_controller*.py" -exec sed -i '' 's/def bearer_auth(token):/def bearer_auth(token, request):/g' {} \;

# Add proper parameter documentation for bearer_auth function
find "$GENERATED_DIR" -name "*security_controller*.py" -exec sed -i '' '/^    """$/,/^    """$/c\
    """\
    Check and retrieve authentication information from custom bearer token.\
    Returned value will be passed in '\''token_info'\'' parameter of your operation function, if there is one.\
    '\''sub'\'' or '\''uid'\'' will be set in '\''user'\'' parameter of your operation function, if there is one.\
\
    :param token: Token provided by Authorization header\
    :type token: str\
    :param request: The request object containing headers and authorization information\
    :type request: connexion.request\
    :return: Decoded token information or None if token is invalid\
    :rtype: dict | None\
    """
' {} \;

# Inject username and token_info parameters into controller function signatures (only if not already present)
find "$GENERATED_DIR" -name "*controller*.py" -not -name "*security_controller*.py" -exec sed -i '' 's/def \([^(]*\)(\([^)]*[^)]\)):  # noqa: E501/def \1(\2, user=None, token_info=None):  # noqa: E501/g' {} \;
find "$GENERATED_DIR" -name "*controller*.py" -not -name "*security_controller*.py" -exec sed -i '' 's/def \([^(]*\)():  # noqa: E501/def \1(user=None, token_info=None):  # noqa: E501/g' {} \;

# Add parameter descriptions for user and token_info in controller docstrings
find "$GENERATED_DIR" -name "*controller*.py" -not -name "*security_controller*.py" -exec sed -i '' '/^    :rtype:/i\
    :param user: The authenticated user information\
    :type user: str\
    :param token_info: The token information from authentication\
    :type token_info: dict
' {} \;

echo "Authentication parameter injection completed!"
