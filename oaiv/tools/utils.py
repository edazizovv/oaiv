#
import json


#
from web3 import Web3
from web3.middleware import geth_poa_middleware


#


#
def check_precision(currency):

    if currency == 'USDC':
        precision = 6
    else:
        raise KeyError("Unknown contract name")

    """
    if network in ['mainnet', 'goerli', 'ropsten']:

        with open('./oaiv/tools/address/{0}/info.json'.format(network), 'r') as file:
            names = json.load(file)
        if currency in names.keys():
            precision = int(names[currency]['precision'])
        else:
            raise KeyError("Unknown currency name")

        return precision

    else:

        raise KeyError("Invalid network name")
    """

    return precision


def data_constructor(receiver_address, amount, currency):
    method = '0xa9059cbb'
    receiver = "0" * (64 - len(receiver_address[2:])) + receiver_address[2:]
    amount_precision = check_precision(currency=currency)
    amount = hex(int(amount * (10 ** amount_precision)))[2:]
    amount = "0" * (64 - len(amount)) + amount
    data = method + receiver + amount
    return data


def format_provider(ethereum_network, infura_project_id):

    provider = 'https://{0}.infura.io/v3/{1}'.format(
        ethereum_network,
        infura_project_id
    )

    return provider


def format_w3(provider):

    w3 = Web3(Web3.HTTPProvider(
        provider
    ))
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)

    return w3
