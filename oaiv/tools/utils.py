# -*- coding: utf-8 -*-
"""Utils."""

from decimal import Decimal

from web3 import Web3
from web3.middleware import geth_poa_middleware

from oaiv.constants import get_precision_eth


def data_constructor(w3, receiver_address, amount, currency):
    method = '0xa9059cbb'
    receiver = "0" * (64 - len(receiver_address[2:])) + receiver_address[2:]
    amount_precision = get_precision_eth(w3=w3, token_name=currency)
    amount = hex(int(Decimal(amount) * (Decimal(10) ** Decimal(amount_precision))))[2:]
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
    w3 = Web3(Web3.HTTPProvider(provider))
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    return w3
