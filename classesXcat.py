import zXcat
import bXcat
from utils import *
from waiting import *
from time import sleep
import json
import os, sys
from pprint import pprint
from contract import Contract, Trade, Participant

def check_p2sh(currency, address):
    if currency == 'bitcoin':
        print("Checking funds in Bitcoin p2sh")
        return bXcat.check_funds(address)
    else:
        print("Checking funds in Zcash p2sh")
        return zXcat.check_funds(address)

def set_price():
    trade = {}
    #TODO: make currencies interchangeable. Save to a tuple?
    sell = input("Which currency would you like to trade out of (bitcoin or zcash)? ")
    if sell == 'bitcoin':
        buy = 'zcash'
    else:
        buy = 'bitcoin'
    sell_amt = input("How much {0} do you want to sell? ".format(sell))
    sell_amt = 3.5
    print(sell_amt)
    buy_amt = input("How much {0} do you want to receive in exchange? ".format(buy))
    buy_amt = 1.2
    print(buy_amt)
    sell = {'currency': sell, 'amount': sell_amt}
    buy = {'currency': buy, 'amount': buy_amt}
    trade['sell'] = sell
    trade['buy'] = buy
    save_trade(trade)

def create_htlc(currency, funder, redeemer, secret, locktime):
    if currency == 'bitcoin':
        sell_p2sh = bXcat.hashtimelockcontract(funder, redeemer, secret, locktime)
    else:
        sell_p2sh = zXcat.hashtimelockcontract(funder, redeemer, secret, locktime)
    return sell_p2sh

def fund_htlc(currency, p2sh, amount):
    if currency == 'bitcoin':
        txid = bXcat.fund_htlc(p2sh, amount)
    else:
        txid = zXcat.fund_htlc(p2sh, amount)
    return txid

def initiate_trade():
    trade = get_trade()
    currency = trade['sell']['currency']
    secret = input("Initiating trade: Enter a password to place the {0} you want to sell in escrow: ".format(currency))
    # TODO: hash and store secret only locally.
    # secret = 'test'
    print('Remember your password:', secret)
    locktime = 20 # Must be more than first tx

    # Returns contract obj
    contracts = {}
    contract = create_htlc(currency, trade['sell']['initiator'], trade['sell']['fulfiller'], secret, locktime)
    sell_p2sh = contract['p2sh']
    contracts[contract['p2sh']] = contract
    save_contract(contracts)

    print('To complete your sell, send {0} {1} to this p2sh: {2}'.format(trade['sell']['amount'], currency, contract['p2sh']))
    response = input("Type 'enter' to allow this program to send funds on your behalf.")
    print("Sent")

    sell_amt = trade['sell']['amount']
    txid = fund_htlc(currency, sell_p2sh, sell_amt)

    trade['sell']['p2sh'] = sell_p2sh
    trade['sell']['fund_tx'] = txid
    trade['sell']['status'] = 'funded'
    # TODO: Save secret locally for seller
    trade['sell']['secret'] = secret

    save_trade(trade)

    buy_currency = trade['buy']['currency']
    buy_initiator = trade['buy']['initiator']
    buy_fulfiller = trade['buy']['fulfiller']
    print("Now creating buy contract on the {0} blockchain where you will wait for the buyer to send funds...".format(buy_currency))
    buy_contract = create_htlc(buy_currency, buy_fulfiller, buy_initiator, secret, locktime)
    buy_p2sh = buy_contract['p2sh']
    contracts[buy_contract['p2sh']] = buy_contract
    save_contract(contracts)
    print("Now contact the buyer and tell them to send funds to this p2sh: ", buy_p2sh)

    trade['buy']['p2sh'] = buy_p2sh

    save_trade(trade)

def get_addresses():
    trade = get_trade()
    sell = trade['sell']['currency']
    buy = trade['buy']['currency']

    init_offer_addr = input("Enter your {0} address: ".format(sell))
    # init_offer_addr = bXcat.new_bitcoin_addr()
    init_offer_addr = 'myfFr5twPYNwgeXyjCmGcrzXtCmfmWXKYp'
    print(init_offer_addr)
    init_bid_addr = input("Enter your {0} address: ".format(buy))
    # init_bid_addr = zXcat.new_zcash_addr()
    init_bid_addr = 'tmFRXyju7ANM7A9mg75ZjyhFW1UJEhUPwfQ'
    print(init_bid_addr)
    trade['sell']['initiator'] = init_offer_addr
    trade['buy']['initiator'] = init_bid_addr

    fulfill_offer_addr = input("Enter the {0} address of the party you want to trade with: ".format(sell))
    # fulfill_offer_addr = bXcat.new_bitcoin_addr()
    fulfill_offer_addr = 'mrQzUGU1dwsWRx5gsKKSDPNtrsP65vCA3Z'
    print(fulfill_offer_addr)
    fulfill_bid_addr = input("Enter the {0} address of the party you want to trade with: ".format(buy))
    # fulfill_bid_addr = zXcat.new_zcash_addr()
    fulfill_bid_addr = 'tmTjZSg4pX2Us6V5HttiwFZwj464fD2ZgpY'
    print(fulfill_bid_addr)
    trade['sell']['fulfiller'] = fulfill_offer_addr
    trade['buy']['fulfiller'] = fulfill_bid_addr

    # zec_funder, zec_redeemer = zXcat.get_keys(zec_fund_addr, zec_redeem_addr)
    trade['id'] = 1

    save_trade(trade)

def buyer_fulfill():
    trade = get_trade()

    buy_p2sh = trade['buy']['p2sh']
    sell_p2sh = trade['sell']['p2sh']

    buy_amount = check_p2sh(trade['buy']['currency'], buy_p2sh)
    sell_amount = check_p2sh(trade['sell']['currency'], sell_p2sh)


    amount = trade['buy']['amount']
    currency = trade['buy']['currency']
    if buy_amount == 0:
        input("The seller's p2sh is funded with {0} {1}, type 'enter' if this is the amount you want to buy in {1}.".format(trade['sell']['amount'], trade['sell']['currency']))
        input("You have not send funds to the contract to buy {1} (requested amount: {0}), type 'enter' to allow this program to send the agreed upon funds on your behalf.".format(amount, currency))
        p2sh = trade['buy']['p2sh']
        txid = fund_htlc(currency, p2sh, amount)
        trade['buy']['fund_tx'] = txid

        save_trade(trade)
    else:
        print("It looks like you've already funded the contract to buy {1}, the amount in escrow in the p2sh is {0}.".format(amount, currency))
        print("Please wait for the seller to remove your funds from escrow to complete the trade.")


def check_blocks(p2sh):
    # blocks = []
    with open('watchdata', 'r') as infile:
        for line in infile:
            res = bXcat.search_p2sh(line.strip('\n'), p2sh)
            # blocks.append(line.strip('\n'))
    # print(blocks)
    # for block in blocks:
    #     res = bXcat.search_p2sh(block, p2sh)

def redeem_p2sh(currency, p2sh, action):
    # action is buy or sell
    if currency == 'bitcoin':
        res = bXcat.redeem(p2sh, action)
    else:
        res = zXcat.redeem(p2sh, action)
    return res

def seller_redeem():
    # add locktime as variable?
    trade = get_trade()
    if 'status' in trade['buy'] and trade['buy']['status'] == 'redeemed':
        print("You already redeemed the funds and acquired {0} {1}".format(trade['buy']['amount'], trade['buy']['currency']))
        exit()
    else:
        # Seller redeems buyer's funded tx (contract in p2sh)
        p2sh = trade['buy']['p2sh']
        currency = trade['buy']['currency']
        redeem_tx = redeem_p2sh(currency, p2sh, 'buy')
        trade['buy']['redeem_tx'] = redeem_tx
        trade['buy']['status'] = 'redeemed'
        save_trade(trade)

def buyer_redeem():
    trade = get_trade()
    if 'status' in trade['sell'] and trade['sell']['status'] == 'redeemed':
        print("You already redeemed the funds and acquired {0} {1}".format(trade['sell']['amount'], trade['sell']['currency']))
        exit()
    else:
        # Buyer redeems seller's funded tx
        p2sh = trade['sell']['p2sh']
        currency = trade['sell']['currency']
        redeem_tx = redeem_p2sh(currency, p2sh, 'sell')
        trade['sell']['redeem_tx'] = redeem_tx
        trade['sell']['status'] = 'redeemed'
        save_trade(trade)

def print_trade(role):
    print("\nTrade status:")
    trade = get_trade()
    if role == 'seller':
        pprint(trade)
    else:
        del trade['sell']['secret']
        pprint(trade)

if __name__ == '__main__':
    print("ZEC <-> BTC XCAT (Cross-Chain Atomic Transactions)")
    print("=" * 50)
    # TODO: Get trade indicated by id number
    # TODO: pass trade into functions?
    # TODO: workflow framed as currency you're trading out of being sell. appropriate?
    # Have initiator propose amounts to trade
    trade = get_trade()

    # Instantiate classes from json/dicts?

    # print("C before Contract", c)
    sellContract = Contract(fulfiller='mTjZSg4pX2Us6V5HttiwFZwj464fD2ZgpY', initiator='mFRXyju7ANM7A9mg75ZjyhFW1UJEhUPwfQ', p2sh='2N7TKhb8wwn5d3dyXGj7jfaLLgqJnj44A4', amount=2.2, currency='bitcoin')

    buyContract = Contract(fulfiller='tmTjZSg4pX2Us6V5HttiwFZwj464fD2ZgpY', initiator='tmFRXyju7ANM7A9mg75ZjyhFW1UJEhUPwfQ', p2sh='t2N7TKhb8wwn5d3dyXGj7jfaLLgqJnj44A4', amount=1.2, currency='zcash')
    print("buyContract", buyContract.__dict__)

    trade = Trade(buyContract=buyContract, sellContract=sellContract)
    print("New trade", trade.__dict__)

    buy = trade.buyContract
    print("Trade buy contract initiator", buy.initiator)

    try:
        if sys.argv[1] == 'new':
            erase_trade()
            role = 'seller'
            trade = get_trade()
            print("Creating new XCAT transaction...")
        else:
            role = sys.argv[1]
            print("Your role in demo:", role)
    except:
        if trade == None:
            print("No active trades available.")
            res = input("Would you like to initiate a trade? (y/n) ")
            if res == 'y':
                role = 'seller'
            else:
                exit()
        else:
            print("Trade exists, run script as buyer or seller to complete trade.")
            exit()

    if trade is not None:
        if trade['sell']['status'] == 'redeemed' and trade['buy']['status'] == 'redeemed':
            print("This trade is already complete! Trade details:")
            pprint(trade)
            exit()

    if role == "seller":
        if trade == None or 'status' not in trade['sell']:
            set_price()
            get_addresses()
            initiate_trade()
            print_trade('seller')
        elif 'status' in trade['sell']:
            if 'fund_tx' in trade['buy']:
                # Means buyer has already funded the currency the transaction initiator wants to exchange into
                input("Buyer funded the contract where you offered to buy {0}, type 'enter' to redeem {1} {0} from {2}.".format(trade['buy']['currency'], trade['buy']['amount'], trade['buy']['p2sh']))
                seller_redeem()
                print("You have redeemed {0} {1}!".format(trade['buy']['amount'], trade['buy']['currency']))
                print_trade('seller')
            else:
                print("Buyer has not yet funded the contract where you offered to buy {0}, please wait for them to complete their part.".format(trade['buy']['currency']))
                print_trade('seller')
    else:
        # Need better way of preventing buyer from having secret
        if 'status' not in trade['buy'] and trade['sell']['status'] == 'funded':
            print("One active trade available, fulfilling buyer contract...")
            trade = get_trade()
            buyer_fulfill()
            # How to monitor if txs are included in blocks -- should use blocknotify and a monitor daemon?
            # For regtest, can mock in a function
            # p2sh = trade['buy']['p2sh']
            # check_blocks(p2sh)
            print_trade('buyer')
        elif trade['buy']['status'] == 'redeemed':
            # Seller has redeemed buyer's tx, buyer can now redeem.
            input("Buyer funded the contract where you paid them in {0} to buy {1}, type 'enter' to redeem {2} {1} from {3}.".format(trade['buy']['currency'], trade['sell']['currency'], trade['buy']['amount'], trade['buy']['p2sh']))
            buyer_redeem()
            print("XCAT trade complete!")
            print_trade('buyer')



        # Note: there is some little endian weirdness in the bXcat and zXcat files, need to handle the endianness of txids better & more consistently