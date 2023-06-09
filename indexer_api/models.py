import math
from django.db import models

INT256_MAX_DIGITS = int(math.ceil(math.log10(2 ** 256)))
INT256_DECIMAL_PLACES = 0  # wei values has no decimal point
ETHEREUM_ADDRESS_LENGTH = 42
ETHEREUM_TX_HASH_LENGTH = 66
TX_HASH_LENGTH = 66
STRING_LENGTH = 255
DEFAULT_STEP = 1000
DEFAULT_LAST_BLOCK = 0


class NetworkType(models.TextChoices):
    filterable = ("filterable", "Filterable eth_filter")
    no_filters = ("no_filters", "No filters supported")


class TokenStrategy(models.TextChoices):
    event_based_transfer = ("event_based_transfer", "Event-based transfers")
    receipt_based_transfer = ("receipt_based_transfer", "Receipt-based transfers")


class IndexerStrategy(models.TextChoices):
    recipient = ("recipient", "Recipient")
    sender = ("sender", "Sender")
    token_scan = ("token_scan", "Scan transfers (all transfers are saved)")
    tokenomics = ("tokenomics", "Tokenomics parameters")
    specified_holders = ("specified_holders", "Specified holders")
    transfers_participants = ("transfers_participants", "Transfer participants")


class TokenType(models.TextChoices):
    native = ("native", "Native")
    erc20 = ("erc20", "ERC20 Fungible token")
    erc721 = ("erc721", "NFT ERC721")
    erc721enumerable = ("erc721enumerable", "NFT ERC721Enumerable")
    erc777 = ("erc777", "ERC777 Fungible token")
    erc1155 = ("erc1155", "ERC1155 collection token")


class IndexerType(models.TextChoices):
    transfer_indexer = ("transfer_indexer", "Transfer indexer")
    balance_indexer = ("balance_indexer", "Balance indexer")


class IndexerStatus(models.TextChoices):
    on = ("on", "Active")
    off = ("off", "Disabled")


FUNGIBLE_TOKENS = [TokenType.native, TokenType.erc20, TokenType.erc777]
NON_FUNGIBLE_TOKENS = [TokenType.erc721, TokenType.erc721enumerable]
ERC1155_TOKENS = [TokenType.erc1155]


class Network(models.Model):
    chain_id = models.PositiveBigIntegerField()  # possibly there can be several instances of one network
    name = models.CharField(max_length=STRING_LENGTH)
    rpc_url = models.CharField(max_length=STRING_LENGTH * 10)  # possibly can store some token in it
    max_step = models.PositiveBigIntegerField(default=DEFAULT_STEP)
    type = models.CharField(max_length=STRING_LENGTH, choices=NetworkType.choices)
    need_poa = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.chain_id})"


class Indexer(models.Model):
    name = models.CharField(max_length=STRING_LENGTH, unique=True)  # must be unique since is used as identifier
    last_block = models.PositiveBigIntegerField(default=DEFAULT_LAST_BLOCK)
    network = models.ForeignKey(Network, related_name="indexers", on_delete=models.CASCADE)
    watched_tokens = models.ManyToManyField("Token", related_name="indexers")
    strategy = models.CharField(max_length=STRING_LENGTH, choices=IndexerStrategy.choices)
    short_sleep_seconds = models.PositiveBigIntegerField(default=1,
                                                         help_text="Short sleep is time between two filter requests to blockchain")
    long_sleep_seconds = models.PositiveBigIntegerField(default=5,
                                                        help_text="Indexer will sleep this time if no new blocks in blockchain by the moment")
    strategy_params = models.JSONField(verbose_name="Configure indexer's strategy using JSON dict", null=True,
                                       blank=True)

    status = models.CharField(max_length=STRING_LENGTH, choices=IndexerStatus.choices, default=IndexerStatus.off)
    type = models.CharField(max_length=STRING_LENGTH, choices=IndexerType.choices, default=IndexerType.transfer_indexer)

    def __str__(self):
        return f"{self.name}"


class Token(models.Model):
    # not unique: possibly on several chains there can be tokens with the same address
    address = models.CharField(max_length=ETHEREUM_ADDRESS_LENGTH, null=True, blank=True)
    name = models.CharField(max_length=STRING_LENGTH, help_text="Should be kebab-case. Example: usdt-ethereum-indexer")
    strategy = models.CharField(choices=TokenStrategy.choices, max_length=STRING_LENGTH,
                                help_text="Use receipt based transfer strategy with native token. Note: it can be very slow to index")
    network = models.ForeignKey(Network, related_name="tokens", on_delete=models.CASCADE)
    type = models.CharField(choices=TokenType.choices, max_length=STRING_LENGTH,
                            help_text="Options erc721 and erc721enumerable are the same if token is indexed only by transfers (not balances).")

    total_supply = models.DecimalField(max_digits=INT256_MAX_DIGITS, decimal_places=INT256_DECIMAL_PLACES,
                                       default=0)
    volume = models.DecimalField(max_digits=INT256_MAX_DIGITS, decimal_places=INT256_DECIMAL_PLACES, default=0)

    def __str__(self):
        return f"{self.name} on {self.network.name}"

    class Meta:
        unique_together = [["address", "network"]]


class TokenBalance(models.Model):
    holder = models.CharField(max_length=ETHEREUM_ADDRESS_LENGTH)
    token_instance = models.ForeignKey(Token, related_name="balances", on_delete=models.CASCADE)

    amount = models.DecimalField(max_digits=INT256_MAX_DIGITS, decimal_places=INT256_DECIMAL_PLACES, null=True)
    token_id = models.DecimalField(max_digits=INT256_MAX_DIGITS, decimal_places=INT256_DECIMAL_PLACES, null=True)

    def __str__(self):
        return f"Balance of {self.holder} on {self.token_instance.address}"


class TokenTransfer(models.Model):
    token_instance = models.ForeignKey(Token, related_name="transfers", on_delete=models.CASCADE)
    operator = models.CharField(max_length=ETHEREUM_ADDRESS_LENGTH, null=True, blank=True)
    sender = models.CharField(max_length=ETHEREUM_ADDRESS_LENGTH)
    recipient = models.CharField(max_length=ETHEREUM_ADDRESS_LENGTH)
    tx_hash = models.CharField(max_length=ETHEREUM_TX_HASH_LENGTH, unique=True)
    token_id = models.DecimalField(max_digits=INT256_MAX_DIGITS, decimal_places=INT256_DECIMAL_PLACES, null=True,
                                   blank=True)
    amount = models.DecimalField(max_digits=INT256_MAX_DIGITS, decimal_places=INT256_DECIMAL_PLACES, null=True,
                                 blank=True)

    def __str__(self):
        return f"{self.token_instance.name} transfer {self.sender} → {self.recipient}"
