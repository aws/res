from ideasdk.protocols import TokenServiceProtocol, AuthResult
from ideadatamodel.api.api_model import ApiAuthorizationType
from typing import Optional, Dict


class MockTokenService(TokenServiceProtocol):

    def get_access_token_using_client_credentials(self, cached=True) -> AuthResult:
        return AuthResult()

    def decode_token(self, token: str, verify_exp: Optional[bool] = True) -> Dict:
        return {}

    def is_token_expired(self, token: str) -> bool:
        return False

    def get_username(self, access_token: str, verify_exp=True) -> Optional[str]:
        return None

