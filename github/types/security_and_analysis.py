from typing import Literal, TypedDict

from typing_extensions import NotRequired

__all__ = ("SecurtiyAndAnalysis",)


class AdvancedSecurity(TypedDict):
    status: Literal["enabled", "disabled"]


class SecretScanning(TypedDict):
    status: Literal["enabled", "disabled"]


class SecretScanningPushProtection(TypedDict):
    status: Literal["enabled", "disabled"]


class SecurtiyAndAnalysis(TypedDict):
    advanced_security: NotRequired[AdvancedSecurity]
    secret_scanning: NotRequired[SecretScanning]
    secret_scanning_push_protection: NotRequired[SecretScanningPushProtection]
