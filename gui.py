from Tkinter import *
from realitykeysdemo import *
from pybitcointools import *
from decimal import Decimal

def ignore():
    parser = create_parser()
    args = parser.parse_args()
    setting_args = vars(args)

    self.settings = {
        'verbose': not setting_args.get('quiet', False),
        'testnet': setting_args.get('testnet', False),
        'seed': setting_args.get('seed', False),
        'no_pushtx': setting_args.get('no_pushtx', False),
        'inputs': setting_args.get('inputs', None)
    }

    command = args.command
    if command == "makekeys":
        out = execute_makekeys(self.settings)
    elif command == "setup":
        out = execute_setup(self.settings, args.realitykey_id, args.yes_key, args.stake_yes, args.no_key, args.stake_no, args.transaction)
    elif command == "claim":
        out = execute_claim(self.settings, args.realitykey_id, args.yes_key, args.no_key, args.fee, args.destination_address)
    elif command == "pay":
        out = execute_pay(self.settings, args.destination_address, args.amount, args.fee)

    print "\n".join(out)


class RealityKeysGUI(Frame):

    def __init__(self, master):
        self.settings = {
            'verbose': True,
            'testnet': False,
            'seed': None,
            'no_pushtx': True,
            'inputs': None,
        }

        seed = self.settings.get('seed', None)
        verbose = self.settings.get('verbose', False)
        priv = user_private_key(True, seed)
        pub = privtopub(priv)
        addr = pubtoaddr(pub, magic_byte(self.settings))

        Frame.__init__(self, master)
        self.grid()
        # self.create_widgets()

        self.priv_label = Label(self, text="Private key")
        self.priv_entry = Entry(self, width=75)
        self.pub_label = Label(self, text="Public key")
        self.pub_entry = Entry(self, width=75)
        self.fund_label = Label(self, text="Address")
        self.fund_entry = Entry(self, width=50)

        self.priv_label.grid(row=0, column=0)
        self.priv_entry.grid(row=0, column=1, columnspan=5, sticky=W)
        self.pub_label.grid(row=1, column=0)
        self.pub_entry.grid(row=1, column=1, columnspan=5, sticky=W)
        self.fund_label.grid(row=2, column=0)
        self.fund_entry.grid(row=2, column=1, columnspan=5, sticky=W)

        self.priv_entry.insert(0, priv)
        self.pub_entry.insert(0, pub)
        self.fund_entry.insert(0, addr)

        self.realitykey_id_label = Label(self, text="Reality Keys ID")
        self.realitykey_id_entry = Entry(self, width=6, validate='key', validatecommand=self.handle_contract_change)
        self.realitykey_id_label.grid(row=4, column=0)
        self.realitykey_id_entry.grid(row=4, column=1)

        self.v = IntVar()
        self.selection_label = Label(self, text="You win on:")
        self.selection_yes = Radiobutton(self, text="Yes", variable=self.v, value=1, command=self.handle_yes_no_change)
        self.selection_no = Radiobutton(self, text="No", variable=self.v, value=0, command=self.handle_yes_no_change)

        self.selection_label.grid(row=5, column=0)
        self.selection_yes.grid(row=5, column=1)
        self.selection_no.grid(row=5, column=3)
        self.selection_yes.select()

        self.stake_label = Label(self, text="Stake")

        self.stake_yes_entry = Entry(self, width=10, justify=RIGHT, validate='key', validatecommand=self.handle_contract_change)
        self.stake_yes_entry.insert(0, '0')

        self.stake_no_entry = Entry(self, width=10, justify=RIGHT, validate='key', validatecommand=self.handle_contract_change)
        self.stake_no_entry.insert(0, '0')

        self.stake_label.grid(row=6, column=0)
        self.stake_yes_entry.grid(row=6, column=1)
        self.stake_no_entry.grid(row=6, column=3)

        self.pub_label = Label(self, text="Public key")
        self.yes_pub_entry = Entry(self, validate='key', validatecommand=self.handle_contract_change)
        self.no_pub_entry = Entry(self, validate='key', validatecommand=self.handle_contract_change)

        self.pub_label.grid(row=7, column=0)
        self.yes_pub_entry.grid(row=7, column=1)
        self.no_pub_entry.grid(row=7, column=3)

        # These will be enabled when we check the radio buttons
        #self.yes_pub_entry.config(state=DISABLED)
        #self.no_pub_entry.config(state=DISABLED)

        self.proposal_tx_label = Label(self, text="Propose") 
        self.proposal_tx_entry = Text(self, height=6) 
        self.proposal_tx_label.grid(row=8, column=0)
        self.proposal_tx_entry.grid(row=8, column=1, columnspan=4)

        self.acceptance_tx_label = Label(self, text="Accept") 
        self.acceptance_tx_entry = Text(self, height=6) 
        self.acceptance_tx_label.grid(row=9, column=0)
        self.acceptance_tx_entry.grid(row=9, column=1, columnspan=4)

        self.broadcast_button = Button(self, text = 'Broadcast', command=self.handle_broadcast)
        self.broadcast_button.grid(row=10, column=2)

        self.handle_yes_no_change()

    def handle_yes_no_change(self):
        if self.v.get() == 1:
            #self.yes_pub_entry.config(state=NORMAL)
            self.yes_pub_entry.delete(0, END)
            self.yes_pub_entry.insert(0,self.pub_entry.get())
            #self.yes_pub_entry.config(state=DISABLED)

            #self.no_pub_entry.config(state=NORMAL)
            self.no_pub_entry.delete(0, END)
            self.no_pub_entry.insert(0, '')

        else:
            #self.no_pub_entry.config(state=NORMAL)
            self.no_pub_entry.delete(0, END)
            self.no_pub_entry.insert(0,self.pub_entry.get())
            #self.no_pub_entry.config(state=DISABLED)

            #self.no_pub_entry.config(state=NORMAL)
            self.yes_pub_entry.delete(0, END)
            self.yes_pub_entry.insert(0, '')

        self.handle_contract_change()

    def handle_contract_change(self):


        is_proposal_ready = True
        is_acceptance_ready = True

        realitykey_id = None
        yes_pub = None
        no_pub = None
        stake_yes_satoshis = 0
        stake_no_satoshis = 0
        #try:

        if self.realitykey_id_entry.get() == '':
            is_proposal_ready = False
        else:
            realitykey_id = int(self.realitykey_id_entry.get())
            if realitykey_id == 0:
                is_proposal_ready = False

        yes_pub = str(self.yes_pub_entry.get())
        no_pub = str(self.no_pub_entry.get())

        if yes_pub == '':
            is_proposal_ready = False

        if no_pub == '':
            is_proposal_ready = False

        if self.stake_yes_entry.get() != '':
            stake_yes_satoshis = int( Decimal(self.stake_yes_entry.get()) * 100000000)

        if self.stake_no_entry.get() != '':
            stake_no_satoshis = int( Decimal(self.stake_no_entry.get()) * 100000000)

        if stake_yes_satoshis < 0:
            is_proposal_ready = False

        if stake_no_satoshis < 0:
            is_proposal_ready = False

        if (stake_yes_satoshis == 0 and stake_no_satoshis == 0):
            is_proposal_ready = False

        # Acceptance has all the same conditions as proposal and then some
        if not is_proposal_ready: 
            is_acceptance_ready = False

        if self.acceptance_tx_entry.get(1.0, END) == '':
            is_acceptance_ready = False

        #except Exception as e:
        #    print e 
        #    is_acceptance_ready = False
        #    is_proposal_ready = False
           
        if is_acceptance_ready:
            out = execute_setup(self.settings, realitykey_id, yes_pub, stake_yes_satoshis, no_pub, stake_no_satoshis, None)
            print out
        else:
            print "not ready"

        return True

    def handle_broadcast(self):
        pass

    def create_widgets(self):
        submit_button = Button(self, text = 'Submit', command=self.handle_submit)
        submit_button.grid()

        self.text = Text(self, width=40, height=1)
        self.text.grid()

        # self.label = Label(self, text = 'This is a label. Oh, yes.')
        # self.label.grid()

    def handle_submit(self):
        self.text.insert(1.0, self.realitykey_id_entry.get())

root = Tk()
root.title('Reality Keys Tool')
root.geometry('800x400')
app = RealityKeysGUI(root)

root.mainloop()
