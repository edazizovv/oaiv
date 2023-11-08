# -*- coding: utf-8 -*-
"""Account."""

import time
import json
import datetime
from decimal import Decimal

import pandas
from web3 import Web3
from urllib import parse, request
from eth_account.messages import encode_defunct
from bitcoinlib.encoding import EncodingError
from bitcoinlib.config.config import DEFAULT_NETWORK
from bitcoinlib.services.services import Service
from bitcoinlib.keys import HDKey, Address, BKeyError
from oaiv_btc.func import Transactor

from tools.utils import format_provider, format_w3, data_constructor
from tools.address import find_address
from constants import BlockchainType


class InteractionFunctionality:
    def __init__(self, bitcoin_kwg, ethereum_kwg):
        self.bitcoin_interaction = InteractionFunctionalityBitcoin(**bitcoin_kwg)
        self.ethereum_interaction = InteractionFunctionalityEthereum(**ethereum_kwg)

    def _invalid_blockchain_handler(self, invalid_value):
        raise ValueError(f"Invalid blockchain type provided, should be BlockchainType.ETHEREUM or BlockchainType.BITCOIN; you provided {invalid_value}")

    def is_address(self, address, blockchain):
        if blockchain == BlockchainType.ETHEREUM:
            return self.ethereum_interaction.is_address(address=address)
        elif blockchain == BlockchainType.BITCOIN:
            return self.bitcoin_interaction.is_address(address=address)
        else:
            self._invalid_blockchain_handler(blockchain)

    def is_formatted_address(self, address, blockchain):
        if blockchain == BlockchainType.ETHEREUM:
            return self.ethereum_interaction.is_formatted_address(address=address)
        elif blockchain == BlockchainType.BITCOIN:
            return self.bitcoin_interaction.is_formatted_address(address=address)
        else:
            self._invalid_blockchain_handler(blockchain)

    def format_address(self, address, blockchain):
        if blockchain == BlockchainType.ETHEREUM:
            return self.ethereum_interaction.format_address(address=address)
        elif blockchain == BlockchainType.BITCOIN:
            return self.bitcoin_interaction.format_address(address=address)
        else:
            self._invalid_blockchain_handler(blockchain)

    def is_supported(self, address, blockchain):
        if blockchain == BlockchainType.ETHEREUM:
            return self.ethereum_interaction.is_supported(address=address)
        elif blockchain == BlockchainType.BITCOIN:
            return self.bitcoin_interaction.is_supported(address=address)
        else:
            self._invalid_blockchain_handler(blockchain)

    def is_key_pair(self, blockchain, private_key, address):
        if blockchain == BlockchainType.ETHEREUM:
            return self.ethereum_interaction.is_key_pair(private_key=private_key, address=address)
        elif blockchain == BlockchainType.BITCOIN:
            return self.bitcoin_interaction.is_key_pair(private_key=private_key, address=address)
        else:
            self._invalid_blockchain_handler(blockchain)

    def balance(self, addresses, blockchain):
        if blockchain == BlockchainType.ETHEREUM:
            return self.ethereum_interaction.balance(addresses=addresses)
        elif blockchain == BlockchainType.BITCOIN:
            return self.bitcoin_interaction.balance(addresses=addresses)
        else:
            self._invalid_blockchain_handler(blockchain)

    def get_transactions(self, blockchain, **kwargs):
        if blockchain == BlockchainType.ETHEREUM:
            return self.ethereum_interaction.get_transactions(**kwargs)
        elif blockchain == BlockchainType.BITCOIN:
            return self.bitcoin_interaction.get_transactions(**kwargs)
        else:
            self._invalid_blockchain_handler(blockchain)

    def create_account(self, blockchain):
        if blockchain == BlockchainType.ETHEREUM:
            return self.ethereum_interaction.create_account()
        elif blockchain == BlockchainType.BITCOIN:
            return self.bitcoin_interaction.create_account()
        else:
            self._invalid_blockchain_handler(blockchain)

    def make_transaction(self, blockchain, **kwargs):
        if blockchain == BlockchainType.ETHEREUM:
            return self.ethereum_interaction.make_transaction(**kwargs)
        elif blockchain == BlockchainType.BITCOIN:
            return self.bitcoin_interaction.make_transaction(**kwargs)
        else:
            self._invalid_blockchain_handler(blockchain)


class InteractionFunctionalityBitcoin:
    def __init__(self, **kwargs):
        self.network = DEFAULT_NETWORK
        self.service = Service(network=self.network, providers=None, cache_uri=None)

    def is_address(self, address):
        if isinstance(address, str):
            if len(address) > 0:
                try:
                    _ = Address.parse(address)
                    return True
                except EncodingError as e:
                    return False
            else:
                return False
        else:
            return False

    def is_formatted_address(self, address):
        return self.is_address(address=address)

    def format_address(self, address):
        return address

    def is_supported(self, address):
        if isinstance(address, str):
            if len(address) > 0:
                try:
                    address = Address.parse(address)
                    # only p2pkh / p2wpkh addressed derived from compressed public_key are supported
                    # all other formats (including non-compressed p2pkh / p2sh / p2sh-p2wpkh / p2tr) won't be valid here
                    return any([(address.encoding == 'base58') and (address.script_type == 'p2pkh'),
                                (address.encoding == 'bech32') and (address.script_type == 'p2wpkh')])
                except EncodingError as e:
                    return False
            else:
                return False
        else:
            return False

    def is_key_pair(self, private_key, address):
        try:
            # only p2pkh / p2wpkh addressed derived from compressed public_key are supported
            # all other formats (including non-compressed p2pkh / p2sh / p2sh-p2wpkh / p2tr)
            # might have unexpected behavior here
            address_parsed = Address.parse(address)
            witness_type = address_parsed.witness_type
            encoding = address_parsed.encoding
            script_type = address_parsed.script_type
            hdkey = HDKey(private_key, compressed=True, encoding=encoding, witness_type=witness_type)
            address_derived = hdkey.address(script_type=script_type, encoding=encoding)
            return address_parsed.address == address_derived
        except BKeyError as e:
            return False
        except EncodingError as e:
            return False

    def balance(self, addresses):
        result = {}
        for address in addresses:
            balance = self.service._provider_execute('getbalance', [address])
            # balance = balance / 100_000_000
            # TODO: control source libraries for Decimal
            balance = Decimal(balance) / Decimal("100_000_000")
            result[address] = {'BTC': balance}
        return result

    def get_transactions(self, account, sort='desc', raw=True):

        last_txid = ''
        max_utxos = 100
        request_results = self.service._provider_execute('gettransactions', account, last_txid,  max_utxos)

        if not raw:
            results = {'tx': [], 'datetime': [], 'sender': [], 'receiver': [], 'value': [], 'commission_paid': [],
                       'currency': []}
            for tx in request_results:

                self_inputs = [x for x in tx.inputs if x.address == account]
                self_outputs = [x for x in tx.outputs if x.address == account]
                if len(self_inputs) > 0:
                    # TODO: control source libraries for Decimal
                    value = sum([Decimal(x.value) for x in self_inputs]) - sum([Decimal(x.value) for x in self_outputs])
                    inputs = account
                    outputs = ';'.join([x.address for x in tx.outputs if x.address != account])
                else:
                    # TODO: control source libraries for Decimal
                    value = sum([Decimal(x.value) for x in self_outputs])
                    inputs = ';'.join([x.address for x in tx.inputs])
                    outputs = account
                tx_hash = tx.txid
                tx_datetime = tx.date
                commission = Decimal(tx.fee)
                currency = 'BTC'

                results['tx'].append(tx_hash)
                results['datetime'].append(tx_datetime)
                results['sender'].append(inputs)
                results['receiver'].append(outputs)
                results['value'].append(value)
                results['commission_paid'].append(commission)
                results['currency'].append(currency)

            results = pandas.DataFrame(data=results)
            results['value'] = results['value'] / Decimal("100_000_000")
            results['commission_paid'] = results['commission_paid'] / Decimal("100_000_000")
            results = results.sort_values(by='datetime', ascending=(not (sort == 'desc')))
            results = results.to_dict()
            re = (results, {})
        else:
            re = (request_results, {})
        return re

    def create_account(self):
        hdkey = HDKey()
        private_key = hdkey.private_hex
        # by default, we generate native segwit only (p2wpkh addresses)
        actor = Actor(blockchain=BlockchainType.BITCOIN, private_key=private_key, script_type='p2wpkh')
        return actor

    def make_transaction(self, sender, receiver, value=None, gas=None, **kwargs):

        value = '{0} BTC'.format(value)

        private_hex = sender.private_key
        from_address = Address.parse(sender.address)
        witness_type = from_address.witness_type
        encoding = from_address.encoding
        script_type = from_address.script_type
        hdkey = HDKey(private_hex, compressed=True, encoding=encoding, witness_type=witness_type)
        _ = hdkey.address(script_type=script_type, encoding=encoding)
        kk = Transactor(address=hdkey.address(), hdkey=hdkey)
        address_to = Address.parse(receiver.address)

        # TODO: control source libraries for Decimal
        if gas:
            tx = kk.send_to(address_to, value, offline=False, fee=gas)
        else:
            tx = kk.send_to(address_to, value, offline=False)

        # TODO: consider optimizing this behavior
        if tx.error is not None:
            time.sleep(1)
            tx_check = self.service.gettransaction(tx.txid)
            if not tx_check:
                time.sleep(5)
                tx_check = self.service.gettransaction(tx.txid)
                if not tx_check:
                    if not tx_check:
                        print(tx.info())
                        raise Exception("Unexpected error. Transaction {0} is not sent to the blockchain\n"
                                        "Error message:\n{1}".format(tx.txid, tx.error))
                else:
                    print(tx.info())
                    print(
                        "Transaction is sent to the blockchain, "
                        "however an unexpected response received from the providers\n"
                        "Response message:\n{0}".format(tx.error))
            else:
                print(tx.info())
                print(
                    "Transaction is sent to the blockchain, "
                    "however an unexpected response received from the providers\n"
                    "Response message:\n{0}".format(tx.error))
        tx_id = tx.txid

        return tx_id


class InteractionFunctionalityEthereum:
    def __init__(self, etherscan_api_key, ethplorer_api_key, ethereum_network, infura_project_id):
        self.network = ethereum_network
        self.etherscan_api_key = etherscan_api_key
        self.ethplorer_api_key = ethplorer_api_key
        self.provider = format_provider(
            ethereum_network=ethereum_network,
            infura_project_id=infura_project_id
        )
        self.w3 = format_w3(provider=self.provider)

        self.etherscan = EtherscanInteraction(
            network=ethereum_network,
            etherscan_api_key=etherscan_api_key
        )
        self.ethplorer = EthplorerInteraction(
            ethplorer_api_key=ethplorer_api_key
        )
        self.infura = InfuraInteraction(w3=self.w3)

    def is_address(self, address):
        return self.w3.isAddress(value=address)

    def is_formatted_address(self, address):
        return self.w3.isChecksumAddress(value=address)

    def format_address(self, address):
        return self.w3.toChecksumAddress(value=address)

    def is_supported(self, address):
        return self.w3.isAddress(value=address)

    def is_key_pair(self, private_key, address):
        try:
            message = encode_defunct(text='In memoriam of Ivanov O.A.')
            txx = self.w3.eth.account.sign_message(message, private_key=private_key)
            recovered = self.w3.eth.account.recover_message(message, signature=txx.signature)
            result = recovered == address
            return result
        except Exception as e:
            print(e)
            return False

    def balance(self, addresses):
        addresses = [self.w3.toChecksumAddress(value=address) for address in addresses]

        etherscan_result = self.etherscan.balance(addresses=addresses)
        ethplorer_result = self.ethplorer.balance(addresses=addresses)

        etherscan_result = {self.w3.toChecksumAddress(value=key): etherscan_result[key]
                            for key in etherscan_result.keys()}
        ethplorer_result = {self.w3.toChecksumAddress(value=key): ethplorer_result[key]
                            for key in ethplorer_result.keys()}

        keys = list(etherscan_result.keys())
        keys += [x for x in ethplorer_result.keys() if x not in keys]

        result = dict(etherscan_result)
        for address in ethplorer_result.keys():
            for currency in ethplorer_result[address].keys():
                result[address][currency] = ethplorer_result[address][currency]

        return result

    def get_transactions(self, **kwargs):
        return self.etherscan.get_transactions(**kwargs)

    def create_account(self):
        return self.infura.create_account()

    def make_transaction(self, **kwargs):
        return self.infura.make_transaction(**kwargs)


class EthplorerInteraction:
    def __init__(self, ethplorer_api_key):
        self.ethplorer_api_key = ethplorer_api_key

    def request(self, method, params, kwargs):
        url = 'https://api.ethplorer.io/'
        if method in ['getAddressInfo']:
            url += 'getAddressInfo/{address}'
        else:
            raise KeyError("Invalid `method` keyword: 'getAddressInfo' is only valid, '{0}' value provided".format(
                method))
        params['apiKey'] = self.ethplorer_api_key

        query = parse.urlencode(params)
        url = '{0}?{1}'.format(url, query)
        url = url.format(**kwargs)
        with request.urlopen(url) as response:
            response_data = json.loads(response.read())

        return response_data

    def balance(self, addresses):

        results = {}

        # """
        params = {}

        for address in addresses:

            response_data = self.request(method='getAddressInfo', params=params, kwargs={'address': address})

            if 'tokens' in response_data.keys():
                results[response_data['address']] = {}
                for i, token in enumerate(response_data['tokens']):
                    # TODO: control source libraries for Decimal
                    results[response_data['address']][response_data['tokens'][i]['tokenInfo']['symbol']] = \
                        Decimal(response_data['tokens'][i]['balance']) / Decimal('10') ** Decimal(
                        response_data['tokens'][i]['tokenInfo']['decimals'])

        return results


class EtherscanInteraction:
    def __init__(self, network, etherscan_api_key):
        self.network = network
        self.etherscan_api_key = etherscan_api_key

    def request(self, params):
        network = {
            'mainnet': 'https://api.etherscan.io/api',
            'goerli': 'https://api-goerli.etherscan.io/api',
            'ropsten': 'https://api-ropsten.etherscan.io/api'
        }
        try:
            url = network[self.network]
        except KeyError:
            raise KeyError("Invalid network name")
        
        query = parse.urlencode(params)
        url = '{0}?{1}'.format(url, query)
        with request.urlopen(url) as response:
            response_data = json.loads(response.read())

        return response_data

    def balance(self, addresses):

        results = {}

        params = {
            'module': 'account',
            'action': 'balancemulti',
            'address': ','.join(addresses),
            'tag': 'latest',
            'apikey': self.etherscan_api_key,
        }

        response_data = self.request(params=params)

        # TODO: control source libraries for Decimal
        for i, account in enumerate(addresses):
            results[account] = {'ETH': Decimal(response_data['result'][i]['balance']) / Decimal('10') ** Decimal('18')}

        return results

    def get_transactions(self, account, sort='desc', raw=True):
        re = tuple()
        params = {
            'module': 'account',
            'action': 'txlist',
            'address': account,
            'startblock': 0,  # check numbers
            'endblock': 99999999,  # TODO: check numbers
            # 'page': 1,
            # 'offset': 10,
            'sort': sort,
            'apikey': self.etherscan_api_key,
        }
        response_data_eth = self.request(params)
        if not raw:
            results_eth = {'tx': [], 'datetime': [], 'sender': [], 'receiver': [], 'value': [],
                           'commission_paid': [], 'currency': []}
            for item in response_data_eth['result']:
                results_eth['tx'].append(item['hash'])
                results_eth['datetime'].append(datetime.datetime.fromtimestamp(int(item['timeStamp'])))
                results_eth['sender'].append(item['from'])
                results_eth['receiver'].append(item['to'])
                # TODO: control source libraries for Decimal
                results_eth['value'].append(Web3.fromWei(number=Decimal(item['value']), unit='ether'))
                results_eth['commission_paid'].append(Web3.fromWei(number=(Decimal(item['gasPrice']) *
                                                                           Decimal(item['gasUsed'])),
                                                                   unit='ether'))
                results_eth['currency'].append('ETH')
            re += (results_eth,)
        else:
            re += (response_data_eth,)
        params = {
            'module': 'account',
            'action': 'tokentx',
            'address': account,
            # &contractaddress=0x9f8f72aa9304c8b593d555f12ef6589cc3a579a2  # we can use this arg to filter by spec token
            'startblock': 0,  # check numbers
            'endblock': 99999999,  # TODO: check numbers
            # 'page': 1,
            # 'offset': 10,
            'sort': sort,
            'apikey': self.etherscan_api_key,
        }
        response_data_erc20 = self.request(params)
        if not raw:
            results_erc20 = {'tx': [], 'datetime': [], 'sender': [], 'receiver': [], 'value': [],
                             'commission_paid': [], 'currency': []}
            for item in response_data_erc20['result']:
                results_erc20['tx'].append(item['hash'])
                results_erc20['datetime'].append(datetime.datetime.fromtimestamp(int(item['timeStamp'])))
                results_erc20['sender'].append(item['from'])
                results_erc20['receiver'].append(item['to'])
                # TODO: control source libraries for Decimal
                results_erc20['value'].append(Decimal(item['value']) / (Decimal('10') ** Decimal(item['tokenDecimal'])))
                results_erc20['commission_paid'].append(Web3.fromWei(number=(Decimal(item['gasPrice']) *
                                                                             Decimal(item['gasUsed'])),
                                                                     unit='ether'))
                results_erc20['currency'].append(item['tokenSymbol'])
            re += (results_erc20,)
        else:
            re += (response_data_erc20,)
        return re


class Actor:
    def __init__(self, blockchain, **kwargs):
        self.blockchain = blockchain
        if self.blockchain == BlockchainType.ETHEREUM:
            self._actor = ActorEthereum(**kwargs)
        elif self.blockchain == BlockchainType.BITCOIN:
            self._actor = ActorBitcoin(**kwargs)
        else:
            raise KeyError("Invalid blockchain type {0} is entered; please, check available ones".format(blockchain))

    def __getattribute__(self, item):
        if item == 'blockchain':
            return super().__getattribute__(item)
        else:
            return super().__getattribute__('_actor').__getattribute__(item)


# TODO: change the behavior so that the address is not autogenerated with the private key;
#  put the current autogeneration to a separate method like 'get_address'    # ??? should it be so ???
class ActorBitcoin:
    def __init__(self, private_key=None, address=None, encryption=None, script_type='p2wpkh', **kwargs):

        if private_key and address:
            if self.is_key_pair(private_key=private_key, address=address):
                self.private_key = private_key
                self._address = address
            else:
                raise ValueError(f"Invalid address {address} or private key ***** provided; both should match each other")
        elif private_key:
            self.private_key = private_key
            # we support only (compressed; p2pkh; base58) and (compressed; p2wpkh; bech32) addresses
            hdkey = HDKey(private_key)
            if script_type == 'p2pkh':
                self._address = hdkey.address(script_type=script_type, encoding='base58')
            elif script_type == 'p2wpkh':
                self._address = hdkey.address(script_type=script_type, encoding='bech32')
            else:
                raise ValueError(
                    "Invalid script_type value {0} provided; check available script types first".format(
                        script_type))
        elif address:
            if self.is_address(address):
                self._address = address
            else:
                raise ValueError(f"Invalid address {address} provided; should be a valid Bitcoin address")

        self.encryption = encryption

    def is_address(self, address):
        if isinstance(address, str):
            if len(address) > 0:
                try:
                    address = Address.parse(address)
                    # only p2pkh / p2wpkh addressed derived from compressed public_key are supported
                    # all other formats (including non-compressed p2pkh / p2sh / p2sh-p2wpkh / p2tr) won't be valid here
                    return any([(address.encoding == 'base58') and (address.script_type == 'p2pkh'),
                                (address.encoding == 'bech32') and (address.script_type == 'p2wpkh')])
                except EncodingError as e:
                    return False
            else:
                return False
        else:
            return False

    def is_key_pair(self, private_key, address):
        try:
            # only p2pkh / p2wpkh addressed derived from compressed public_key are supported
            # all other formats (including non-compressed p2pkh / p2sh / p2sh-p2wpkh / p2tr)
            # might have unexpected behavior here
            address_parsed = Address.parse(address)
            witness_type = address_parsed.witness_type
            encoding = address_parsed.encoding
            script_type = address_parsed.script_type
            hdkey = HDKey(private_key, compressed=True, encoding=encoding, witness_type=witness_type)
            address_derived = hdkey.address(script_type=script_type, encoding=encoding)
            return address_parsed.address == address_derived
        except BKeyError as e:
            return False
        except EncodingError as e:
            return False

    @property
    def address(self):
        return self._address

    @address.setter
    def address(self, value):
        if self.is_address(value):
            self._address = value
        else:
            raise ValueError("Invalid address {0} provided; should be a valid Bitcoin address".format(value))

    def sign_transaction(self, tx):
        raise NotImplementedError("Transactions are signed on make_transaction level")


# TODO: add mnemonic support (see the w3.eth.account docs)
# TODO: add encoding support
# TODO: add importing & exporting features
class ActorEthereum:
    def __init__(self, w3, private_key=None, address=None, encryption=None, **kwargs):
        self._w3 = w3
        self.private_key = private_key
        if private_key:
            self._account = w3.eth.account.from_key(private_key)
            self._address = self._account.address
        else:
            self._account = None
            self._address = None
        if address:
            if not w3.is_checksum_address(address):
                address = self._w3.to_checksum_address(address)
            if self._address:
                if self._address != address:
                    raise ValueError(
                        "Invalid address {0} or private key ***** provided; "
                        "both should match each other".format(address))
            else:
                self._address = address

        self.encryption = encryption

    @property
    def nonce(self):
        return self._w3.eth.get_transaction_count(self.address)

    @property
    def address(self):
        return self._address

    @address.setter
    def address(self, value):
        if self._w3.is_checksum_address(value):
            self._address = value
        else:
            self._address = self._w3.to_checksum_address(value)

    def sign_transaction(self, tx):
        if self.private_key:
            return self._account.sign_transaction(tx)
        else:
            raise Exception("You have to provide a private_key to use this feature")


class InfuraInteraction:
    def __init__(self, w3):
        self.w3 = w3

    # TODO: add mnemonic support (see the w3.eth.account docs)
    def create_account(self):
        private_key = self.w3.eth.account.create().key.hex()
        actor = Actor(blockchain=BlockchainType.ETHEREUM, w3=self.w3, private_key=private_key)
        return actor

    def generate_transaction_data(self, sender, receiver, value=None, currency=None, gas=None):
        tx = {
            'from': sender.address,
            'to': receiver.address,
        }

        if value:
            value = Decimal(value)
            if currency == 'ETH':
                tx['value'] = self.w3.to_wei(value, 'ether')
            else:
                token_contract_address = find_address(name=currency)
                contract = Actor(blockchain=BlockchainType.ETHEREUM, w3=self.w3, private_key=None, address=token_contract_address)
                tx['to'] = contract.address
                tx['data'] = data_constructor(w3=self.w3, receiver_address=receiver.address, amount=value, currency=currency)

        # TODO: improve gas calculations with pre-London and post-London versions
        if gas:
            gas = Decimal(gas)
            tx['gas'] = gas
        else:
            tx['gas'] = self.w3.eth.estimate_gas(tx)

        tx['gasPrice'] = self.w3.eth.gas_price
        tx['nonce'] = sender.nonce

        return tx

    def make_transaction(self, sender, receiver, value=None, currency=None, gas=None, **kwargs):
        tx = self.generate_transaction_data(sender=sender, receiver=receiver, value=value, currency=currency, gas=gas)
        signed_txn = sender.sign_transaction(tx)
        tx_id = self.w3.toHex(self.w3.eth.send_raw_transaction(signed_txn.rawTransaction))
        return tx_id
