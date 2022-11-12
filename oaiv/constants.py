#
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
