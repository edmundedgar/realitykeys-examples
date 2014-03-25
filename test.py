#!/usr/bin/python

import realitykeysdemo
import unittest
from unittest import TestCase
from pybitcointools import * # https://github.com/vbuterin/pybitcointools

class RealityKeysDemoTestCast(TestCase):

    # You can leave these as they are if you like, but don't be surprised if your transactions get spent out from under you while you're working on them...
    bob_seed = 'bob-082b113a7e2a5c6c1c9c682b8b25087c'
    bob_pub = '0460d353f4c834bccd1a0e690dc5b7a3c0e07f1ed916f05234ea539c08c0792f3ee90b7704a329e6e0a9e4cda2eb156ac6b1721f53a308d2bda2cce56efa925ddd'
    bob_addr_mainnet = '12fai6JhCHKGdDpJCM8ej3g7RySThdMxCD'
    bob_addr_testnet = 'mhBY19Pg1JkXQLHuuv72YxtSHy3Acje1NJ'

    alice_seed = 'alice-7d267a6b6b7bd0460fcd4a37208dea46'
    alice_pub = '04e08a571e7a61d03fb293be00a8a3e106dfc78cc47e6ef7e088850f3883b22deaa4c904b7e9e96f6ce70a2e9c7a060374f3bbf3d5b081d68d98e6e73ec0093b22'
    alice_addr_testnet = 'mraEF8MUVhpXuXVJDNhM11n9ZbfPiPa8Kh'

    yes_fact_id = 3
    no_fact_id = 1

    # We'll use some actual testnet inputs to walk through some actual transactions.
    # The test won't actually try to send them to the network - it's too late now because they're already spent.
    # But we can use them to check that the script is still producing the same transactions that it was before.
    # If you alter these to make your own transactions, don't forget to make sure the output id (before the amount) is correct, as it's normally assigned randomly.

    ecc_inputs = ["mhBY19Pg1JkXQLHuuv72YxtSHy3Acje1NJ:98b6cda0652dabd38a41ab454fac05714ca2ecf29af22ac351c3fb245b57a32e:0:100000",       
            "mraEF8MUVhpXuXVJDNhM11n9ZbfPiPa8Kh:99cbbbdaf1d1d8d58289f2e5a22d00bc2e6ee4132ed330e21d9b0919ff9b3940:1:100000"]

    normal_inputs_yes_wins = ["mhBY19Pg1JkXQLHuuv72YxtSHy3Acje1NJ:dfa44665e0ffc32a2ee237012f2720733c6aad01ba3b1bb6d53b7e39f12999ed:0:100000",       
            "mraEF8MUVhpXuXVJDNhM11n9ZbfPiPa8Kh:67f1b6d63b52b8ea9f7fb5b8169980f4b243780bb82c122137685296567bd0f7:0:100000"]

    normal_inputs_no_wins = ["mhBY19Pg1JkXQLHuuv72YxtSHy3Acje1NJ:75d7ef20bb0824916cda49d4155d4dc667d2c034480db96dd2643b3abf1f3d1c:0:100000",       
            "mraEF8MUVhpXuXVJDNhM11n9ZbfPiPa8Kh:9600005096047e9080089453878e664138fcfbba3070af3df608f538bb43d500:1:100000"]

    # The transaction as completed by setup
    ecc_claimable_tx = '010000000240399bff19099b1de230d32e13e46e2ebc002da2e5f28982d5d8d1f1dabbcb99010000008a473044022033affa6041c1682eced141b93089240e8f9a17619a9d57be2dccb6e60a72ff2302200e2d12008f1b4ef935b9d1d65264ce6d9725367ae012455b78d6ba97fff8ac0e014104e08a571e7a61d03fb293be00a8a3e106dfc78cc47e6ef7e088850f3883b22deaa4c904b7e9e96f6ce70a2e9c7a060374f3bbf3d5b081d68d98e6e73ec0093b22ffffffff2ea3575b24fbc351c32af29af2eca24c7105ac4f45ab418ad3ab2d65a0cdb698000000008c493046022100be1d6ac87a95d3c0fc785b2c4ef2c7f9f65fea366a73279f631e87b356785896022100ce73f9bdb28ac5fea1b1fedd19e7974d29ef4cf3c9a43a03a4dcdbe969532b6101410460d353f4c834bccd1a0e690dc5b7a3c0e07f1ed916f05234ea539c08c0792f3ee90b7704a329e6e0a9e4cda2eb156ac6b1721f53a308d2bda2cce56efa925dddffffffff0120bf02000000000017a914f6641de65e2bf13639f38bd1524cc0e56e065f068700000000'

    normal_claimable_tx_yes_wins = '0100000002f7d07b569652683721122cb80b7843b2f4809916b8b57f9feab8523bd6b6f167000000008a47304402204021138c11c627a1b46eb37f583dde39e425d842ab4ba59fa111cc07044a748b0220503d88c6d9fb9c526f99707db8bf0230bca2f66d8ac3673c877b7c96b06f728c014104e08a571e7a61d03fb293be00a8a3e106dfc78cc47e6ef7e088850f3883b22deaa4c904b7e9e96f6ce70a2e9c7a060374f3bbf3d5b081d68d98e6e73ec0093b22ffffffffed9929f1397e3bd5b61b3bba01ad6a3c7320272f0137e22e2ac3ffe06546a4df000000008b48304502200d6207237691d73940a82d471a06e954964d08772c84ce02b15ed95bb59d167a0221009d79e73528fe3d5c97bc4e434c742a705f95f5f8704c7cf3da8a078b8cad107001410460d353f4c834bccd1a0e690dc5b7a3c0e07f1ed916f05234ea539c08c0792f3ee90b7704a329e6e0a9e4cda2eb156ac6b1721f53a308d2bda2cce56efa925dddffffffff0120bf02000000000017a914274bb9146052f35467c30b9280ac624108b4f6d78700000000'

    normal_claimable_tx_no_wins = '010000000200d543bb38f508f63daf7030bafbfc3841668e8753940880907e049650000096010000008b483045022100c89e5cd23ab7a77b22a41881c4c9a9fb7110b7da890bbc6f2a0c21bfcf3e2eb202202ba9ba1c9838bd6fecaf3de5fe1920ed1d2c12784ca244467ba70ea3429f0f10014104e08a571e7a61d03fb293be00a8a3e106dfc78cc47e6ef7e088850f3883b22deaa4c904b7e9e96f6ce70a2e9c7a060374f3bbf3d5b081d68d98e6e73ec0093b22ffffffff1c3d1fbf3a3b64d26db90d4834c0d267c64d5d15d449da6c912408bb20efd775000000008a473044022049e24454c87e9c06e50a1d487447dc209b96ecc55aab1624d59d74d4843b7ac7022048a0850c3d0e3a7bad0468d5e45f3979ca1640ac8703602d0089feae1819c4ae01410460d353f4c834bccd1a0e690dc5b7a3c0e07f1ed916f05234ea539c08c0792f3ee90b7704a329e6e0a9e4cda2eb156ac6b1721f53a308d2bda2cce56efa925dddffffffff0120bf02000000000017a914845f1892439aa1282a78644c43893ce694360c8d8700000000'

    ecc_claim_tx = '0100000001477a55f2f8cc1df96812a1257f5205747f3fe6b6dd5aad3f1b5da3c4baecaa0500000000d3004830450220080389b3c32f8db64bd2e90cd5b31f120ced55bc2b117fab0a679588df90e871022100d7f427d438b26018ce442cf2d8aaa3257bc4ce28c0953ccc11bbd8c5cc1297af014c87514104cd0298cfa9c3bb885ed42159f2ec3a5cc6cc294a022ce5dff8806fb5101b858e184f2d334996ff207d2f0dac386ad47bba1fa84269443be03cd376aae77002cc4104465d674476158492cf262cb9a3c7135ea9c16ea5c6e380828ddc521524360db67bb8138e358253ef20c040cdd43d80a2430b09c415dc3f6b9ddcbd07ab2cfed152aeffffffff0120bf0200000000001976a9147947f20d56ea47e518dce3ce23b604e45e3a959f88ac00000000'

    normal_claim_tx_yes_wins = '0100000001ac32dc8f5ad1425b52cd33c645d93f4d0bfc877909ea87f443b197693f60126400000000fd65010047304402204b728a8d5df16001b4481d89083ae3f169d4e46ee8487b7e6e5dc5ed5688eea902206600ea4fc69cbb22695d3313f40b3008cb7ec90de676038439001a5de893f2300147304402207449229680a5e6d42ed83c452e7fe9f158b8f66b5d366f236d5b982b130bf4a7022010495bd101faad2a96f0e0529866dfe9f61e25779f7f48c24e1e3566ee8b206e01514cd163524104e08a571e7a61d03fb293be00a8a3e106dfc78cc47e6ef7e088850f3883b22deaa4c904b7e9e96f6ce70a2e9c7a060374f3bbf3d5b081d68d98e6e73ec0093b22210339c1817d51455acebcd4f6c0d0dcda537becf2d2ac34f4209cd31e28cab6d19552ae6752410460d353f4c834bccd1a0e690dc5b7a3c0e07f1ed916f05234ea539c08c0792f3ee90b7704a329e6e0a9e4cda2eb156ac6b1721f53a308d2bda2cce56efa925ddd2102882b16fb1e677ed36d73c64db841dad33df045771596285988428f59a8e3e34652ae68ffffffff0120bf0200000000001976a9147947f20d56ea47e518dce3ce23b604e45e3a959f88ac00000000'

    normal_claim_tx_no_wins = '0100000001a3f0c901f726db5127fa45e74d23c30ea7a65e65eecded5c15f1f6d2c4b0827500000000fd6901004930460221008328683009415759039a726fb887856b89d98798bed4ab471071999f29b8c0930221009a2c8ac22d6e55505abaaad78f97c14cc11605e6cdf4eb8fce65cf6a491e608001493046022100ec49e507275dad01011de967b5f4294a3dd29f7eee81597bf3e02751475fe234022100fae39d29f588001dca3c9aef384ff30da7e33333621244d580c9539a2c0b1f5601004cd163524104e08a571e7a61d03fb293be00a8a3e106dfc78cc47e6ef7e088850f3883b22deaa4c904b7e9e96f6ce70a2e9c7a060374f3bbf3d5b081d68d98e6e73ec0093b222103ea19d70a96a072a1881a6177ab47144168f19f9648675eb189e35e4bde4b16cd52ae6752410460d353f4c834bccd1a0e690dc5b7a3c0e07f1ed916f05234ea539c08c0792f3ee90b7704a329e6e0a9e4cda2eb156ac6b1721f53a308d2bda2cce56efa925ddd21036d4f24332e9c49861591558f074a112f9718e47383c394106325ac5b65b9cd3052ae68ffffffff0120bf0200000000001976a9141244121c9220e72451a8200497f0f4fa1eed0e3788ac00000000'

    def test_make_keys(self):

        alice_priv = realitykeysdemo.user_private_key(False, self.alice_seed)
        self.assertEqual( privtopub(alice_priv), self.alice_pub)
        self.assertEqual( pubtoaddr(privtopub(alice_priv), 111), self.alice_addr_testnet)

        bob_priv = realitykeysdemo.user_private_key(False, self.bob_seed)
        self.assertEqual( privtopub(bob_priv), self.bob_pub)

        settings = {
            'seed': self.bob_seed,
            'ecc_voodoo': True
        }
        out = realitykeysdemo.execute_makekeys(settings)
        self.assertEqual( out[0], self.bob_pub)
        self.assertEqual( out[1], self.bob_addr_mainnet)

        settings['testnet'] = True
        out = realitykeysdemo.execute_makekeys(settings)
        self.assertEqual( out[0], '0460d353f4c834bccd1a0e690dc5b7a3c0e07f1ed916f05234ea539c08c0792f3ee90b7704a329e6e0a9e4cda2eb156ac6b1721f53a308d2bda2cce56efa925ddd')
        self.assertNotEqual( out[1], self.bob_addr_mainnet)
        self.assertEqual( out[1], self.bob_addr_testnet)

    def test_unspent_outputs(self):
        addr = "mhBY19Pg1JkXQLHuuv72YxtSHy3Acje1NJ"
        ret = realitykeysdemo.unspent_outputs(addr, self.ecc_inputs)
        self.assertEqual(len(ret), 1)
        o = ret[0]
        self.assertEqual(o['address'], addr)
        self.assertEqual(o['value'], 100000)
        self.assertEqual(o['output'], "98b6cda0652dabd38a41ab454fac05714ca2ecf29af22ac351c3fb245b57a32e:0")

        addr = "mraEF8MUVhpXuXVJDNhM11n9ZbfPiPa8Kh"
        ret = realitykeysdemo.unspent_outputs(addr, self.ecc_inputs)
        self.assertEqual(len(ret), 1)
        o = ret[0]
        self.assertEqual(o['address'], addr)
        self.assertEqual(o['value'], 100000)
        self.assertEqual(o['output'], "99cbbbdaf1d1d8d58289f2e5a22d00bc2e6ee4132ed330e21d9b0919ff9b3940:1")

    def test_setup_ecc_voodoo(self):
        settings = {
            'seed': self.alice_seed,
            'testnet': True,
            'no_pushtx': True,
            'ecc_voodoo': True
        }

        # This should fail because we can't get the inputs for testnet even if they're there...
        self.assertRaises(Exception, realitykeysdemo.execute_setup, settings, self.yes_fact_id, self.alice_pub, 90000, self.bob_pub, 90000, None)

        settings['inputs'] = self.ecc_inputs
        out = realitykeysdemo.execute_setup(settings, self.yes_fact_id, self.alice_pub, 90000, self.bob_pub, 90000, None)
        alice_tx = out[0]
        alice_tx_obj = deserialize(alice_tx)
        #print tx_obj
        self.assertEqual(180000, alice_tx_obj['outs'][0]['value'])

        settings['seed'] = self.bob_seed
        #settings['verbose'] = True
        out = realitykeysdemo.execute_setup(settings, self.yes_fact_id, self.alice_pub, 90000, self.bob_pub, 90000, alice_tx)
        bob_tx = out[0]
        bob_tx_obj = deserialize(bob_tx)
        self.assertEqual(180000, bob_tx_obj['outs'][0]['value'])
        self.assertNotEqual(alice_tx, bob_tx)

        self.assertEqual(self.ecc_claimable_tx, bob_tx)

    def test_setup_normal(self):
        settings = {
            'seed': self.alice_seed,
            'testnet': True,
            'no_pushtx': True,
            'ecc_voodoo': False
        }

        # This should fail because we can't get the inputs for testnet even if they're there...
        self.assertRaises(Exception, realitykeysdemo.execute_setup, settings, self.yes_fact_id, self.alice_pub, 90000, self.bob_pub, 90000, None)

        settings['inputs'] = self.normal_inputs_yes_wins
        out = realitykeysdemo.execute_setup(settings, self.yes_fact_id, self.alice_pub, 90000, self.bob_pub, 90000, None)
        alice_tx = out[0]
        alice_tx_obj = deserialize(alice_tx)
        #print tx_obj
        self.assertEqual(180000, alice_tx_obj['outs'][0]['value'])

        settings['seed'] = self.bob_seed
        #settings['verbose'] = True
        out = realitykeysdemo.execute_setup(settings, self.yes_fact_id, self.alice_pub, 90000, self.bob_pub, 90000, alice_tx)
        bob_tx = out[0]
        bob_tx_obj = deserialize(bob_tx)
        self.assertEqual(180000, bob_tx_obj['outs'][0]['value'])
        self.assertNotEqual(alice_tx, bob_tx)

        #print deserialize(bob_tx)
        #print "bob tx"
        #print bob_tx
        self.assertEqual(self.normal_claimable_tx_yes_wins, bob_tx)

        # Now see if Bob can win one.
        settings['seed'] = self.alice_seed
        settings['inputs'] = self.normal_inputs_no_wins
        out = realitykeysdemo.execute_setup(settings, self.no_fact_id, self.alice_pub, 90000, self.bob_pub, 90000, None)
        alice_tx = out[0]
        alice_tx_obj = deserialize(alice_tx)
        #print tx_obj
        self.assertEqual(180000, alice_tx_obj['outs'][0]['value'])

        settings['seed'] = self.bob_seed
        #settings['verbose'] = True
        out = realitykeysdemo.execute_setup(settings, self.no_fact_id, self.alice_pub, 90000, self.bob_pub, 90000, alice_tx)
        bob_tx = out[0]
        bob_tx_obj = deserialize(bob_tx)
        self.assertEqual(180000, bob_tx_obj['outs'][0]['value'])
        #print "bob tx (no)"
        #print bob_tx
        self.assertNotEqual(alice_tx, bob_tx)

    def test_claim_ecc_voodoo(self):
        settings = {
            'seed': self.alice_seed,
            'testnet': True,
            'no_pushtx': True,
            'ecc_voodoo': True
        }
        previous_tx_obj = deserialize(self.ecc_claimable_tx)
        previous_tx_hash = txhash(self.ecc_claimable_tx)
        self.assertEqual('05aaecbac4a35d1b3fad5addb6e63f7f7405527f25a11268f91dccf8f2557a47', previous_tx_hash)
        spendable_outputs = ['' + ':' + previous_tx_hash + ':' + '0' + ':' + '180000']
        settings['inputs'] = spendable_outputs

        out = realitykeysdemo.execute_claim(settings, self.yes_fact_id, self.alice_pub, self.bob_pub)
        tx = out[0]
        self.assertEqual(tx, self.ecc_claim_tx)

        settings = {
            'seed': self.bob_seed,
            'testnet': True,
            'no_pushtx': True,
            'ecc_voodoo': True
        }
        previous_tx_obj = deserialize(self.ecc_claimable_tx)
        previous_tx_hash = txhash(self.ecc_claimable_tx)
        self.assertEqual('05aaecbac4a35d1b3fad5addb6e63f7f7405527f25a11268f91dccf8f2557a47', previous_tx_hash)
        spendable_outputs = ['' + ':' + previous_tx_hash + ':' + '0' + ':' + '180000']
        settings['inputs'] = spendable_outputs

        # Loser shouldn't win
        self.assertRaises(Exception, realitykeysdemo.execute_claim, settings, self.yes_fact_id, self.alice_pub, self.bob_pub)

    def test_claim_normal(self):
        settings = {
            'seed': self.alice_seed,
            'testnet': True,
            'no_pushtx': True,
            'ecc_voodoo': False
        }
        previous_tx_obj = deserialize(self.normal_claimable_tx_yes_wins)
        previous_tx_hash = txhash(self.normal_claimable_tx_yes_wins)
        #self.assertEqual('f047d17c6e0149965234c445966d2be05c151e4bb1641b1f7195871746accb92', previous_tx_hash)
        spendable_outputs = ['' + ':' + previous_tx_hash + ':' + '0' + ':' + '180000']
        settings['inputs'] = spendable_outputs

        out = realitykeysdemo.execute_claim(settings, self.yes_fact_id, self.alice_pub, self.bob_pub)
        tx = out[0]
        #print "no ecc claim:"
        #print tx
        self.assertEqual(tx, self.normal_claim_tx_yes_wins)

        settings = {
            'seed': self.bob_seed,
            'testnet': True,
            'no_pushtx': True,
            'ecc_voodoo':False 
        }
        previous_tx_obj = deserialize(self.normal_claimable_tx_yes_wins)
        previous_tx_hash = txhash(self.normal_claimable_tx_yes_wins)
        #self.assertEqual('05aaecbac4a35d1b3fad5addb6e63f7f7405527f25a11268f91dccf8f2557a47', previous_tx_hash)
        spendable_outputs = ['' + ':' + previous_tx_hash + ':' + '0' + ':' + '180000']
        settings['inputs'] = spendable_outputs

        # Loser shouldn't win
        #self.assertRaises(Exception, realitykeysdemo.execute_claim, settings, self.yes_fact_id, self.alice_pub, self.bob_pub)


        # Now see if Bob can win one
        settings['seed'] = self.bob_seed
        previous_tx_obj = deserialize(self.normal_claimable_tx_no_wins)
        previous_tx_hash = txhash(self.normal_claimable_tx_no_wins)
        self.assertEqual('7582b0c4d2f6f1155cedcdee655ea6a70ec3234de745fa2751db26f701c9f0a3', previous_tx_hash)
        spendable_outputs = ['' + ':' + previous_tx_hash + ':' + '0' + ':' + '180000']
        settings['inputs'] = spendable_outputs

        out = realitykeysdemo.execute_claim(settings, self.no_fact_id, self.alice_pub, self.bob_pub)
        tx = out[0]
        self.assertEqual(tx, self.normal_claim_tx_no_wins)



def main():
    unittest.main() 

if __name__ == '__main__':
    main()
