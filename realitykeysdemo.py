#!/usr/bin/python

# This script allows two parties who don't trust each other to create a contract conditional on the outcome of a Reality Key.
# The actual Reality Keys are fetched automatically using the Reality Keys API, so the users only need to supply their own keys.
# It requires pybitcointools, which you can get here:
# https://github.com/vbuterin/pybitcointools

# Steps:

# Alice and Bob: Agree on a Reality Key, and get the ID <fact_id> from the URL.
 
# Alice: Creates keys and sends the public key to Bob.   
#    ./realitykeysdemo.py makekeys
#    Get the public key and send it to Bob.
#    Temporarily fund her own address with her stake using any bitcoin client. 
#    (This step makes things simpler here, although the script can be rewritten without it.)

# Bob: Creates keys and sends the pubkey to Alice. 
#    ./realitykeysdemo.py makekeys
#    Get the public key and send it to Alice.
#    Temporarily fund his own address with his stake.
#    (This step makes things simpler here, although the script can be rewritten without it.)

# If Bob or Alice disappears before completing the transaction, the other person can get the money back from the temporary address with:
#    ./realitykeysdemo.py pay <address> <amount> [<fee>]"

# Alice: 
#    Creates a 1/2 (for now) P2SH address for combinations of ( her key + rk-yes ) or ( his key + rk-no ).
#    Creates a transaction spending the contents of both her and Bob's temporary address to the P2SH address, signed with her private key.
#    ./realitykeysdemo.py setup <fact_id> <yes_winner_public_key> <yes_stake_amount> <no_winner_public_key> <no_stake_amount>" 
#    (This outputs a serialized, partially-signed transaction which she then sends to Bob to complete and broadcast.)

# Bob: Recreates Alice's transaction to make sure he gets the same thing, then signs it with his private key and broadcasts it.
#    ./realitykeysdemo.py setup <fact_id> <yes_winner_public_key> <yes_stake_amount> <no_winner_public_key> <no_stake_amount> <transaction_only_half_signed>" 

# ...Wait until the result is issued...

# Alice or Bob (whoever wins):
#    ./realitykeysdemo.py claim <fact_id> <yes_winner_public_key> <no_winner_public_key> [<fee>] [<send_to_address>]
#    If the broadcast fails, the script will output the transaction to send to some other bitcoind somewhere, eg:
#    ./bitcoind sendrawtransaction <transaction> 

from pybitcointools import * # https://github.com/vbuterin/pybitcointools

import os
import sys

import urllib2
import simplejson

REALITY_KEYS_API = 'https://www.realitykeys.com/api/v1/fact/%s/?accept_terms_of_service=current'
APP_SECRET_FILE = ".realitykeysdemo"

MAX_TRANSACTION_FEE = 20000
MIN_TRANSACTION_FEE = 10000
DEFAULT_TRANSACTION_FEE = 10000

def user_private_key(create_if_missing=False):
    """Return the private key of the current user.

    Normally it would come from a seed in a file in the user's home directory, generated during makekeys.

    Alternatively it can be specified as an environment parameter, in which case the seed file will be ignored.
    For example, you might run:
    SEED='alice-9823jeijldijfiljilfjaeidfjsfksdjfkdfjkdfj102OSIJDIFJDijifjdsjfxd' ./realitykeysdemo.py setup etc etc etc
    This is useful when experimenting, because it allows you to switch between test users easily.

    """

    # If the user passed us a seed as an environmental variable, use that.
    seed = os.getenv('SEED')

    # Otherwise try to get it from a dotfile in the user's home directory or equivalent.
    if seed is None:

        home_dir = os.getenv('HOME')
        if home_dir is None:
            raise Exception("Could not get your home directory to read your secret seed.")

        seed_file = os.path.join(home_dir, APP_SECRET_FILE)
        if not os.path.isfile(seed_file):
            if create_if_missing:
                with open(seed_file, 'w') as s:
                    print "Writing your secret seed to %s" % (seed_file)
                    print ""
                    os.chmod(seed_file, 0600)
                    seed = s.write(random_electrum_seed())
            else:
                raise Exception("Seed file not found. Run %s makekeys to generate it or set it as the SEED environmental variable." % (script_name))

        with open(seed_file, 'r') as s:
            seed = s.read().rstrip()

        if seed is None or seed == "":
            raise Exception("Seed file was empty or unreadable.")

    return sha256(seed)

def spendable_output(addr, stake_amount, min_transaction_fee, max_transaction_fee=0):
    """Return an output for the specified amount, plus fee, or None if it couldn't find one.
    Fetched by querying blockchain.info.
    This is very primitive, and assumes you've already put exactly the right amount into the address.
    """

    outputs = unspent(addr)
    if len(outputs) == 0:
        return None

    if len(outputs) > 1:
        return None

    for o in outputs:

        val = o['value']
        if max_transaction_fee > 0 and val > ( stake_amount + max_transaction_fee ):
            #print "Too much money in input implying too-high fee."
            #print "Could continue but the fee " + str(val-pay_amount)+ " which would be greater than " + str(max_transaction_fee) + " and sounds too high"
            continue

        if val < stake_amount:
            #print "Not enough money in input, giving up"
            continue

        if val < ( stake_amount + min_transaction_fee ):
            #print "Not enough money in input to cover the minimum transaction fee of "+str(min_transaction_fee)+", giving up"
            continue

        return o

    #print "No suitable outputs found for address %s, giving up" % (addr)
    return None

def execute_makekeys():
    """Create a random seed and generate a key from it, and output the corresponding public key and address.

    If the seed already exists, leave it as it is and just output the information about it again.
    If the SEED environmental variable was set, forget about the seed file and work from that instead.
    """

    priv = user_private_key(True)
    pub = privtopub(priv)
    addr = pubtoaddr(pub)

    #print "Your private key is:"
    #print priv
    #print "Please keep this safe and don't tell anyone."
    #print ""

    print "Your public key is:"
    print pub
    print "Please send this to the other party."
    print ""

    print "Your temporary address is:"
    print addr
    print "Please make payment to this address first."
    print ""

    print "Next step: Exchange keys, pay your stake to %s, have them pay their stake to their address, then one of you runs:" % (addr)
    print "If you are yes:"
    print "./realitykeysdemo.py setup <fact_id> %s <your_stake_in_satoshis> <their_public_key> <their_stake_in_satoshis>" % (pub)
    print "If you are no:"
    print "./realitykeysdemo.py setup <fact_id> <their_public_key> <their_stake_in_satoshis> %s <your_stake_in_satoshis>" % (pub)

    sys.exit()

def execute_setup(fact_id, yes_winner_public_key, yes_stake_amount, no_winner_public_key, no_stake_amount, existing_tx, is_nopushtx): 
    """Create a P2SH address spendable by the each person's own key combined with the appropriate reality key.
    If passed a half-signed version of the transaction created like that, sign it and broadcast it.
    If not, create and output a half-signed version of the transaction to send to the other party to complete.
    """

    yes_winner_address = pubtoaddr(yes_winner_public_key)
    no_winner_address = pubtoaddr(no_winner_public_key)

    # The private key of the person currently using the script.
    # Both parties will need to run the script in turn, substituting their own public keys.
    private_key = user_private_key()

    # Find out if the current user is we're representing yes or no.
    # This will tell us which input to sign, and help us provide user feedback.
    public_key = privtopub(private_key)
    if public_key == yes_winner_public_key:
        am_i_yes_or_no = 'yes'
    elif public_key == no_winner_public_key:
        am_i_yes_or_no = 'no'
    else:
        print "Neither of the public keys supplied matched the private key supplied."
        print "For simplicity, this script expects you to use the same keypair to temporarily fund an address that you use to unlock the final result if you win."
        print "Giving up, sorry."
        sys.exit()

    # The amount pledged by yes and no combined will be locked up as a single output in a p2sh address.
    contract_total_amount = yes_stake_amount + no_stake_amount
    if (contract_total_amount == 0):
        print "Contract is zero, nothing to do."
        sys.exit()

    # We've assumed that there is a single output paid the address owned by each party that can be used as inputs.
    # This means each party can create the whole transaction (except the signatures) independently, even the other party's inputs. 

    # If we hadn't taken the shortcut of forcing the parties to temporarily fund addresses with the right amounts,
    # we'd need to sign this with an additional "SIGHASH_ALL|SIGHASH_ANYONECANPAY" flag. 
    # This would to allow them to add their own inputs later, without invalidating our signature for the inputs we signed.
    # It might be helpful to patch pybitcointools to make this easier, as not all the relevant functions seem to want to let us pass in the flag.
    inputs = []

    signatures_needed = 0
    if yes_stake_amount > 0:
        signatures_needed = signatures_needed + 1
        yes_input = spendable_output(yes_winner_address, yes_stake_amount, MIN_TRANSACTION_FEE/2, MAX_TRANSACTION_FEE/2)
        if yes_input is not None:
            inputs = inputs + [yes_input]

    if no_stake_amount > 0:
        signatures_needed = signatures_needed + 1
        no_input = spendable_output(no_winner_address, no_stake_amount, MIN_TRANSACTION_FEE/2, MAX_TRANSACTION_FEE/2)
        if no_input is not None:
            inputs = inputs + [no_input]

    if (yes_stake_amount > 0 and yes_input is None) or (no_stake_amount > 0 and no_input is None):
        print "The temporary addresses have not yet been fully funded."
        if (yes_stake_amount > 0 and yes_input is None):
            if am_i_yes_or_no == 'yes':
                print "Please fund the following (yes):"
            else:
                print "Please ask the other party to fund the following (yes):"
            print "Yes: %s satoshis to the address %s" % (str(yes_stake_amount), yes_winner_address)

        if (no_stake_amount > 0 and no_input is None):
            if am_i_yes_or_no == 'no':
                print "Please fund the following (no):"
            else:
                print "Please ask the other party to fund the following (no):"

            print "No: %s satoshis to the address %s" % (str(no_stake_amount), no_winner_address)

        sys.exit()

    # Fetch the reality key public keys for yes and no.
    req = urllib2.Request(REALITY_KEYS_API % (fact_id))
    response = urllib2.urlopen(req)
    fact_json = simplejson.load(response)
    yes_reality_key = fact_json['yes_pubkey']   
    no_reality_key = fact_json['no_pubkey']

    # Use ECC addition to combine the key of the person who wins on "yes" with the "yes" reality key
    # ...and the key of the person who wins on "no" with the "no" reality key
    # Hopefully this is a safe thing to be doing. Feedback gratefully received...

    # See the discussion on the following thread, in particular this suggestion by Peter Todd:
    # https://bitcointalk.org/index.php?topic=260898.msg3040083#msg3040083
    # It would be cleaner to do this with OP_IF / OP_ELSE logic in the transaction script, but that would fail IsStandard checks.

    # TODO: Add a third key for the two parties so that they can settle themselves without Reality Keys if they prefer.
    # Ideally we'd do;
    # 2/4 yes_compound_public_key, no_compound_public_key, yes_winner_public_key, no_winner_public_key
    # If that's non-standard (not sure), we could do:
    # 1/3 yes_compound_public_key, no_compound_public_key, yes_winner_no_winner_compound_public_key

    yes_compound_public_key = add_pubkeys(yes_winner_public_key, yes_reality_key)
    no_compound_public_key = add_pubkeys(no_winner_public_key, no_reality_key)

    multisig_script = mk_multisig_script([yes_compound_public_key, no_compound_public_key], 1, 2)
    pay_to_addr = p2sh_scriptaddr(multisig_script)
    print "Made p2sh address: %s. Creating a transaction to fund it." % (pay_to_addr)

    outputs = [{'value': contract_total_amount, 'address': pay_to_addr}]

    tx = mktx(inputs, outputs)

    # The first person runs the script without passing it a transaction. The existing_tx will be None and we use the one we just made.
    # This then outputs a transaction, with their input signed but still needing to be signed by the second person.
    # The second person then runs the script, passing it the transaction they got from the first person.
    # If we get that transaction, we'll check it against the version we just made ourselves to be sure it's what we expect.
    # It should be the same except that ours is unsigned, in which case we'll throw away our transaction and use theirs instead.
    signatures_done = 0
    if existing_tx is not None:
        #print existing_tx
        their_tx = deserialize(existing_tx)
        our_tx = deserialize(tx)
        # Compare the transactions, except the inputs, which are signed and we don't care anyway.
        # Alternatively we could go through these and just remove the signatures, but it shouldn't matter.
        # Being honest they haven't horsed around with their tx and sent us this instead.
        # If they had we'd catch them here.
        # their_tx['outs'] = [{'value': 110000, 'script': '1NGtmZttBEUGWTTGGyQTHTTrC76dHXPEZt'}]
        our_tx['ins'] = []
        their_tx['ins'] = []
        if serialize(our_tx) != serialize(their_tx):
            print "The transaction we received was not what we expected."
            print "Aborting."
            sys.exit()
        tx = existing_tx
        signatures_done = signatures_done + 1

    #print "Unsigned:"
    #print deserialize(tx)

    # Sign whichever of the inputs we have the private key for. 
    # Since we only allow one input per person, and we add them ourselves, we can assume yes is first and no is second.
    if (am_i_yes_or_no == 'yes') and (yes_stake_amount > 0):
        tx = sign(tx,0,private_key)
        signatures_done = signatures_done + 1
        #print "Signed yes:"
        #print deserialize(tx)

    if (am_i_yes_or_no == 'no') and (no_stake_amount > 0):
        tx = sign(tx,1,private_key)
        signatures_done = signatures_done + 1
        #print "Signed no:"
        #print deserialize(tx)

    if signatures_needed == signatures_done:
        if is_nopushtx:
            print "Created the following transaction, but won't broadcast it because you specified --nopushtx:"
            print tx
        else:
            print "Broadcasting transaction...:"
            print tx
            pushtx(tx)
            print "Next step: Wait for the result, then the winner runs:"
            print "./realitykeysdemo.py claim %s %s %s [<fee>] [<send_to_address>]" % (fact_id, yes_winner_public_key, no_winner_public_key)
    else:
        print "Created a transaction:"
        print tx
        print "Next step: The other party runs:"
        print "./realitykeysdemo.py setup %s %s %s %s %s %s" % (fact_id, yes_winner_public_key, str(yes_stake_amount), no_winner_public_key, str(no_stake_amount), tx)

    sys.exit()

def execute_claim(fact_id, yes_winner_public_key, no_winner_public_key, fee, send_to_address, is_nopushtx):
    """When executed by the winner, creates the P2SH address used in previous contracts and spends the contents to <send_to_address>
    """

    private_key = user_private_key()
    if send_to_address is None:
        send_to_address = pubtoaddr(privtopub(private_key))
    
    # Get the reality keys representing "yes" and "no".
    req = urllib2.Request(REALITY_KEYS_API % (fact_id))
    response = urllib2.urlopen(req)
    fact_json = simplejson.load(response)
    yes_reality_key = fact_json['yes_pubkey']   
    no_reality_key = fact_json['no_pubkey']

    winner = fact_json['winner']
    winner_privkey = fact_json['winner_privkey']

    if winner is None:
        print "The winner of this fact has not yet been decided. Please try again later."
        sys.exit()

    if winner_privkey is None:
        print "This fact has been decided but the winning key has not been published yet. Please try again later."
        sys.exit()

    # Combine the key of the person who wins on "yes" with the "yes" reality key
    # ...and the key of the person who wins on "no" with the "no" reality key
    # ...to recreate the p2sh address we created in setup

    yes_compound_public_key = add_pubkeys(yes_winner_public_key, yes_reality_key)
    no_compound_public_key = add_pubkeys(no_winner_public_key, no_reality_key)

    winner_compound_private_key = add_privkeys(private_key, winner_privkey)

    # Make sure we can generate the public key from the private key we created.
    # If we can't there's no point in trying to use it to spend the transaction.
    try:
        winner_public_key_from_winner_private_key = privtopub(winner_compound_private_key)
    except:
        print "An error occurred trying to recreate the expected public keys from the private key supplied, giving up."
        sys.exit()

    if winner == "Yes":
        if (yes_compound_public_key != winner_public_key_from_winner_private_key):
            print "Could not recreate the expected public keys from the private key supplied. Are you sure you won?"
            sys.exit()
    elif winner == "No":
        if (no_compound_public_key != winner_public_key_from_winner_private_key):
            print "Could not recreate the expected public keys from the private key supplied, Are you sure you won?."
            sys.exit()
    else:
        print "Expected the winner to be Yes or No, but got \"%s\", now deeply confused, giving up." % (winner)
        sys.exit()

    # Regenerate the p2sh address we used during setup:
    multisig_script = mk_multisig_script([yes_compound_public_key, no_compound_public_key], 1, 2)
    p2sh_address = p2sh_scriptaddr(multisig_script)

    transactions = unspent(p2sh_address)
    if len(transactions) == 0:
        print "There do not seem to be any payments made to this address."
        sys.exit()
    
    val = 0
    for out in transactions:
        # eg [{'output': u'4cc806bb04f730c445c60b3e0f4f44b54769a1c196ca37d8d4002135e4abd171:1', 'value': 50000, 'address': u'1CQLd3bhw4EzaURHbKCwM5YZbUQfA4ReY6'}]
        val = val + out['value']

    if val == 0:
        print "Nothing to spend."
        sys.exit()

    val = val - fee
    print "Found %s in the P2SH address" % (str(val))

    outs = [{'value': val, 'address': send_to_address}]
    tx = mktx(transactions, outs)

    #print deserialize(tx)
    sig1 = multisign(tx,0,multisig_script,winner_compound_private_key)
    multi_tx = apply_multisignatures(tx,0,multisig_script,[sig1])

    if is_nopushtx:
        print "Created the following transaction, but won't broadcast it because you specified --nopushtx:"
        print multi_tx
    else:
        # blockchain.info seems to reject this transaction.
        # confusingly, it seems to go ok with bitcoind
        try:
            pushtx(multi_tx)
        except:
            try:
                eligius_pushtx(multi_tx)
            except:
                print "We think this should be a valid, standard transaction, but the blockchain.info API won't accept it."
                print "You can send it with bitcoind instead:"
                print "./bitcoind sendrawtransaction %s" % (multi_tx)

def execute_pay(pay_to_addr, pay_amount, fee, is_nopushtx):
    """ Make a simple payment, from a single output, with change.

    You can use this to refund an aborted transaction, if the other user fails to fund their side or fails to complete the P2SH transaction.
    """

    private_key = user_private_key()
    public_key = privtopub(private_key)
    addr = pubtoaddr(public_key)

    if addr == pay_to_addr:
        print "Paying yourself..."

    spendable_input = spendable_output(addr, pay_amount, fee, 0)
    if spendable_input is None:
        print "Could not find an output to spend, giving up."
        sys.exit()

    remainder = spendable_input['value'] - pay_amount - fee 

    outputs = [{'value': pay_amount, 'address': pay_to_addr}]
    if remainder > 0:
        print "Sending %s back to the original address as change." % (str(remainder))
        change_outputs = [{'value': remainder, 'address': addr}]
        outputs = outputs + change_outputs

    tx = mktx([spendable_input], outputs)
    tx = sign(tx, 0, private_key)

    if is_nopushtx:
        print "Created the following transaction, but won't broadcast it because you specified --nopushtx:"
        print tx
    else:
        pushtx(tx)

#########################################################################

arg_list = sys.argv

# nopushtx flag applies to pay, claim and setup and prevents us from sending anything to the blockchain.
is_nopushtx = "--nopushtx" in arg_list
if is_nopushtx:
    arg_list.remove("--nopushtx")

args = dict(enumerate(arg_list))
script_name = args.get(0)

command = args.get(1)
if command is None:
    print "Usage: ./realitykeysdemo.py [--nopushtx] <makekeys|setup|claim|pay> [<params>]"
    sys.exit()

if command == "makekeys":

    execute_makekeys()

elif command == "setup":

    if len(args) < 7:
        print "Usage: ./realitykeysdemo.py [--nopushtx] setup <fact_id> <yes_winner_public_key> <yes_stake_amount> <no_winner_public_key> <no_stake_amount> [<serialized_half_signed_transaction>]"
        sys.exit()

    execute_setup(str(int(args.get(2))), args.get(3), int(args.get(4)), args.get(5), int(args.get(6)), args.get(7, None), is_nopushtx)

elif command == "claim":

    if len(args) < 5:
        print "Usage: ./realitykeysdemo.py [--nopushtx] claim <fact_id> <yes_winner_public_key> <no_winner_public_key> [<fee>] [<send_to_address>]"
        sys.exit()

    execute_claim(str(int(args.get(2))), args.get(3), args.get(4), int(args.get(5, DEFAULT_TRANSACTION_FEE)), args.get(6), is_nopushtx)

elif command == "pay":

    if len(args) < 4:
        print "Usage: ./realitykeysdemo.py [--nopushtx] pay <address> <amount> [<fee>]"
        sys.exit()

    execute_pay(args.get(2), int(args.get(3)), int(args.get(4, DEFAULT_TRANSACTION_FEE)), is_nopushtx)

else:

    print "Usage: ./realitykeysdemo.py [--nopushtx] <makekeys|create|complete|claim> [<params>]"
    print "Start with ./realitykeysdemo.py makekeys"
    sys.exit()

