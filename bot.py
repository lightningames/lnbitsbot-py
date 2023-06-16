from telethon import TelegramClient, events
from telethon.sync import Button
from telethon.tl.custom import Conversation
from lnbits import LnbitsAPI
from PIL import Image
import asyncio
import qrcode
import io
import json
from dotenv import load_dotenv
import os


load_dotenv()

api_id = os.environ.get('TELEGRAM_API_ID')  # telegram dev api
api_hash = os.environ.get('TELEGRAM_API_HASH')  # telegram dev api
bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')  # botfather token


client = TelegramClient('bot', api_id, api_hash).start(bot_token=bot_token)
lnbits_api = LnbitsAPI(config_file="config.yml")

# Tracks conversation status
ongoing_conversations = {}

class ConversationCanceled(Exception):
    pass


async def get_balance_button(conv):
    print("get_balance_button: started")
    balance = await lnbits_api.get_wallet_balance()
    await conv.send_message(f'<b>Your wallet balance is:</b> {balance} sats', parse_mode="html")
    print("get_balance_button: finished")


async def get_wallet_details_button(conv):
    print("get_wallet_details_button: started")
    wallet_details = await lnbits_api.get_wallet_details()

    wallet_name = wallet_details['name']
    wallet_balance = wallet_details['balance']

    response = (
        f"<b>Wallet Details:</b>\n"
        f"<i>Name:</i> {wallet_name}\n"
        f"<i>Balance:</i> {wallet_balance}\n"
    )

    await conv.send_message(response, parse_mode='html')
    print("get_wallet_details_button: finished")


async def create_invoice_button(conv):
    # Ask for amount
    print("check_invoice_button: started")
    await conv.send_message("<b>Let's create an invoice! First, please enter the amount (in SATs):</b>", parse_mode="html")
    while True:
        try:
            amount = int((await conv.get_response()).text)
            break
        except ValueError:
            await conv.send_message("<b>Please enter a valid numerical value for the amount.</b>", parse_mode="html")

    # Ask for memo
    await conv.send_message("<b>Great! Now, please enter a memo for the invoice:</b>", parse_mode="html")
    memo = (await conv.get_response()).text

    # Create invoice
    invoice = await lnbits_api.create_invoice(False, amount, memo, "http://google.com")
    payment_request = invoice['payment_request']

    # Generate QR code
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H)
    qr.add_data(payment_request)
    qr.make(fit=True)
    img = qr.make_image(fill_color="orange", back_color="white")

    # Load Bitcoin logo
    logo_path = "btc-qrcode-pic.png"
    logo = Image.open(logo_path).convert("RGBA")

    # Calculate logo size and position
    qr_width, qr_height = img.size
    logo_width, logo_height = logo.size
    scale_factor = min(qr_width // 3, qr_height // 3, logo_width, logo_height)
    new_logo_width = logo_width * scale_factor // logo_width
    new_logo_height = logo_height * scale_factor // logo_height
    logo = logo.resize((new_logo_width, new_logo_height))
    logo_pos = ((qr_width - new_logo_width) // 2, (qr_height - new_logo_height) // 2)

    # Overlay logo on QR code
    img.paste(logo, logo_pos, logo)

    # Save QR code to BytesIO
    img_data = io.BytesIO()
    img.save(img_data, format='PNG')
    img_data.seek(0)

    # Send invoice details and QR code
    await conv.send_message(f'<b>Invoice for {amount} sats:</b>', parse_mode="html")
    await conv.send_file(file=img_data)
    await conv.send_message(payment_request)
    print("check_invoice_button: finished")


async def decode_invoice_button(conv):
    print("decode_invoice_button: started")
    # Ask for invoice
    await conv.send_message("<b>Please provide an invoice to decode:</b>", parse_mode="html")
    invoice = (await conv.get_response()).text

    # Decode invoice
    decoded_invoice = await lnbits_api.decode_invoice(invoice)

    # Create a new dictionary with only the first 7 key-value pairs
    limited_decoded_invoice = {k: decoded_invoice[k] for k in list(decoded_invoice.keys())[:7]}

    # Convert the limited decoded invoice dictionary to a string
    limited_decoded_invoice_str = json.dumps(limited_decoded_invoice, indent=2)

    # Split the decoded invoice message into chunks
    message_chunks = split_message_into_chunks(f'<b>Decoded invoice:</b>\n<pre>{limited_decoded_invoice_str}</pre>',
                                               4096)

    # Send each chunk separately
    for chunk in message_chunks:
        await conv.send_message(chunk, parse_mode="html")
    print("decode_invoice_button: finished")


async def pay_invoice_button(conv, invoice):
    print("pay_invoice_button: started")
    payment_result = await lnbits_api.pay_invoice(invoice)
    if payment_result is None:
        await conv.send_message('<b>Payment successful!</b>', parse_mode="html")
    else:
        error_message = payment_result.get('detail', 'Unknown error')
        await conv.send_message(f'<b>Payment failed:</b> {error_message}', parse_mode="html")
    print("pay_invoice_button: finished")


async def check_invoice_button(conv):
    # Ask for payment hash
    print("check_invoice_button: started")
    await conv.send_message("<b>Please provide a payment hash to check:</b>", parse_mode="html")
    payment_hash = (await conv.get_response()).text

    # Check invoice status
    invoice_status = await lnbits_api.check_invoice(payment_hash)

    # Send invoice status
    await conv.send_message(f'<b>Invoice status:</b>\n<pre>{invoice_status}</pre>', parse_mode="html")
    print("check_invoice_button: finished")


async def create_paylink_button(conv):
    print("create_paylink_button: started")
    # Ask for description
    await conv.send_message(
        "<b>Let's create your paylink! I'll need some information to get started. First, what's a good description for this paylink?</b>",
        parse_mode="html")
    description = (await conv.get_response()).text

    # Ask for amount
    await conv.send_message("<b>Awesome! Next, let's set the amount (in SATs)</b>", parse_mode="html")
    while True:
        try:
            amount = int((await conv.get_response()).text)
            break
        except ValueError:
            await conv.send_message("<b>Please enter a valid numerical value for the amount.</b>", parse_mode="html")

    # Currently using min/max range as 'amount' to mirror lnbits UI

    # Ask for minimum value
    # await conv.send_message("<b>Great! Now let's set a minimum value...</b>", parse_mode="html")
    # min_amount = int((await conv.get_response()).text)
    min_amount = amount

    # Ask for maximum value
    # await conv.send_message("<b>...and a maximum value!</b>", parse_mode="html")
    # max_amount = int((await conv.get_response()).text)
    max_amount = amount

    # Ask for comment chars
    await conv.send_message("<b>Finally, let's set the comment chars</b>", parse_mode="html")
    while True:
        try:
            comment_chars = int((await conv.get_response()).text)
            break
        except ValueError:
            await conv.send_message("<b>Please enter a valid numerical value for the comment chars.</b>", parse_mode="html")

    # Create paylink
    body = {
        "description": description,
        "amount": amount,
        "max": max_amount,
        "min": min_amount,
        "comment_chars": comment_chars
    }

    try:
        new_paylink = await lnbits_api.create_paylink(body)
        lnurl = new_paylink['lnurl']
        await conv.send_message(f"<b>Great! Here's your lightning paylink:</b>\n{lnurl}", parse_mode="html")
    except Exception as e:
        await conv.send_message(f"<b>Error creating PayLink: {e}</b>", parse_mode="html")
    print("create_paylink_button: finished")


@client.on(events.NewMessage(pattern='/lightning'))
async def lightning_menu(event):
    buttons = [
        [Button.inline("💰 Create Invoice (/create_invoice)", b"create_invoice")],
        [Button.inline("💼 Get Balance (/get_balance)", b"get_balance")],
        [Button.inline("📝 Get Wallet Details (/get_wallet_details)", b"get_wallet_details")],
        [Button.inline("🔍 Decode Invoice (/decode_invoice)", b"decode_invoice")],
        [Button.inline("💸 Pay Invoice (/pay_invoice)", b"pay_invoice")],
        [Button.inline("🔖 Check Invoice (/check_invoice)", b"check_invoice")],
        [Button.inline("🔗 Create LNURLp (/create_paylink)", b"create_paylink")],
    ]
    await event.respond("<b>Welcome to the lnbits telegram bot! Choose a command or type the command (i.e. /create_invoice) to get started</b>", buttons=buttons, parse_mode="html")


@client.on(events.CallbackQuery)
async def handle_callback_query(event):
    data = event.data
    chat_id = event.chat_id

    # Cancel ongoing conversation if any
    if chat_id in ongoing_conversations:
        ongoing_conversations[chat_id].cancel()
        del ongoing_conversations[chat_id]

    # Answer the callback query before starting a new conversation
    await event.answer()

    async def handle_conversation():
        try:
            async with client.conversation(chat_id, timeout=5) as conv:
                ongoing_conversations[chat_id] = conv
                print(f"New conversation started with chat_id {chat_id}.")
                if data == b"create_invoice":
                    await create_invoice_button(conv)
                elif data == b"get_balance":
                    await get_balance_button(conv)
                elif data == b"get_wallet_details":
                    await get_wallet_details_button(conv)
                elif data == b"decode_invoice":
                    await decode_invoice_button(conv)
                elif data == b"pay_invoice":
                    await conv.send_message("<b>Please provide an invoice to pay:</b>", parse_mode="html")
                    invoice = (await conv.get_response()).text
                    await pay_invoice_button(conv, invoice)
                elif data == b"check_invoice":
                    await check_invoice_button(conv)
                elif data == b"create_paylink":
                    await create_paylink_button(conv)
                else:
                    await event.answer("Unknown action")
        except asyncio.TimeoutError:
            await event.respond("<b>Conversation timed out. Please select an option from the menu, or type /lightning to see the menu again.</b>", parse_mode="html")
        except ConversationCanceled:
            pass
        except asyncio.CancelledError:
            pass
        finally:
            if chat_id in ongoing_conversations:
                del ongoing_conversations[chat_id]

    # Start a new conversation with a small delay
    await asyncio.sleep(0.5)
    asyncio.create_task(handle_conversation())

def split_message_into_chunks(message, max_length=4096):
    return [message[i:i + max_length] for i in range(0, len(message), max_length)]

### INDIVIDUAL EVENT HANDLERS ###

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
    try:
        async with client.conversation(event.chat_id, timeout=5) as conv:
            # Ask for amount
            await conv.send_message("<b>Let's create an invoice! First, please enter the amount (in SATs):</b>", parse_mode="html")
            while True:
                try:
                    amount = int((await conv.get_response()).text)
                    break
                except ValueError:
                    await conv.send_message("<b>Please enter a valid numerical value for the amount.</b>", parse_mode="html")

            # Ask for memo
            await conv.send_message("<b>Great! Now, please enter a memo for the invoice:</b>", parse_mode="html")
            memo = (await conv.get_response()).text

            # Create invoice
            invoice = await lnbits_api.create_invoice(False, amount, memo, "http://google.com")
            payment_request = invoice['payment_request']

            # Generate QR code
            qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H)
            qr.add_data(payment_request)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")

            # Load Bitcoin logo
            logo_path = "btc-qrcode-pic.png"
            logo = Image.open(logo_path).convert("RGBA")

            # Calculate logo size and position
            qr_width, qr_height = img.size
            logo_width, logo_height = logo.size
            scale_factor = min(qr_width // 3, qr_height // 3, logo_width, logo_height)
            new_logo_width = logo_width * scale_factor // logo_width
            new_logo_height = logo_height * scale_factor // logo_height
            logo = logo.resize((new_logo_width, new_logo_height))
            logo_pos = ((qr_width - new_logo_width) // 2, (qr_height - new_logo_height) // 2)

            # Overlay logo on QR code
            img.paste(logo, logo_pos, logo)

            # Save QR code to BytesIO
            img_data = io.BytesIO()
            img.save(img_data, format='PNG')
            img_data.seek(0)

            # Send invoice details and QR code
            await conv.send_message(f'<b>Invoice for {amount} sats:</b>', parse_mode="html")
            await conv.send_file(file=img_data)
            await conv.send_message(payment_request)

    except asyncio.TimeoutError:
        await event.respond("<b>Conversation timed out. Please select an option from the menu, or type /lightning to see the menu again.</b>", parse_mode="html")
    raise events.StopPropagation

# Decode Invoice

def split_message_into_chunks(message, max_length=4096):
    return [message[i:i + max_length] for i in range(0, len(message), max_length)]

@client.on(events.NewMessage(pattern='/decode_invoice'))
async def decode_invoice(event):
    try:
        async with client.conversation(event.chat_id, timeout=5) as conv:
            # Ask for invoice
            await conv.send_message("<b>Please provide an invoice to decode:</b>", parse_mode="html")
            invoice = (await conv.get_response()).text

            # Decode invoice
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
                await conv.send_message(chunk, parse_mode="html")

    except asyncio.TimeoutError:
        await event.respond("<b>Conversation timed out. Please select an option from the menu, or type /lightning to see the menu again.</b>", parse_mode="html")
    raise events.StopPropagation

# Pay Invoice

@client.on(events.NewMessage(pattern='/pay_invoice'))
async def pay_invoice(event):
    try:
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
    except asyncio.TimeoutError:
        await event.respond("<b>Conversation timed out. Please select an option from the menu, or type /lightning to see the menu again.</b>", parse_mode="html")
    raise events.StopPropagation

# Check Invoice

@client.on(events.NewMessage(pattern='/check_invoice'))
async def check_invoice(event):
    try:
        async with client.conversation(event.chat_id, timeout=5) as conv:
            # Ask for payment hash
            await conv.send_message("<b>Please provide a payment hash to check:</b>", parse_mode="html")
            payment_hash = (await conv.get_response()).text

            # Check invoice status
            invoice_status = await lnbits_api.check_invoice(payment_hash)

            # Send invoice status
            await conv.send_message(f'<b>Invoice status:</b>\n<pre>{invoice_status}</pre>', parse_mode="html")

    except asyncio.TimeoutError:
        await event.respond("<b>Conversation timed out. Please select an option from the menu, or type /lightning to see the menu again.</b>", parse_mode="html")
    raise events.StopPropagation

# Create paylink

@client.on(events.NewMessage(pattern='/create_paylink'))
async def create_paylink(event):
    try:
        async with client.conversation(event.chat_id, timeout=5) as conv:
            # Ask for description
            await conv.send_message("<b>Let's create your paylink! I'll need some information to get started. First, what's a good description for this paylink?</b>", parse_mode="html")
            description = (await conv.get_response()).text

            # Ask for amount
            await conv.send_message("<b>Awesome! Next, let's set the amount (in SATs)</b>", parse_mode="html")
            while True:
                try:
                    amount = int((await conv.get_response()).text)
                    break
                except ValueError:
                    await conv.send_message("<b>Please enter a valid numerical value for the amount.</b>", parse_mode="html")

            # Min and Max Values currently same as amount for convience.
            # Ask for minimum value (No Longer In Use)
            # await conv.send_message("<b>Great! Now let's set a minimum value...</b>", parse_mode="html")
            # min_amount = int((await conv.get_response()).text)
            min_amount = amount

            # Ask for maximum value (No Longer In Use)
            # await conv.send_message("<b>...and a maximum value!</b>", parse_mode="html")
            # max_amount = int((await conv.get_response()).text)
            max_amount = amount

            # Ask for comment chars
            await conv.send_message("<b>Finally, let's set the number of comment chars</b>", parse_mode="html")
            while True:
                try:
                    comment_chars = int((await conv.get_response()).text)
                    break
                except ValueError:
                    await conv.send_message("<b>Please enter a valid numerical value for the comment chars.</b>", parse_mode="html")

            # Create paylink
            body = {
                "description": description,
                "amount": amount,
                "max": max_amount,
                "min": min_amount,
                "comment_chars": comment_chars
            }

            try:
                new_paylink = await lnbits_api.create_paylink(body)
                lnurl = new_paylink['lnurl']
                await conv.send_message(f"<b>Great! Here's your lightning paylink:</b>\n{lnurl}", parse_mode="html")
            except Exception as e:
                await conv.send_message(f"<b>Error creating PayLink: {e}</b>", parse_mode="html")

    except asyncio.TimeoutError:
        await event.respond("<b>Conversation timed out. Please select an option from the menu, or type /lightning to see the menu again.</b>", parse_mode="html")
    raise events.StopPropagation


async def main():
    await client.start(bot_token=bot_token)
    print('(Press Ctrl+C to stop)')
    try:
        await client.run_until_disconnected()
    finally:
        await lnbits_api.close()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())