import logging
import time
from dataclasses import dataclass

import requests

logger = logging.getLogger(__name__)


@dataclass
class TokenInfo:
    """Container for API token information."""

    token: str
    token_id: str
    access_token: str
    username: str
    base_url: str


def get_api_token(
    username: str, password: str, base_url: str, keycloak_realm: str, client_id: str
) -> TokenInfo:
    """
    Generate an API token for testing.

    Returns:
        TokenInfo: Object containing token, token_id, access_token, username, and base_url
    """
    token_url = f"{base_url}/keycloak/realms/{keycloak_realm}/protocol/openid-connect/token"
    data = {
        "client_id": client_id,
        "username": username,
        "password": password,
        "grant_type": "password",
        "scope": "workspaces",
    }

    response = requests.post(token_url, data=data)
    response.raise_for_status()
    token_data = response.json()
    access_token = token_data.get("access_token")

    token_url = f"{base_url}/api/workspaces/{username}/me/tokens"

    response = requests.post(
        token_url,
        headers={"Authorization": f"Bearer {access_token}"},
        json={"name": f"pyeodh-test-token-{int(time.time())}"},
    )
    response.raise_for_status()

    token = response.json().get("token")
    token_id = response.json().get("id")

    return TokenInfo(
        token=token,
        token_id=token_id,
        access_token=access_token,
        username=username,
        base_url=base_url,
    )


def delete_api_token(token_info: TokenInfo):
    """
    Delete an API token after testing.

    Args:
        token_info: TokenInfo object containing the token information
    """
    token_url = f"{token_info.base_url}/api/workspaces/{token_info.username}/me/tokens/{token_info.token_id}"
    headers = {"Authorization": f"Bearer {token_info.access_token}"}

    response = requests.delete(token_url, headers=headers)
    response.raise_for_status()
    logger.info(f"Successfully deleted token {token_info.token_id}")
