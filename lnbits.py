from aiohttp.client import ClientSession
from pylnbits.config import Config
from pylnbits.user_wallet import UserWallet
from pylnbits.lnurl_p import LnurlPay

class LnbitsAPI:
    def __init__(self, config_file):
        self.config = Config(config_file=config_file)
        self.session = ClientSession()

    async def get_wallet_details(self):
        async with self.session:
            uw = UserWallet(self.config, self.session)
            userwallet = await uw.get_wallet_details()
            return userwallet

    async def get_wallet_balance(self):
        userwallet = await self.get_wallet_details()
        balance = userwallet['balance']
        return balance

    async def create_invoice(self, is_fixed, amount, description, webhook):
        async with self.session:
            uw = UserWallet(self.config, self.session)
            res = await uw.create_invoice(is_fixed, amount, description, webhook)
            return res

    async def list_paylinks(self):
        async with self.session:
            lw = LnurlPay(self.config, self.session)
            links = await lw.list_paylinks()
            return links

    async def get_paylink(self, pay_id):
        async with self.session:
            lw = LnurlPay(self.config, self.session)
            getlink = await lw.get_paylink(pay_id=pay_id)
            return getlink

    async def create_paylink(self, body):
        async with self.session:
            lw = LnurlPay(self.config, self.session)
            newlink = await lw.create_paylink(body=body)
            return newlink

    async def update_paylink(self, pay_id, body):
        async with self.session:
            lw = LnurlPay(self.config, self.session)
            update_result = await lw.update_paylink(pay_id=pay_id, body=body)
            return update_result

    async def decode_invoice(self, invoice):
        async with self.session:
            uw = UserWallet(self.config, self.session)
            try:
                decoded_invoice = await uw.get_decoded(invoice)
                # print('Decoded invoice (LnbitsAPI):', decoded_invoice)
                return decoded_invoice
            except Exception as e:
                print('Error while decoding invoice (LnbitsAPI):', e)
                return None

    async def check_invoice(self, payment_hash):
        async with self.session:
            uw = UserWallet(self.config, self.session)
            try:
                invoice_status = await uw.check_invoice(payment_hash)
                return invoice_status
            except Exception as e:
                print('Error while checking invoice (LnbitsAPI):', e)
                return None

    async def delete_paylink(self, pay_id):
        async with self.session:
            lw = LnurlPay(self.config, self.session)
            delete_result = await lw.delete_paylink(pay_id=pay_id)
            return delete_result

    async def close(self):
        await self.session.close()