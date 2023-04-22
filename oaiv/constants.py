#
import json
from enum import Enum, auto


#


#


#
class BlockchainName:
    ETHEREUM = 'ETHEREUM'
    BITCOIN = 'BITCOIN'


class BlockchainType(Enum):
    ETHEREUM = auto()
    BITCOIN = auto()


def blockchain_type(blockchain_name):
    available = {BlockchainName.ETHEREUM: BlockchainType.ETHEREUM,
                 BlockchainName.BITCOIN: BlockchainType.BITCOIN}
    if blockchain_name in available.keys():
        return available[blockchain_name]
    else:
        raise KeyError("Invalid blockchain type {0} is entered; please, check available ones".format(blockchain_type))


def blockchain_name(blockchain_type):
    available = {BlockchainType.ETHEREUM: BlockchainName.ETHEREUM,
                 BlockchainType.BITCOIN: BlockchainName.BITCOIN}
    if blockchain_type in available.keys():
        return available[blockchain_type]
    else:
        raise KeyError("Invalid blockchain name {0} is entered; please, check available ones".format(blockchain_name))


def available_blockchain_types():
    return [BlockchainType.ETHEREUM, BlockchainType.BITCOIN]


def available_blockchain_names():
    return [BlockchainName.ETHEREUM, BlockchainName.BITCOIN]


def blockchain_gas_currency(blockchain_type):
    available = {BlockchainType.ETHEREUM: 'ETH',
                 BlockchainType.BITCOIN: 'BTC'}
    if blockchain_type in available.keys():
        return available[blockchain_type]
    else:
        raise KeyError("Invalid blockchain type {0} is entered; please, check available ones".format(blockchain_type))


# TODO: check this is valid for all our tokens
EIP20_ABI = json.loads('[{"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_from","type":"address"},{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transferFrom","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[{"name":"_owner","type":"address"},{"name":"_spender","type":"address"}],"name":"allowance","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"anonymous":false,"inputs":[{"indexed":true,"name":"_from","type":"address"},{"indexed":true,"name":"_to","type":"address"},{"indexed":false,"name":"_value","type":"uint256"}],"name":"Transfer","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"_owner","type":"address"},{"indexed":true,"name":"_spender","type":"address"},{"indexed":false,"name":"_value","type":"uint256"}],"name":"Approval","type":"event"}]')

# TODO: check if it is possible to retrieve this info online or somehow in another way
token_info_eth = {
    'ETH': {'contract': '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'},
    'USDC': {'contract': '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'},
    'USDT': {'contract': '0xdac17f958d2ee523a2206206994597c13d831ec7'},
}


def _invalid_token_handler(invalid_value):
    raise ValueError("Invalid token_name provided: {0}".format(invalid_value))


def get_precision_eth(w3, token_name):
    token_contract_address = get_contract_eth(token_name=token_name)
    address2 = w3.to_checksum_address(token_contract_address)
    contract = w3.eth.contract(address2, abi=EIP20_ABI)
    return contract.functions.decimals().call()


def get_contract_eth(token_name):
    if token_name in token_info_eth.keys():
        return token_info_eth[token_name]['contract']
    else:
        _invalid_token_handler(token_name)
