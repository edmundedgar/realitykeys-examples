#!/usr/bin/python

# This script allows two parties who don't trust each other to create a contract conditional on the outcome of a Reality Key.
# The actual Reality Keys are fetched automatically using the Reality Keys API, so the users only need to supply their own keys.
# It requires pybitcointools, which you can get here:
# https://github.com/vbuterin/pybitcointools

# Steps:
 
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

# Alice and Bob: Register a Reality Key, and get the ID <fact_id> from the URL.
# NB They should make sure the Reality Keys were newly created and didn't exist before they exchanged keys.

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
#    ./realitykeysdemo.py claim <fact_id> <yes_winner_public_key> <no_winner_public_key> [<fee>] [<pay_to_address>]
#    If the broadcast fails, the script will output the transaction to send to some other bitcoind somewhere, eg:
#    ./bitcoind sendrawtransaction <transaction> 

from pybitcointools import * # https://github.com/vbuterin/pybitcointools

import os
import sys
import argparse

import urllib2
import simplejson

REALITY_KEYS_API = 'https://www.realitykeys.com/api/v1/fact/%s/?accept_terms_of_service=current'
APP_SECRET_FILE = ".realitykeysdemo"

MAX_TRANSACTION_FEE = 20000
MIN_TRANSACTION_FEE = 10000
DEFAULT_TRANSACTION_FEE = 10000

def apply_multisignatures_with_if_hint(*args): # tx,i,script,sigs OR tx,i,script,sig1,sig2...,sig[n]
    """A copy of the pybitcointools apply_multisignatures, but with an extra if
    """

    if_hint = 1
    tx, i, script = args[0], int(args[1]), args[2]
    sigs = args[3] if isinstance(args[3],list) else list(args[3:])

    if re.match('^[0-9a-fA-F]*$',script): script = script.decode('hex')
    sigs = [x.decode('hex') if x[:2] == '30' else x for x in sigs]
    if re.match('^[0-9a-fA-F]*$',tx):
        return apply_multisignatures_with_if_hint(tx.decode('hex'),i,script,sigs).encode('hex')

    txobj = deserialize(tx)
    txobj["ins"][i]["script"] = serialize_script([None]+sigs+[if_hint]+[script])
    return serialize(txobj)

def mk_multisig_script_if_else(combos):

    combo1 = combos[0]
    combo2 = combos[1]

    OP_CHECKMULTISIG = 174
    OP_IF = 99
    OP_ELSE = 103
    OP_ENDIF = 104

    num_required = len(combo1)
    num_supplied = len(combo1)

    script_elements = []

    # A dummy if that doesn't do anything
    # script_elements.append(1)
    script_elements.append(OP_IF)

    script_elements.append(num_supplied)
    script_elements.extend(combo1)
    script_elements.append(num_required)
    script_elements.append(OP_CHECKMULTISIG)

    script_elements.append(OP_ENDIF)

    return serialize_script(script_elements)
    #return serialize_script([num_required]+combo+[num_supplied,OP_CHECKMULTISIG])

    # with flags (1)
    # x sig sig 1 
    # op_if
    # 2 alice rk-yes
    # op_else 
    # 2 bob   rk-no
    # op_endif
    # 2 OP_CHECKSIG
    script_str = ""
    script_str = script_str + OP_IF

    combo = combos[0]
    num_required = len(combo)
    num_supplied = num_required
    num_required_hex = str(hex(num_required+OP_NUMBER_PLUS)).lstrip("0x")
    num_supplied_hex = str(hex(num_supplied+OP_NUMBER_PLUS)).lstrip("0x")
    script_str = script_str + num_supplied_hex
    for pub in combo:
        num_bytes_hex = str(hex(len(pub) / 2)).lstrip("0x")
        script_str = script_str + num_bytes_hex + pub
    script_str = script_str + num_required_hex # this could be once on the end for economy 

    script_str = script_str + OP_ELSE

    combo = combos[1]
    script_str = script_str + num_supplied_hex
    for pub in combo:
        num_bytes_hex = str(hex(len(pub) / 2)).lstrip("0x")
        script_str = script_str + num_bytes_hex + pub
    script_str = script_str + num_required_hex # this could be once on the end for economy 

    script_str = script_str + OP_ENDIF 
    script_str = script_str + OP_CHECKMULTISIGVERIFY

    return script_str



def user_private_key(create_if_missing=False, seed=None):
    """Return the private key of the current user.

    Normally it would come from a seed in a file in the user's home directory, generated during makekeys.

    Alternatively it can be specified as an environment parameter, in which case the seed file will be ignored.
    For example, you might run:
    SEED='alice-9823jeijldijfiljilfjaeidfjsfksdjfkdfjkdfj102OSIJDIFJDijifjdsjfxd' ./realitykeysdemo.py setup etc etc etc
    This is useful when experimenting, because it allows you to switch between test users easily.

    """
    #print "using seed %s " % (seed)

    # Otherwise try to get it from a dotfile in the user's home directory or equivalent.
    if seed is None:

        #print "no seed, getting from file"

        home_dir = os.getenv('HOME')
        if home_dir is None:
            raise Exception("Could not get your home directory to read your secret seed.")

        seed_file = os.path.join(home_dir, APP_SECRET_FILE)
        if not os.path.isfile(seed_file):
            if create_if_missing:
                with open(seed_file, 'w') as s:
                    os.chmod(seed_file, 0600)
                    seed = s.write(random_electrum_seed())
            else:
                raise Exception("Seed file not found, tried to create it at %s but failed." % (seed_file))

        with open(seed_file, 'r') as s:
            seed = s.read().rstrip()

        if seed is None or seed == "":
            raise Exception("Seed file was empty or unreadable.")

    return sha256(seed)

def unspent_outputs(addr, filter_from_outputs=None):
    """ If we were passed a list of outputs to use, filter them for the right address
     Otherwise, fetch unspent outputs for the address from blockchain.info
    """
    if filter_from_outputs is not None:
        unspents = []
        for o in filter_from_outputs:
            parts = o.split(":")
            o_addr = parts[0]
            # allow an optional blank address to just assume it's for us
            if o_addr != "" and o_addr != addr:
                continue
            tx_id = parts[1]
            idx = int(parts[2])
            val = int(parts[3])
            # make something like this:
            # [{'output': u'4cc806bb04f730c445c60b3e0f4f44b54769a1c196ca37d8d4002135e4abd171:1', 'value': 50000, 'address': u'1CQLd3bhw4EzaURHbKCwM5YZbUQfA4ReY6'}]
            unspents.append( {
                'output': tx_id + ':' + str(idx),
                'value': val,
                'address': o_addr
            } )
        return unspents
    else:
        unspents = unspent(addr)
    return unspents 

def spendable_input(addr, stake_amount, min_transaction_fee, max_transaction_fee=0, inputs=None):
    """Return an output for the specified amount, plus fee, or None if it couldn't find one.
    Fetched by querying blockchain.info, or by passing a list in here as inputs.
    This is very primitive, and assumes you've already put exactly the right amount into the address.
    """
    outputs = unspent_outputs(addr, inputs)

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

def magic_byte(settings):
    """The magic byte to be used for addresses.
    Only supports bitcoin and bitcoin testnet, would need to be modified for other coins.
    """
    if settings.get('testnet', False):
        return 111
    else:
        return 0

def execute_makekeys(settings):
    """Create a random seed and generate a key from it, and output the corresponding public key and address.

    If the seed already exists, leave it as it is and just output the information about it again.
    If the SEED environmental variable was set, forget about the seed file and work from that instead.
    """

    seed = settings.get('seed', None)
    verbose = settings.get('verbose', False)

    priv = user_private_key(True, seed)
    pub = privtopub(priv)
    addr = pubtoaddr(pub, magic_byte(settings))

    #print "Your private key is:"
    #print priv
    #print "Please keep this safe and don't tell anyone."
    #print ""

    out = []

    if verbose:
        out.append("Your public key is:")
        out.append(pub)
        out.append("Please send this to the other party.")
        out.append("")
    else:
        out.append(pub)

    if verbose:
        out.append("Your temporary address is:")
        out.append(addr)
        out.append("Please make payment to this address first.")
        out.append("")
    else:
        out.append(addr)

    if verbose:
        out.append("Next step: Exchange keys, pay your stake to %s, have them pay their stake to their address, then one of you runs:" % (addr))
        out.append("If you are yes:")
        out.append("./realitykeysdemo.py setup <fact_id> %s <your_stake_in_satoshis> <their_public_key> <their_stake_in_satoshis>" % (pub))
        out.append("If you are no:")
        out.append("./realitykeysdemo.py setup <fact_id> <their_public_key> <their_stake_in_satoshis> %s <your_stake_in_satoshis>" % (pub))

    return out

def execute_setup(settings, fact_id, yes_winner_public_key, yes_stake_amount, no_winner_public_key, no_stake_amount, existing_tx): 
    """Create a P2SH address spendable by the each person's own key combined with the appropriate reality key.
    If passed a half-signed version of the transaction created like that, sign it and broadcast it.
    If not, create and output a half-signed version of the transaction to send to the other party to complete.
    """

    out = []

    fact_id = str(fact_id)
    verbose = settings.get('verbose', False)
    seed = settings.get('seed', None)

    yes_winner_address = pubtoaddr(yes_winner_public_key, magic_byte(settings))
    no_winner_address = pubtoaddr(no_winner_public_key, magic_byte(settings))

    # The private key of the person currently using the script.
    # Both parties will need to run the script in turn, substituting their own public keys.
    private_key = user_private_key(False, seed)
    #print "my priv key is %s" % (private_key)

    # Find out if the current user is we're representing yes or no.
    # This will tell us which input to sign, and help us provide user feedback.
    public_key = privtopub(private_key)
    if public_key == yes_winner_public_key:
        am_i_yes_or_no = 'yes'
    elif public_key == no_winner_public_key:
        am_i_yes_or_no = 'no'
    else:
        raise Exception("Neither of the public keys supplied matched the private key supplied :%s:%s:%s:%s:." % (private_key, public_key, yes_winner_public_key, no_winner_public_key))

    # The amount pledged by yes and no combined will be locked up as a single output in a p2sh address.
    contract_total_amount = yes_stake_amount + no_stake_amount
    if (contract_total_amount == 0):
        raise Exception("Neither of the public keys supplied matched the private key supplied.")

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
        yes_input = spendable_input(yes_winner_address, yes_stake_amount, MIN_TRANSACTION_FEE/2, MAX_TRANSACTION_FEE/2, settings.get('inputs', None))
        if yes_input is not None:
            inputs = inputs + [yes_input]

    if no_stake_amount > 0:
        signatures_needed = signatures_needed + 1
        no_input = spendable_input(no_winner_address, no_stake_amount, MIN_TRANSACTION_FEE/2, MAX_TRANSACTION_FEE/2, settings.get('inputs', None))
        if no_input is not None:
            inputs = inputs + [no_input]

    if (yes_stake_amount > 0 and yes_input is None) or (no_stake_amount > 0 and no_input is None):
        if verbose:
            out.append("The temporary addresses have not yet been fully funded.")
        if (yes_stake_amount > 0 and yes_input is None):
            if am_i_yes_or_no == 'yes':
                if verbose:
                    out.append("Please fund the following (yes):")
            else:
                if verbose:
                    out.append("Please ask the other party to fund the following (yes):")
            if verbose:
                out.append("Yes: %s satoshis to the address %s" % (str(yes_stake_amount), yes_winner_address))

        if (no_stake_amount > 0 and no_input is None):
            if am_i_yes_or_no == 'no':
                if verbose:
                    out.append("Please fund the following (no):")
            else:
                if verbose:
                    out.append("Please ask the other party to fund the following (no):")

            if verbose:
                out.append("No: %s satoshis to the address %s" % (str(no_stake_amount), no_winner_address))
        return out 

    # Fetch the reality key public keys for yes and no.
    req = urllib2.Request(REALITY_KEYS_API % (fact_id))
    response = urllib2.urlopen(req)
    fact_json = simplejson.load(response)
    yes_reality_key = fact_json['yes_pubkey']   
    no_reality_key = fact_json['no_pubkey']

    if settings.get('ecc_voodoo'):

        # Use ECC addition to combine the key of the person who wins on "yes" with the "yes" reality key
        # ...and the key of the person who wins on "no" with the "no" reality key
        # Hopefully this is a safe thing to be doing. Feedback gratefully received...

        # See the discussion on the following thread, in particular this suggestion by Peter Todd:
        # https://bitcointalk.org/index.php?topic=260898.msg3040083#msg3040083

        # TODO: Add a third key for the two parties so that they can settle themselves without Reality Keys if they prefer.
        # Ideally we'd do;
        # 2/4 yes_compound_public_key, no_compound_public_key, yes_winner_public_key, no_winner_public_key
        # If that's non-standard (not sure), we might be able to do:
        # 1/3 yes_compound_public_key, no_compound_public_key, yes_winner_no_winner_compound_public_key
        # ... but this requires that Alice and Bob don't know each other's public keys in advance.

        yes_compound_public_key = add_pubkeys(yes_winner_public_key, yes_reality_key)
        no_compound_public_key = add_pubkeys(no_winner_public_key, no_reality_key)

        multisig_script = mk_multisig_script([yes_compound_public_key, no_compound_public_key], 1, 2)

    else:

        # Default to OP_IF / OP_ELSE logic, but which is cleaner but causes the redeem transaction to fail IsStandard checks.
        multisig_script = mk_multisig_script_if_else([[yes_winner_public_key, yes_reality_key], [no_winner_public_key, no_reality_key]])
        # print deserialize_script(multisig_script)

    pay_to_addr = p2sh_scriptaddr(multisig_script)
    if verbose:
        out.append("Made p2sh address: %s. Creating a transaction to fund it." % (pay_to_addr))

    outputs = [{'value': contract_total_amount, 'address': pay_to_addr}]
    #print "making tx with inputs:"
    #print inputs
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
            raise Exception("The transaction we received was not what we expected.")
        tx = existing_tx
        signatures_done = signatures_done + 1

    #print "Unsigned:"
    #print deserialize(tx)

    # Sign whichever of the inputs we have the private key for. 
    # Since we only allow one input per person, and we add them ourselves, we can assume yes is first and no is second.
    if (am_i_yes_or_no == 'yes') and (yes_stake_amount > 0):
        #print "i am yes, signing 0"
        tx = sign(tx,0,private_key)
        signatures_done = signatures_done + 1
        #print "Signed yes:"
        #print deserialize(tx)

    if (am_i_yes_or_no == 'no') and (no_stake_amount > 0):
        #print "i am no, signing 1"
        tx = sign(tx,1,private_key)
        signatures_done = signatures_done + 1
        #print "Signed no:"
        #print deserialize(tx)

    if signatures_needed == signatures_done:
        if settings.get('no_pushtx', False):
            if verbose:
                out.append("Created the following transaction, but won't broadcast it because you specified --no_pushtx:")
            out.append(tx)
        else:
            if verbose:
                out.append("Broadcasting transaction...:")
                out.append(tx)
                pushtx(tx)
                out.append("Next step: Wait for the result, then the winner runs:")
                out.append("./realitykeysdemo.py claim %s %s %s [<fee>] [<pay_to_address>]" % (fact_id, yes_winner_public_key, no_winner_public_key))
    else:
        if verbose:
            out.append("Created a transaction:")
        out.append(tx)
        if verbose:
            out.append("Next step: The other party runs:")
            out.append("./realitykeysdemo.py setup %s %s %s %s %s %s" % (fact_id, yes_winner_public_key, str(yes_stake_amount), no_winner_public_key, str(no_stake_amount), tx))

    return out

def execute_claim(settings, fact_id, yes_winner_public_key, no_winner_public_key, fee=0, pay_to_address=None):
    """When executed by the winner, creates the P2SH address used in previous contracts and spends the contents to <pay_to_address>
    """

    out = []

    verbose = settings.get('verbose', False)
    seed = settings.get('seed', None)

    private_key = user_private_key(False, seed)
    if pay_to_address is None:
        pay_to_address = pubtoaddr(privtopub(private_key), magic_byte(settings))
    
    # Get the reality keys representing "yes" and "no".
    req = urllib2.Request(REALITY_KEYS_API % (fact_id))
    response = urllib2.urlopen(req)
    fact_json = simplejson.load(response)
    yes_reality_key = fact_json['yes_pubkey']   
    no_reality_key = fact_json['no_pubkey']

    winner = fact_json['winner']
    winner_privkey = fact_json['winner_privkey']

    if winner is None:
        out.append("The winner of this fact has not yet been decided. Please try again later.")
        return out

    if winner_privkey is None:
        out.append("This fact has been decided but the winning key has not been published yet. Please try again later.")
        return out

    if (settings.get('ecc_voodoo')):

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
            raise Exception("An error occurred trying to recreate the expected public keys from the private key supplied, giving up.")

        if winner == "Yes":
            if (yes_compound_public_key != winner_public_key_from_winner_private_key):
                raise Exception("Could not recreate the expected public keys from the private key supplied. Are you sure you won?")
        elif winner == "No":
            if (no_compound_public_key != winner_public_key_from_winner_private_key):
                raise Exception("Could not recreate the expected public keys from the private key supplied, Are you sure you won?.")
        else:
            raise Exception("Expected the winner to be Yes or No, but got \"%s\", now deeply confused, giving up." % (winner))

        multisig_script = mk_multisig_script([yes_compound_public_key, no_compound_public_key], 1, 2)

    else:

        multisig_script = mk_multisig_script_if_else([[yes_winner_public_key, yes_reality_key], [no_winner_public_key, no_reality_key]])
        print "if else script:"
        print deserialize_script(multisig_script)

    # Regenerate the p2sh address we used during setup:
    p2sh_address = p2sh_scriptaddr(multisig_script)

    transactions = [spendable_input(p2sh_address, 0, 0, 0, settings.get('inputs', None))]

    if len(transactions) == 0:
        out.append("There do not seem to be any payments made to this address.")
        return out
    
    val = 0
    for outtrans in transactions:
        # eg [{'output': u'4cc806bb04f730c445c60b3e0f4f44b54769a1c196ca37d8d4002135e4abd171:1', 'value': 50000, 'address': u'1CQLd3bhw4EzaURHbKCwM5YZbUQfA4ReY6'}]
        val = val + outtrans['value']

    if val == 0:
        raise Exception("Nothing to spend.")
        return out

    val = val - fee
    if verbose:
        out.append("Found %s in the P2SH address" % (str(val)))

    outs = [{'value': val, 'address': pay_to_address}]
    tx = mktx(transactions, outs)

    if settings.get('ecc_voodoo'):
        #print deserialize(tx)
        sig1 = multisign(tx,0,multisig_script,winner_compound_private_key)
        multi_tx = apply_multisignatures(tx,0,multisig_script,[sig1])
    else:
        sig1 = multisign(tx,0,multisig_script,private_key)
        sig2 = multisign(tx,0,multisig_script,winner_privkey)
        multi_tx = apply_multisignatures_with_if_hint(tx,0,multisig_script,[sig1, sig2])

    if settings.get('no_pushtx', False):
        if verbose:
            out.append("Created the following transaction, but won't broadcast it because you specified --no_pushtx:")
        out.append(multi_tx)
    else:
        # blockchain.info seems to reject this transaction.
        # confusingly, it seems to go ok with bitcoind
        try:
            pushtx(multi_tx)
        except:
            try:
                eligius_pushtx(multi_tx)
            except:
                if verbose:
                    out.append("We think this should be a valid, standard transaction, but the blockchain.info API won't accept it.")
                    out.append("You can send it with bitcoind instead:")
                    out.append("./bitcoind sendrawtransaction %s" % (multi_tx))
                else: 
                    out.append(multi_tx)

    return out

def execute_pay(settings, pay_to_addr, pay_amount, fee):
    """ Make a simple payment, from a single output, with change.

    You can use this to refund an aborted transaction, if the other user fails to fund their side or fails to complete the P2SH transaction.
    """

    out = []

    seed = settings.get('seed', None)

    private_key = user_private_key(False, seed)
    public_key = privtopub(private_key)
    addr = pubtoaddr(public_key, magic_byte(settings))

    if addr == pay_to_addr:
        if verbose:
            out.append("Paying yourself...")

    spendable_in = spendable_input(addr, pay_amount, fee, 0, settings.get('inputs', None))
    if spendable_in is None:
        raise Exception("Could not find an output to spend, giving up.")

    remainder = spendable_in['value'] - pay_amount - fee 

    outputs = [{'value': pay_amount, 'address': pay_to_addr}]
    if remainder > 0:
        if verbose:
            out.append("Sending %s back to the original address as change." % (str(remainder)))
        change_outputs = [{'value': remainder, 'address': addr}]
        outputs = outputs + change_outputs

    tx = mktx([spendable_in], outputs)
    tx = sign(tx, 0, private_key)

    if no_pushtx:
        if verbose:
            out.append("Created the following transaction, but won't broadcast it because you specified --no_pushtx:")
        out.append(tx)
    else:
        pushtx(tx)

    return out

#########################################################################

def main():

    parser = create_parser()
    args = parser.parse_args()

    settings = {
        'verbose': args.verbose,
        'testnet': args.testnet,
        'no_pushtx': args.no_pushtx,
        'seed': args.seed,
        'inputs': args.inputs
    }

    command = args.command
    if command == "makekeys":
        out = execute_makekeys(settings)
    elif command == "setup":
        out = execute_setup(settings, args.fact_id, args.yes_key, args.yes_stake, args.no_key, args.no_stake, args.transaction)
    elif command == "claim":
        out = execute_claim(settings, args.fact_id, args.yes_key, args.no_key, args.fee, args.pay_to_address)
    elif command == "pay":
        out = execute_pay(settings, args.pay_to_address, args.amount, args.fee)

    print "\n".join(out)

def create_parser():
    parser = argparse.ArgumentParser(
        description='Create, setup or claim a contract using Reality Keys.'
    )

    subparsers = parser.add_subparsers(dest='command',help='Commands: makekeys create claim pay')
    makekeys_parser = subparsers.add_parser('makekeys')
    setup_parser = subparsers.add_parser('setup')
    claim_parser = subparsers.add_parser('claim')
    pay_parser = subparsers.add_parser('pay')

    setup_parser.add_argument( '-y', '--yes-key', required=False, help='The public key of the user representing "yes"')
    setup_parser.add_argument( '-Y', '--yes-stake', type=int, required=False, help='The number of statoshis staked by the party representing "yes"')
    claim_parser.add_argument( '-y', '--yes-key', required=False, help='The public key of the user representing "yes"')

    setup_parser.add_argument( '-n', '--no-key', required=False, help='The public key of the user representing "no"')
    setup_parser.add_argument( '-N', '--no-stake', type=int, required=False, help='The number of statoshis staked by the party representing "no"')
    claim_parser.add_argument( '-n', '--no-key', required=False, help='The public key of the user representing "no"')

    setup_parser.add_argument( '-r', '--fact-id', type=int, required=False, help='The ID of the Reality Keys fact you want to base your contract on (assumes freebase)')
    claim_parser.add_argument( '-r', '--fact-id', type=int, required=False, help='The ID of the Reality Keys fact you want to base your contract on (assumes freebase)')

    setup_parser.add_argument( '-x', '--transaction', required=False, help='A serialized, part-signed transaction')
    claim_parser.add_argument( '-d', '--pay-to-address', required=False, help='The address to send money to (pay and claim)')
    pay_parser.add_argument( '-d', '--pay-to-address', required=False, help='The address to send money to (pay and claim)')


    parser.add_argument( '--no-pushtx', '-P', required=False, action='store_true', help='Do not push tx')
    parser.add_argument( '--seed', '-s', required=False, help='Seed for key generation. If not supplied this will be created automatically and stored.')

    parser.add_argument( '--inputs', '-i', action='append', required=False, default=[], help='The inputs to use in transactions. If not stated we will try to fetch available inputs from the network.')
    parser.add_argument( '--fee', '-f', type=int, required=False, default=DEFAULT_TRANSACTION_FEE, help='The address to send money to (pay and claim)')

    pay_parser.add_argument( '-a', '--amount', type=int, required=False, default=0, help='The amount of money to send (pay and claim)')

    parser.add_argument( '--verbose', '-v', required=False, action='store_true', help='Verbose output')
    parser.add_argument( '--testnet', '-t', required=False, action='store_true', help='Use testnet instead of mainnet. (Some commands will only work with --no-pushtx)')
    setup_parser.add_argument( '-e', '--ecc-voodoo', required=False, help='Use ECC addition to make a standard transaction (May not be safe)')

    return parser

if __name__ == '__main__':
    main()
