from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel


class ProviderSendResult(BaseModel):
    success: bool
    provider_message_id: Optional[str] = None
    status: str = "SENT" # SENT, QUEUED, FAILED
    error_message: Optional[str] = None
    raw_response: Dict[str, Any] = {}


NotificationDeliveryResult = ProviderSendResult


class NotificationProvider(ABC):
    """Abstract interface for all notification communication adapters."""
    
    @abstractmethod
    async def send_message(
        self,
        recipient_address: str,
        content: str,
        template_id: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
    ) -> ProviderSendResult:
        pass

    @abstractmethod
    def verify_webhook_signature(self, raw_body: bytes, signature_header: str) -> bool:
        pass


NotificationProviderAdapter = NotificationProvider
