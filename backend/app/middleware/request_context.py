from typing import Optional

from fastapi import Request


def get_request_ip(request: Request) -> Optional[str]:
    if request.client:
        return request.client.host
    return None
