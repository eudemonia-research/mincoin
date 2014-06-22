import config
import base64
import ecdsa
import random
from rpc import RPC


my_rpc = RPC()
system_random = random.SystemRandom()


def key_to_base64(key):
    return base64.b64encode(key.to_string()).decode('utf-8')


def base64_to_privkey(string):
    return ecdsa.SigningKey.from_string(base64.b64decode(string), curve=ecdsa.SECP256k1)


def base64_to_pubkey(string):
    return ecdsa.VerifyingKey.from_string(base64.b64decode(string), curve=ecdsa.SECP256k1)


class Wallet:
    def __init__(self):
        # indexed on base64 version of pubkey
        self.privkey = {}
        self.labels = {}

        # keys.txt format: privkey:pubkey:label
        # save both to avoid recalculation. space is cheap!

        with config.open('keys.txt', 'rb') as f:
            for line in f.readlines():
                privkey, pubkey, label = line.split(b':', 2)
                if privkey:
                    privkey = base64_to_privkey(privkey)
                pubkey = base64_to_pubkey(pubkey)
                label = label.strip()
                self.labels[key_to_base64(pubkey)] = label.decode('utf-8')
                self.privkey[key_to_base64(pubkey)] = privkey

    def generate_address(self, label: str):
        label = label.strip()
        assert '\n' not in label

        # TODO: introduce extra entropy
        secret = system_random.randrange(ecdsa.SECP256k1.order)

        privkey = ecdsa.SigningKey.from_secret_exponent(secret, curve=ecdsa.SECP256k1)
        pubkey = privkey.get_verifying_key()

        # add it to keys.txt (see format above in __init__)
        with config.open('keys.txt', 'ab') as f:
            output = key_to_base64(privkey) + ':'
            output += key_to_base64(pubkey) + ':'
            output += label + '\n'
            f.write(output.encode('utf-8'))

        self.labels[key_to_base64(pubkey)] = label
        self.privkey[key_to_base64(pubkey)] = privkey

        return key_to_base64(pubkey).decode('utf-8')

    def transactions(self):
        ret = []
        for pubkey, label in self.labels.items():
            ret += my_rpc.get_transactions(pubkey)
        return ret

    def get_balance(self):
        ret = 0
        for pubkey, label in self.labels.items():
            ret += my_rpc.get_balance(pubkey)
        return ret

    def send(self, to, amount):
        if self.get_balance() < amount:
            raise Exception("Not enough funds!")

        for pubkey, label in self.labels.items():
            balance = my_rpc.get_balance(pubkey)
            if balance > 0:
                amount_from_this_addr = min(amount, balance)
                amount -= amount_from_this_addr
                my_rpc.broadcast_transaction(pubkey, to, amount_from_this_addr, 'ignored for now')
