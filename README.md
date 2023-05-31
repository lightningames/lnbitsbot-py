# lnbitsbot-py

A starter template for running bots based off of lnbits.com or your own install.

Basic outline with lnbits as the backend for a python TG bot:

- create a wallet on lnbits through User Manager
- create and send invoices
- pay lightning invoices
- link user to lnbits web interface
- Use the [pylnbits sdk](github.com/lightningames/pylnbits)


Getting Started

```
git clone https://github.com/lightningames/lnbitsbot-py
cd lnbitsbot-py
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

See .env.example for the specific ID, Hash, and Token you will need to create your own bot.
