#!/usr/bin/env python3

# Based on spend-p2sh-txout.py from python-bitcoinlib.
# Copyright (C) 2017 The Zcash developers

import sys
if sys.version_info.major < 3:
    sys.stderr.write('Sorry, Python 3.x required by this example.\n')
    sys.exit(1)

import zcash
import zcash.rpc
from zcash import SelectParams
from zcash.core import b2x, lx, x, b2lx, COIN, COutPoint, CMutableTxOut, CMutableTxIn, CMutableTransaction, Hash160
from zcash.core.script import CScript, OP_DUP, OP_IF, OP_ELSE, OP_ENDIF, OP_HASH160, OP_EQUALVERIFY, OP_CHECKSIG, SignatureHash, SIGHASH_ALL, OP_FALSE, OP_DROP, OP_CHECKLOCKTIMEVERIFY, OP_SHA256, OP_TRUE
from zcash.core.scripteval import VerifyScript, SCRIPT_VERIFY_P2SH
from zcash.wallet import CBitcoinAddress, CBitcoinSecret, P2SHBitcoinAddress, P2PKHBitcoinAddress
import bitcoin
from utils import *
from zcash.core.serialize import *

# SelectParams('testnet')
SelectParams('regtest')
zcashd = zcash.rpc.Proxy()
FEE = 0.0001*COIN

def send_raw_tx(rawtx):
    txid = zcashd.sendrawtransaction(rawtx)
    return txid


def import_address(address):
    zcashd.importaddress(address, "", False)

def get_keys(funder_address, redeemer_address):
    fundpubkey = CBitcoinAddress(funder_address)
    redeempubkey = CBitcoinAddress(redeemer_address)
    return fundpubkey, redeempubkey

def privkey(address):
    zcashd.dumpprivkey(address)

def hashtimelockcontract(contract):
    funderAddr = CBitcoinAddress(contract.funder)
    redeemerAddr = CBitcoinAddress(contract.redeemer)
    h = x(contract.hash_of_secret)
    redeemblocknum = contract.redeemblocknum
    print("REDEEMBLOCKNUM ZCASH", redeemblocknum)
    zec_redeemscript = CScript([OP_IF, OP_SHA256, h, OP_EQUALVERIFY,OP_DUP, OP_HASH160,
                                 redeemerAddr, OP_ELSE, redeemblocknum, OP_CHECKLOCKTIMEVERIFY, OP_DROP, OP_DUP, OP_HASH160,
                                 funderAddr, OP_ENDIF,OP_EQUALVERIFY, OP_CHECKSIG])
    print("Redeem script for p2sh contract on Zcash blockchain:", b2x(zec_redeemscript))
    txin_scriptPubKey = zec_redeemscript.to_p2sh_scriptPubKey()
    # Convert the P2SH scriptPubKey to a base58 Bitcoin address
    txin_p2sh_address = CBitcoinAddress.from_scriptPubKey(txin_scriptPubKey)
    p2sh = str(txin_p2sh_address)
    zcashd.importaddress(p2sh,"",False)
    contract.p2sh = p2sh
    contract.redeemscript = b2x(zec_redeemscript)
    # Returning all this to be saved locally in p2sh.json
    return contract

def fund_contract(contract):
    send_amount = float(contract.amount)*COIN
    fund_tx = zcashd.sendtoaddress(contract.p2sh, send_amount)
#    contract.fund_tx = ""
    contract.fund_tx = b2x(lx(b2x(fund_tx)))
    return contract

def check_funds(p2sh):
    zcashd.importaddress(p2sh, "", False) 
    print("Imported address", p2sh)
    # Get amount in address
    amount = zcashd.getreceivedbyaddress(p2sh, 0)
    print("Amount in address", amount)
    amount = amount/COIN
    return amount

def get_tx_details(txid):
    fund_txinfo = zcashd.gettransaction(txid)
    return fund_txinfo['details'][0]

def find_transaction_to_address(p2sh):
    zcashd.importaddress(p2sh, "", False)
    txs = zcashd.listunspent()
    for tx in txs:
        if tx['address'] == CBitcoinAddress(p2sh):
            print("Found tx to p2sh", p2sh, "tx is ", tx)
            return tx

# def get_tx_details(txid):
#     # This method is problematic I haven't gotten the type conversions right
#     print(bytearray.fromhex(txid))
#     print(b2x(bytearray.fromhex(txid)))
#     fund_txinfo = zcashd.gettransaction(bytearray.fromhex(txid))
#     print(fund_txinfo)
#
#     return fund_txinfo['details'][0]
def find_secret(p2sh,vinid):
    zcashd.importaddress(p2sh, "", False)
    # is this working?
    print("vinid:",vinid)
    txs = zcashd.listtransactions()
    # print("==========================================LISTTT============", txs)
    # print()
    # print('LENNNNNNN:', len(txs))
    print('LENNNNNNN2:', len(txs))
    for tx in txs:
        # print("tx addr:", tx['address'], "tx id:", tx['txid'])
        # print(type(tx['address']))
        # print(type(p2sh))
        # print('type::',type(tx['txid']))
        raw = zcashd.gettransaction(lx(tx['txid']))['hex']
        decoded = zcashd.decoderawtransaction(raw)
        print("fdsfdfds", decoded['vin'][0])
        if('txid' in decoded['vin'][0]):
            sendid = decoded['vin'][0]['txid']
            print("sendid:", sendid)
            
            if (sendid == vinid ):
                # print(type(tx['txid']))
                # print(str.encode(tx['txid']))
                print("in if")
                return parse_secret(lx(tx['txid']))
    print("Redeem transaction with secret not found")
    return ""


def parse_secret(txid):
    raw = zcashd.gettransaction(txid)['hex']
    # print("Raw", raw)
    decoded = zcashd.decoderawtransaction(raw)
    scriptSig = decoded['vin'][0]['scriptSig']
    print("Decoded", scriptSig)
    asm = scriptSig['asm'].split(" ")
    pubkey = asm[1]
    secret = hex2str(asm[2])
    redeemPubkey = P2PKHBitcoinAddress.from_pubkey(x(pubkey))
    print('redeemPubkey', redeemPubkey)
    print(secret)
    return secret

def parse_script(script_hex):
    redeemscript = zcashd.decodescript(script_hex)
    scriptarray = redeemscript['asm'].split(' ')
    return scriptarray

def find_redeemblocknum(contract):
    scriptarray = parse_script(contract.redeemscript)
    redeemblocknum = scriptarray[8]
    return int(redeemblocknum)

def find_redeemAddr(contract):
    scriptarray = parse_script(contract.redeemscript)
    redeemer = scriptarray[6]
    redeemAddr = P2PKHBitcoinAddress.from_bytes(x(redeemer))
    return redeemAddr

def find_refundAddr(contract):
    scriptarray = parse_script(contract.redeemscript)
    funder = scriptarray[13]
    refundAddr = P2PKHBitcoinAddress.from_bytes(x(funder))  
    return refundAddr

def find_recipient(contract):
    # make this dependent on actual fund tx to p2sh, not contract
    txid = contract.fund_tx
    raw = zcashd.gettransaction(lx(txid), True)['hex']
    # print("Raw", raw)
    decoded = zcashd.decoderawtransaction(raw)
    scriptSig = decoded['vin'][0]['scriptSig']
    print("Decoded", scriptSig)
    asm = scriptSig['asm'].split(" ")
    pubkey = asm[1]
    initiator = CBitcoinAddress(contract.initiator)
    fulfiller = CBitcoinAddress(contract.fulfiller)
    print("Initiator", b2x(initiator))
    print("Fulfiler", b2x(fulfiller))
    print('pubkey', pubkey)
    redeemPubkey = P2PKHBitcoinAddress.from_pubkey(x(pubkey))
    print('redeemPubkey', redeemPubkey)

# addr = CBitcoinAddress('tmFRXyju7ANM7A9mg75ZjyhFW1UJEhUPwfQ')
# print(addr)
# # print(b2x('tmFRXyju7ANM7A9mg75ZjyhFW1UJEhUPwfQ'))
# print(b2x(addr))

def new_zcash_addr():
    addr = zcashd.getnewaddress()
    print('new ZEC addr', addr)
    return addr

def generate(num):
    blocks = zcashd.generate(num)
    return blocks




# redeems funded tx automatically, by scanning for transaction to the p2sh
# i.e., doesn't require buyer telling us fund txid
# returns false if fund tx doesn't exist or is too small
def redeem_with_secret(contract, secret):
    # How to find redeemscript and redeemblocknum from blockchain?
    # print("Redeeming contract using secret", contract.__dict__)
    p2sh = contract.p2sh
    minamount = float(contract.amount)
    #checking there are funds in the address
    amount = check_funds(p2sh)
    if(amount < minamount):
        print("address ", p2sh, " not sufficiently funded")
        return false
    fundtx = find_transaction_to_address(p2sh)
    amount = fundtx['amount'] / COIN
    p2sh = P2SHBitcoinAddress(p2sh)
    if fundtx['address'] == p2sh:
        print("Found {0} in p2sh {1}, redeeming...".format(amount, p2sh))

        redeemPubKey = find_redeemAddr(contract)
        print('redeemPubKey', redeemPubKey)

        redeemscript = CScript(x(contract.redeemscript))
        txin = CMutableTxIn(fundtx['outpoint'])
        txout = CMutableTxOut(fundtx['amount'] - FEE, redeemPubKey.to_scriptPubKey())
        # Create the unsigned raw transaction.
        tx = CMutableTransaction([txin], [txout])
        sighash = SignatureHash(redeemscript, tx, 0, SIGHASH_ALL)
        # TODO: figure out how to better protect privkey
        privkey = zcashd.dumpprivkey(redeemPubKey)
        sig = privkey.sign(sighash) + bytes([SIGHASH_ALL])
        print("SECRET", secret)
        preimage = secret.encode('utf-8')
        txin.scriptSig = CScript([sig, privkey.pub, preimage, OP_TRUE, redeemscript])

        # exit()

        # print("txin.scriptSig", b2x(txin.scriptSig))
        txin_scriptPubKey = redeemscript.to_p2sh_scriptPubKey()
        # print('Redeem txhex', b2x(tx.serialize()))
        VerifyScript(txin.scriptSig, txin_scriptPubKey, tx, 0, (SCRIPT_VERIFY_P2SH,))
        print("script verified, sending raw tx")
        txid = zcashd.sendrawtransaction(tx)
        print("Txid of submitted redeem tx: ", b2x(lx(b2x(txid))))
        return  b2x(lx(b2x(txid)))
    else:
        print("No contract for this p2sh found in database", p2sh)



# given a contract return true or false according to whether the relevant fund tx's timelock is still valid
def still_locked(contract):
    p2sh = contract.p2sh
    # Parsing redeemblocknum from the redeemscript of the p2sh
    redeemblocknum = find_redeemblocknum(contract)
    blockcount = zcashd.getblockcount()
    return (int(blockcount) < int(redeemblocknum))

def redeem_after_timelock(contract):
    p2sh = contract.p2sh
    fundtx = find_transaction_to_address(p2sh)
    amount = fundtx['amount'] / COIN

    if (fundtx['address'].__str__() != p2sh):
        print("no fund transaction found to the contract p2sh address ",p2sh)
        quit()
    # print("Found fundtx:", fundtx)
    # Parsing redeemblocknum from the redeemscript of the p2sh
    redeemblocknum = find_redeemblocknum(contract)
    blockcount = zcashd.getblockcount()
    print ("Current block:", blockcount, "Can redeem from block:", redeemblocknum)
    if(still_locked(contract)):
        print("too early for redeeming with timelock try again at block", redeemblocknum, "or later")
        return
    
    print("Found {0} in p2sh {1}, redeeming...".format(amount, p2sh))

        
    redeemPubKey = find_refundAddr(contract)
    print('refundPubKey', redeemPubKey)

    redeemscript = CScript(x(contract.redeemscript))
    txin = CMutableTxIn(fundtx['outpoint'])
    txout = CMutableTxOut(fundtx['amount'] - FEE, redeemPubKey.to_scriptPubKey())
    # Create the unsigned raw transaction.
    txin.nSequence = 0
    tx = CMutableTransaction([txin], [txout])
    tx.nLockTime = redeemblocknum
    
    sighash = SignatureHash(redeemscript, tx, 0, SIGHASH_ALL)
    # TODO: figure out how to better protect privkey
    privkey = zcashd.dumpprivkey(redeemPubKey)
    sig = privkey.sign(sighash) + bytes([SIGHASH_ALL])
    txin.scriptSig = CScript([sig, privkey.pub,  OP_FALSE, redeemscript])

    # exit()

    # print("txin.scriptSig", b2x(txin.scriptSig))
    txin_scriptPubKey = redeemscript.to_p2sh_scriptPubKey()
    # print('Redeem txhex', b2x(tx.serialize()))
    VerifyScript(txin.scriptSig, txin_scriptPubKey, tx, 0, (SCRIPT_VERIFY_P2SH,))
    print("script verified, sending raw tx")
    txid = zcashd.sendrawtransaction(tx)
    print("Txid of submitted redeem tx: ", b2x(lx(b2x(txid))))
    return  b2x(lx(b2x(txid)))


def get_redeemer_priv_key(contract):
    if (contract.redeemtype == 'secret'):
        redeemPubKey = find_redeemAddr(contract)
    elif (contract.redeemtype == 'timelock'):
        redeemPubKey = find_refundAddr(contract)
    else:
        raise ValueError("Invalid redeemtype:", contract.redeemtype)

    return zcashd.dumpprivkey(redeemPubKey)


# assuming we have the correct fund tx in the contract prepares the signed redeem raw tx
def get_raw_redeem(contract, privkey):

    p2sh = contract.p2sh
    p2sh = P2SHBitcoinAddress(p2sh)
    fundtx = contract.fund_tx
    '''if contract.fund_tx['address'] == p2sh:
        print("Found {0} in p2sh {1}, redeeming...".format(amount, p2sh))
'''
    redeemPubKey = find_redeemAddr(contract)
    print('redeemPubKey', redeemPubKey)

    redeemscript = CScript(x(contract.redeemscript))
    txin = CMutableTxIn(fundtx['outpoint'])
    txout = CMutableTxOut(fundtx['amount'] - FEE, redeemPubKey.to_scriptPubKey())
    # Create the unsigned raw transaction.
    tx = CMutableTransaction([txin], [txout])


    sighash = SignatureHash(redeemscript, tx, 0, SIGHASH_ALL)
    secret = get_secret()  # assumes secret is present in secret.json
    sig = privkey.sign(sighash) + bytes([SIGHASH_ALL])
    if(contract.redeemtype == "secret"):
        print("SECRET", secret)
        preimage = secret.encode('utf-8')
        txin.scriptSig = CScript([sig, privkey.pub, preimage, OP_TRUE, redeemscript])
    elif(contract.redeemtype == "timelock"):
        txin.scriptSig = CScript([sig, privkey.pub,  OP_FALSE, redeemscript])
    else:
        raise ValueError("invalid redeemtype:", contract.redeemtype)
    
    txin_scriptPubKey = redeemscript.to_p2sh_scriptPubKey()
    VerifyScript(txin.scriptSig, txin_scriptPubKey, tx, 0, (SCRIPT_VERIFY_P2SH,))
    print("script verified, writing raw redeem tx in contract")
    contract.rawredeemtx = CMutableTransaction.serialize(tx)
    return contract



def check_and_return_fundtx(contract):
    # How to find redeemscript and redeemblocknum from blockchain?
    print("Redeeming contract using secret", contract.__dict__)
    p2sh = contract.p2sh
    minamount = float(contract.amount)
    # the funder may have accidentily funded the p2sh with sufficient amount in several transactions. The current code
    # will abort in this case. This is a conservative approach to prevent the following attack, for example: the funder splits
    # the amount into many tiny outputs, hoping the redeemer will not have time to redeem them all by the timelock.
    fundtx = find_transaction_to_address(p2sh)
    if(fundtx== "" or fundtx==None):
        raise ValueError("fund tx to ", p2sh, " not found")
    print('fundtx:', fundtx)
    
    amount = fundtx['amount'] / COIN
    if(amount < minamount):
        raise ValueError("Insufficient funds in fund transaction.")
    
    
    contract.fund_tx = fundtx
    return contract
