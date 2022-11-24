#
import json
import datetime

#
import numpy
import pandas
from web3 import Web3
from urllib import parse, request
from cryptos import Bitcoin, random_key
from eth_account.messages import encode_defunct

#
from oaiv.tools.utils import format_provider, format_w3, data_constructor, check_precision
from oaiv.tools.address import find_address
from oaiv.constants import BlockchainType


class InteractionFunctionality:
    def __init__(self, bitcoin_kwg, ethereum_kwg):
        self.bitcoin_interaction = InteractionFunctionalityBitcoin(**bitcoin_kwg)
        self.ethereum_interaction = InteractionFunctionalityEthereum(**ethereum_kwg)

    def is_address(self, address, blockchain):
        if blockchain == BlockchainType.ETHEREUM:
            return self.ethereum_interaction.is_address(address=address)
        elif blockchain == BlockchainType.BITCOIN:
            return self.bitcoin_interaction.is_address(address=address)
        else:
            raise ValueError("Invalid blockchain type provided, "
                             "should be BlockchainType.ETHEREUM or BlockchainType.BITCOIN; you provided".format(
                blockchain))

    def is_key_pair(self, blockchain, private_key, address):
        if blockchain == BlockchainType.ETHEREUM:
            return self.ethereum_interaction.is_key_pair(private_key=private_key, address=address)
        elif blockchain == BlockchainType.BITCOIN:
            return self.bitcoin_interaction.is_key_pair(private_key=private_key, address=address)
        else:
            raise ValueError("Invalid blockchain type provided, "
                             "should be BlockchainType.ETHEREUM or BlockchainType.BITCOIN; you provided".format(
                blockchain))

    def balance(self, addresses, blockchain):
        if blockchain == BlockchainType.ETHEREUM:
            return self.ethereum_interaction.balance(addresses=addresses)
        elif blockchain == BlockchainType.BITCOIN:
            return self.bitcoin_interaction.balance(addresses=addresses)
        else:
            raise ValueError("Invalid blockchain type provided, "
                             "should be BlockchainType.ETHEREUM or BlockchainType.BITCOIN; you provided".format(
                blockchain))

    def get_transactions(self, blockchain, **kwargs):
        if blockchain == BlockchainType.ETHEREUM:
            return self.ethereum_interaction.get_transactions(**kwargs)
        elif blockchain == BlockchainType.BITCOIN:
            return self.bitcoin_interaction.get_transactions(**kwargs)
        else:
            raise ValueError("Invalid blockchain type provided, "
                             "should be BlockchainType.ETHEREUM or BlockchainType.BITCOIN; you provided".format(
                blockchain))

    def create_account(self, blockchain):
        if blockchain == BlockchainType.ETHEREUM:
            return self.ethereum_interaction.create_account()
        elif blockchain == BlockchainType.BITCOIN:
            return self.bitcoin_interaction.create_account()
        else:
            raise ValueError("Invalid blockchain type provided, "
                             "should be BlockchainType.ETHEREUM or BlockchainType.BITCOIN; you provided".format(
                blockchain))

    def make_transaction(self, blockchain, **kwargs):
        if blockchain == BlockchainType.ETHEREUM:
            return self.ethereum_interaction.make_transaction(**kwargs)
        elif blockchain == BlockchainType.BITCOIN:
            return self.bitcoin_interaction.make_transaction(**kwargs)
        else:
            raise ValueError("Invalid blockchain type provided, "
                             "should be BlockchainType.ETHEREUM or BlockchainType.BITCOIN; you provided".format(
                blockchain))


class InteractionFunctionalityBitcoin:
    def __init__(self):
        self.utility = Bitcoin(testnet=False)

    def is_address(self, address):
        if isinstance(address, str):
            if len(address) > 0:
                return self.utility.is_address(addr=address)
            else:
                return False
        else:
            return False

    def is_key_pair(self, private_key, address):
        # TODO: this should be reworked to a correct message signing-recovering procedure
        #  (after the base btc package switch)
        try:
            result = any([address == self.utility.privtoaddr(privkey=private_key),
                          self.utility.is_segwit(priv=private_key, addr=address)])
            return result
        except Exception as e:
            print(e)
            return False

    def balance(self, addresses):
        result = {}
        for address in addresses:
            unspent = self.utility.unspent(address)
            result[address] = {}
            result[address]['BTC'] = sum([x['value'] / 100_000_000 for x in unspent])
        return result

    def get_transactions(self, account, sort='desc', raw=True):

        request_results = self.utility.history(account)

        if not raw:
            results = {'tx': [], 'datetime': [], 'sender': [], 'receiver': [], 'value': [], 'commission_paid': [], 'currency': []}

            for tx in request_results['txs']:

                for j in range(len(tx['out'])):
                    results['tx'].append(tx['hash'])
                    results['datetime'].append(datetime.datetime.fromtimestamp(tx['time']))
                    inputs_addresses = [tx['inputs'][i]['prev_out']['addr'] for i in range(len(tx['inputs']))]
                    if numpy.unique(inputs_addresses).shape[0] > 1:
                        results['sender'].append('{{{0}}}'.format(
                            ';'.join([tx['inputs'][i]['prev_out']['addr'] for i in range(len(tx['inputs']))])))
                    else:
                        results['sender'].append(tx['inputs'][0]['prev_out']['addr'])
                    results['receiver'].append(tx['out'][j]['addr'])
                    results['value'].append(tx['out'][j]['value'])
                    results['commission_paid'].append(tx['fee'])
                    results['currency'].append('BTC')

            results = pandas.DataFrame(results)
            """
            results = results.groupby(by=[
                'tx', 'datetime', 'sender', 'receiver', 'commission_paid', 'currency'])[['value']].sum()
            results = results.reset_index()
            """
            results['value'] = results['value'] / 100_000_000
            results['commission_paid'] = results['commission_paid'] / 100_000_000
            results = results.loc[results['sender'] != results['receiver']].copy().reset_index(drop=True)
            results = results.sort_values(by='datetime', ascending=(sort == 'asc'))
            results = results.to_dict()
            re = (results, {})
        else:
            re = (request_results, {})
        return re

    def create_account(self):
        private_key = random_key()
        """
        actor = ActorBitcoin(private_key=private_key)
        """
        actor = Actor(blockchain=BlockchainType.BITCOIN, private_key=private_key)
        return actor

    def make_transaction(self, sender, receiver, value=None, gas=None, **kwargs):

        value = int(value * 100_000_000)

        if gas:
            result = self.utility.send(privkey=sender.private_key, to=receiver.address, addr=sender.address,
                                       value=value, fee=gas)
        else:
            result = self.utility.send(privkey=sender.private_key, to=receiver.address, addr=sender.address,
                                       value=value)

        tx_id = result['data']['txid']

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
                    # TODO: fix the Decimal issue
                    results[response_data['address']][response_data['tokens'][i]['tokenInfo']['symbol']] = int(
                        response_data['tokens'][i]['balance']) / 10 ** int(
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

        # TODO: fix the Decimal issue
        for i, account in enumerate(addresses):
            results[account] = {'ETH': int(response_data['result'][i]['balance']) / 10 ** 18}

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
            results_eth = {'tx': [], 'datetime': [], 'sender': [], 'receiver': [], 'value': [], 'commission_paid': [], 'currency': []}
            for item in response_data_eth['result']:
                results_eth['tx'].append(item['hash'])
                results_eth['datetime'].append(datetime.datetime.fromtimestamp(int(item['timeStamp'])))
                results_eth['sender'].append(item['from'])
                results_eth['receiver'].append(item['to'])
                results_eth['value'].append(float(Web3.fromWei(number=int(item['value']), unit='ether')))
                results_eth['commission_paid'].append(float(Web3.fromWei(number=(int(item['gasPrice']) * int(item['gasUsed'])), unit='ether')))
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
        # TODO: fix the Decimal issue
        if not raw:
            results_erc20 = {'tx': [], 'datetime': [], 'sender': [], 'receiver': [], 'value': [], 'commission_paid': [], 'currency': []}
            for item in response_data_erc20['result']:
                results_erc20['tx'].append(item['hash'])
                results_erc20['datetime'].append(datetime.datetime.fromtimestamp(int(item['timeStamp'])))
                results_erc20['sender'].append(item['from'])
                results_erc20['receiver'].append(item['to'])
                results_erc20['value'].append(int(item['value']) / (10 ** int(item['tokenDecimal'])))
                results_erc20['commission_paid'].append(float(Web3.fromWei(number=(int(item['gasPrice']) * int(item['gasUsed'])), unit='ether')))
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
    """
    def __getattr__(self, item):
        if item == 'blockchain':
            return self.blockchain
        else:
            return self._actor.__getattribute__(item)
    """
    # https://stackoverflow.com/questions/3278077/difference-between-getattr-and-getattribute
    def __getattribute__(self, item):
        if item == 'blockchain':
            return super().__getattribute__(item)
        else:
            return super().__getattribute__('_actor').__getattribute__(item)


# TODO: change the behavior so that the address is not autogenerated with the private key;
#  put the current autogeneration to a separate method like 'get_address'
class ActorBitcoin:
    def __init__(self, private_key=None, address=None, encryption=None, address_type='p2pkh', **kwargs):
        self._b = Bitcoin(testnet=False)
        self.private_key = private_key

        if private_key:
            if address_type == 'p2pkh':
                self._address = self._b.privtoaddr(self.private_key)
            elif address_type == 'p2sh':
                self._address = self._b.privtop2w(self.private_key)
            else:
                raise ValueError(
                    "Invalid address_type value {0} provided; check available address types first".format(
                        address_type))
        else:
            self._address = None

        if address:
            if self._b.is_address(address):
                if self._address:
                    if self._address != address:
                        raise ValueError(
                            "Invalid address {0} or private key ***** provided; both should match each other".format(address))
                else:
                    self._address = address
            else:
                raise ValueError("Invalid address {0} provided; should be a valid Bitcoin address".format(address))

        self.encryption = encryption

    @property
    def address(self):
        return self._address

    @address.setter
    def address(self, value):
        if self._b.is_address(value):
            self._address = value
        else:
            raise ValueError("Invalid address {0} provided; should be a valid Bitcoin address".format(value))

    def sign_transaction(self, tx):
        if self.private_key:
            return self._b.signall(tx, self.private_key)
        else:
            raise Exception("You have to provide a private_key to use this feature")


# TODO: add mnemonic support (see the w3.eth.account docs)
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
            if not w3.isChecksumAddress(address):
                address = self._w3.toChecksumAddress(address)
            if self._address:
                if self._address != address:
                    raise ValueError(
                        "Invalid address {0} or private key ***** provided; both should match each other".format(address))
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
        if self._w3.isChecksumAddress(value):
            self._address = value
        else:
            self._address = self._w3.toChecksumAddress(value)

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
        """
        actor = ActorEthereum(w3=self.w3, private_key=private_key)
        """
        actor = Actor(blockchain=BlockchainType.ETHEREUM, w3=self.w3, private_key=private_key)
        return actor

    def generate_transaction_data(self, sender, receiver, value=None, currency=None, gas=None):
        tx = {
            'from': sender.address,
            'to': receiver.address,
        }

        if value:
            if currency == 'ETH':
                tx['value'] = self.w3.toWei(value, 'ether')
            else:
                token_contract_address = find_address(name=currency)
                """
                contract = ActorEthereum(w3=self.w3, private_key=None, address=token_contract_address)
                """
                contract = Actor(blockchain=BlockchainType.ETHEREUM,
                                 w3=self.w3, private_key=None, address=token_contract_address)
                tx['to'] = contract.address
                tx['data'] = data_constructor(
                    receiver_address=receiver.address,
                    amount=value,
                    currency=currency
                )

        # TODO: improve gas calculations with pre-London and post-London versions
        if gas:
            tx['gas'] = gas
        else:
            tx['gas'] = self.w3.eth.estimate_gas(tx)

        tx['gasPrice'] = self.w3.eth.gasPrice
        tx['nonce'] = sender.nonce

        return tx

    def make_transaction(self, sender, receiver, value=None, currency=None, gas=None, **kwargs):
        tx = self.generate_transaction_data(
            sender=sender,
            receiver=receiver,
            value=value,
            currency=currency,
            gas=gas
        )

        signed_txn = sender.sign_transaction(tx)

        tx_id = self.w3.toHex(self.w3.eth.sendRawTransaction(signed_txn.rawTransaction))

        return tx_id
