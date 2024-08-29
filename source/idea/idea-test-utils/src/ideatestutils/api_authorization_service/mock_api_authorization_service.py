from ideasdk.auth.api_authorization_service_base import ApiAuthorizationServiceBase
from ideadatamodel.api.api_model import ApiAuthorizationType, ApiAuthorization
from ideadatamodel.auth import User
from typing import Optional, Dict, List


class MockApiAuthorizationService(ApiAuthorizationServiceBase):
    
    def get_user_from_token_username(self, token_username: Optional[str]):
        return User (
            username = token_username,
            role = 'user',
            enabled = True
        )
    
    def get_authorization(self, decoded_token: Optional[Dict]) -> Optional[ApiAuthorization]:
        return ApiAuthorization(
            type=ApiAuthorizationType.USER,
        )

    def is_scope_authorized(self, decoded_token: str, scope: str) -> bool:
        return False
    
    def get_username(self, decoded_token: str) -> Optional[str]:
        return None

    def get_roles_for_user(self, user: User, role_assignment_resource_key: Optional[str]) -> List[Dict]:
        return []