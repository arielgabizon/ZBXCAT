# ZBXCAT

A work-in-progress for Zcash Bitcoin Cross-Chain Atomic Transactions

Contains basic scripts we're still testing in regtest mode on both networks. This may all be refactored as we go.

Bitcoin scripts use the rpc proxy code in python-bitcoinlib, and Zcash script will use python-zcashlib (a Zcash fork of python-bitcoinlib).

## Setup

To successfully run this, you'll need python3, the dependencies installed, and a bitcoin daemon running in regtest mode.

To install python3 in a virtualenv, run this command from the top level of the directory:
```
virtualenv -p python3 venv
source venv/bin/activate
```

Use pip to install these two repositoires
https://github.com/arielgabizon/python-bitcoinlib
https://github.com/arielgabizon/python-zcashlib

[//]: <> (To install dependencies, run:)
[//]: <>  (```)
[//]: <> (pip install -r requirements.txt)
[//]: <> (```)

## Run Zcash and Bitcoin daemons locally

To test, run a Zcash daemon and bitcoin daemon in regtest mode. You may have to change the port one of them runs on, for example with the flag `-port=18445`.

To run a bitcoin daemon in regtest mode, with the ability to inspect transactions outside your wallet (useful for testing purposes), use the command
```
bitcoind -regtest -txindex=1 -daemon -port=18445
```

Be sure to run a Zcash daemon in regtest mode.
```
zcashd -regtest -txindex=1 --daemon
```

## XCAT CLI interface

All relevant functions are in api.py.
We call the two participating parties a seller and buyer.
We somewhat arbitraily call the party starting the protocol the seller.

Initially the seller makes sure the init.json file contains the addresses of him and the buyer.
Then he runs seller.init(), e.g. by running 
```
python -c 'import api;api.seller_init()'
```
Then he sends the init.json file to the seller,
which puts the file in her ZBXCAR directory.
She the runs
buyer.init()
She notifies the seller she has done so,
and he runs seller.fund().

Then seller runs buyer.fund().

Then buyer runs seller.redeem().

And seller runs buyer.redeem()
