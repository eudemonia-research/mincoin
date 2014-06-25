import config
import base64
import ecdsa
import random
import binascii
from cryptonet.standard import SuperTx, Tx
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
        # indexed on the x value of pubkey, as an integer.
        self.privkey = {}
        self.labels = {}

        # hardcode the block reward.
        self.privkey[55066263022277343669578718895168534326250603453777594175500187360389116729240] = 1
        self.labels[55066263022277343669578718895168534326250603453777594175500187360389116729240] = 'block reward'

        # keys.txt format: privkey:pubkey:label
        # save both to avoid recalculation. space is cheap!

        with config.open('keys.txt', 'rb') as f:
            for line in f.readlines():
                privkey, pubkey, label = line.split(b':', 2)
                if privkey:
                    privkey = base64_to_privkey(privkey)
                pubkey = base64_to_pubkey(pubkey)
                x = pubkey.pubkey.point.x()
                label = label.strip()
                self.labels[x] = label.decode('utf-8')
                self.privkey[x] = privkey

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

        x = pubkey.pubkey.point.x()
        self.labels[x] = label
        self.privkey[x] = privkey

        return key_to_base64(pubkey)

    def transactions(self):
        ret = []
        for x, label in self.labels.items():
            ret += my_rpc.get_transactions(x)
        return ret

    def get_balance(self):
        ret = 0
        for x, label in self.labels.items():
            ret += my_rpc.get_balance(x)['balance']
        return ret

    def send(self, to: int, amount: int):
        to = base64_to_pubkey(to).pubkey.point.x()
        if self.get_balance() < amount:
            raise Exception("Not enough funds!")

        for x, label in self.labels.items():
            balance = my_rpc.get_balance(x)['balance']
            if balance > 0:
                amount_from_this_addr = min(amount, balance)
                amount -= amount_from_this_addr

                stx = SuperTx.make(txs=[Tx.make(dapp=b'',
                                                value=amount_from_this_addr,
                                                fee=1,
                                                donation=1,
                                                data=[x.to_bytes(32, 'big')])], signature=Signature.make(r=0, s=0, pubkey_x=0, pubkey_y=0))
                stx.sign(self.privkey[x])
                tx = binascii.hexlify(stx.serialize()).decode()
                my_rpc.push_tx(tx)
