from telethon import TelegramClient, events
from telethon.sync import Button
from lnbits import LnbitsAPI
import asyncio
import qrcode
import io
import json

api_id = '' #telegram dev api
api_hash = '' #telegram dev api
bot_token = '' #botfather token

client = TelegramClient('bot', api_id, api_hash).start(bot_token=bot_token)
lnbits_api = LnbitsAPI(config_file="config.yml")

# Get Balance

@client.on(events.NewMessage(pattern='/get_balance'))
async def get_balance(event):
    balance = await lnbits_api.get_wallet_balance()
    await event.respond(f'<b>Your wallet balance is:</b> {balance} sats', parse_mode="html")
    raise events.StopPropagation

@client.on(events.NewMessage(pattern='/get_wallet_details'))
async def get_wallet_details(event):
    wallet_details = await lnbits_api.get_wallet_details()

    # if not wallet_details or 'id' not in wallet_details:
    #     await event.respond('Unable to retrieve wallet details.')
    #     return

    # wallet_id = wallet_details['id']
    wallet_name = wallet_details['name']
    wallet_balance = wallet_details['balance']
    # wallet_admin_key = wallet_details['adminkey']
    # wallet_read_key = wallet_details['readkey']

    response = (
        f"<b>Wallet Details:</b>\n"
        # f"ID: {wallet_id}\n"
        f"<i>Name:</i> {wallet_name}\n"
        f"<i>Balance:</i> {wallet_balance}\n"
        # f"Admin Key: {wallet_admin_key}\n"
        # f"Read Key: {wallet_read_key}"
    )

    await event.respond(response, parse_mode='html')
    raise events.StopPropagation

# Create Invoice

@client.on(events.NewMessage(pattern='/create_invoice'))
async def create_invoice(event):
    amount = int(event.message.text.split()[1])
    invoice = await lnbits_api.create_invoice(False, amount, "testcreatetwo", "http://google.com")
    payment_request = invoice['payment_request']

    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H)
    qr.add_data(payment_request)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img_data = io.BytesIO()
    img.save(img_data, format='PNG')
    img_data.seek(0)
    await event.respond(f'<b>Invoice for {amount} sats:</b>', parse_mode="html")
    await event.respond(file=img_data)

    # payment_request as a string
    await event.respond(payment_request)

    raise events.StopPropagation

# Decode Invoice

def split_message_into_chunks(message, max_length=4096):
    return [message[i:i + max_length] for i in range(0, len(message), max_length)]

@client.on(events.NewMessage(pattern='/decode_invoice'))
async def decode_invoice(event):
    message_parts = event.message.text.split()
    if len(message_parts) < 2:
        await event.respond('<b>Please provide an invoice to decode.</b>', parse_mode="html")
        return

    invoice = message_parts[1]
    decoded_invoice = await lnbits_api.decode_invoice(invoice)

    # Create a new dictionary with only the first 7 key-value pairs
    # pair 8 is a MASSIVE array of arrays...
    limited_decoded_invoice = {k: decoded_invoice[k] for k in list(decoded_invoice.keys())[:7]}

    # Convert the limited decoded invoice dictionary to a string
    limited_decoded_invoice_str = json.dumps(limited_decoded_invoice, indent=2)

    # Split the decoded invoice message into chunks
    message_chunks = split_message_into_chunks(f'<b>Decoded invoice:</b>\n<pre>{limited_decoded_invoice_str}</pre>', 4096)

    # Send each chunk separately
    for chunk in message_chunks:
        await event.respond(chunk, parse_mode="html")

    raise events.StopPropagation

# Pay Invoice

@client.on(events.NewMessage(pattern='/pay_invoice'))
async def pay_invoice(event):
    message_parts = event.message.text.split()
    if len(message_parts) < 2:
        await event.respond('<b>Please provide an invoice to pay.</b>', parse_mode="html")
        return

    invoice = message_parts[1]
    payment_result = await lnbits_api.pay_invoice(invoice)
    if payment_result is None:
        await event.respond('<b>Payment successful!</b>', parse_mode="html")
    else:
        await event.respond(f'<b>Payment failed:</b> {payment_result}', parse_mode="html")
    raise events.StopPropagation

# Check Invoice

@client.on(events.NewMessage(pattern='/check_invoice'))
async def check_invoice(event):
    message_parts = event.message.text.split()
    if len(message_parts) < 2:
        await event.respond('<b>Please provide a payment hash to check.</b>', parse_mode="html")
        return

    payment_hash = message_parts[1]
    invoice_status = await lnbits_api.check_invoice(payment_hash)
    await event.respond(f'<b>Invoice status:</b> {invoice_status}', parse_mode="html")
    raise events.StopPropagation

async def main():
    await client.start(bot_token=bot_token)
    print('(Press Ctrl+C to stop)')
    await client.run_until_disconnected()
    await lnbits_api.close()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())