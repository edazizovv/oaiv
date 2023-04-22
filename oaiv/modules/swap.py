#
from time import time


class Uniswap:
    # TODO: check for Decimal issue applicability
    def __init__(
            self,
            address,
            public_key,
            private_key,
            provider,
            web3,
            router_contract_address,
            quoter_contract_address,
            router_contract,
            quoter_contract,
    ):
        self.address = address
        self.public_key = public_key
        self.private_key = private_key
        self.provider = provider
        self.web3 = web3
        self.router_contract_address = router_contract_address
        self.quoter_contract_address = quoter_contract_address

        self.router = router_contract
        self.quoter = quoter_contract

    @staticmethod
    def _deadline():
        return int(time()) + 10 * 60

    def make_trade_input(
            self,
            input_token_address,
            output_token_address,
            quantity_in_token,
            fee,
            slippage
    ):
        sqrtPriceLimitX96 = 0
        price = self.quoter.functions.quoteExactInputSingle(
                input_token_address,
                output_token_address,
                fee,
                quantity_in_token, 
                sqrtPriceLimitX96
        ).call()
        min_tokens_bought = int(
            (1 - slippage)
            * price
        )

        contract_function = self.router.functions.exactInputSingle(
                    {
                        "tokenIn": input_token_address,
                        "tokenOut": output_token_address,
                        "fee": fee,
                        "recipient": self.address,
                        "deadline": self._deadline(),
                        "amountIn": quantity_in_token,
                        "amountOutMinimum": min_tokens_bought,
                        "sqrtPriceLimitX96": sqrtPriceLimitX96,
                    },
                )

        tx_params = {
            "from": self.public_key,
            "value": quantity_in_token,
            "nonce": self.web3.eth.get_transaction_count(self.address),
        }

        transaction = contract_function.buildTransaction(tx_params)
        # The Uniswap V3 UI uses 20% margin for transactions
        transaction["gas"] = int(self.web3.eth.estimate_gas(transaction) * 1.2)

        signed_txn = self.web3.eth.account.sign_transaction(
            transaction, private_key=self.private_key
        )

        tx_id = self.web3.toHex(self.web3.eth.send_raw_transaction(signed_txn.rawTransaction))

        return tx_id
