from django.core.exceptions import ValidationError
from web3 import Web3


def validate_explorer_url(explorer_url: str):
    if explorer_url.strip().endswith("/"):
        raise ValidationError("Explorer url must have no trailing slash")


def is_ethereum_address_valid(address: str) -> bool:
    try:
        Web3.to_checksum_address(address)
        return True
    except Exception:
        return False


def validate_ethereum_address(address: str):
    if not is_ethereum_address_valid(address):
        raise ValidationError("Address is invalid")
