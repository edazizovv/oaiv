# -*- coding: utf-8 -*-
"""Addresses."""

import json

from web3 import Web3

from constants import token_info_eth


def load_contract(name: str, w3: Web3):
    """

    :param w3:
    :type name: object
    """
    address = find_address(name=name)
    json_file_path = f"tools/abidata/{name}.json"

    try:
        with open(json_file_path, 'r') as file:
            abi = json.load(file)
    except FileNotFoundError:
        raise Exception("Unknown contract name")

    return w3.eth.contract(address=address, abi=abi)


def find_address(name):
    tech_address = {
        'QUOTER': '0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6',
        'ROUTER': '0xE592427A0AEce92De3Edee1F18E0157C05861564',
    }

    token_address = {key: token_info_eth[key]['contract'] for key in token_info_eth}

    contract_address = {**tech_address, **token_address}

    return contract_address.get(name, None)
