def shorten_tx_hash(tx_hash: str, digits: int = 20) -> str:
    if tx_hash.startswith("0x"):
        if len(tx_hash) != 66:
            return tx_hash
    else:
        return tx_hash
    return f"{tx_hash[: (digits - 2) // 2]}...{tx_hash[-(digits - 2) // 2:]}"
