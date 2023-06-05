
# Database design requirements
## Network
1) There MAY be several networks with the same `chain_id`
2) Network MAY accept any URL-like value in `rpc_url`
3) Networks MUST have value of `type` only from `NetworkType` enum

## Indexer
1) There MUST be unique `name` for every indexer
2) Indexer MUST belong only to one `Network` and every `Network` MAY have several indexers
3) Indexer MAY have several `watched_tokens`
4) Indexer CAN receive `null` value in `strategy_params`

## Token
1) There MAY be several tokens with the same `address`
2) Tokens MUST have unique pair of values `address` and `network`
3) There MAY be several tokens with the same `name`
4) Tokens MUST have value of `type` only from `TokenType` enum
5) Tokens MUST have value of `strategy` only from `TokenStrategy` enum
6) Tokens MUST belong only to one `Network` and every `Network` MAY have several tokens
7) Tokens have `total_supply` and `volume` as OPTIONAL parameters

## TokenBalance
1) TokenBalances MUST have nullable columns `amount` and `token_id`

