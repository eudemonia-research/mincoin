from werkzeug.wrappers import Request, Response
from werkzeug.serving import run_simple
from collections import defaultdict

from jsonrpc import JSONRPCResponseManager, dispatcher

balance = defaultdict(int)

# private key for this pubkey is: lF30UsdZuaEsnfO3mmB22yjqsSC4+yLWiozYcTMj48g=

balance['BKJnfE/WWoRpmXwhcyY7Z5IjBVYaFc2A1to27hNpTgqi6jJ0FOURnSPm6YyKYdOdBumM4FgIZUUeU5kUUrVDCQ=='] = 1000

# contains other_address, delta (to the account that it is indexed by)
transactions = defaultdict(list)

def get_balance(pubkey):
    return balance[pubkey]

def get_transactions(pubkey):
    return [{'other': x, 'delta': y} for x, y in transactions[pubkey]]

def broadcast_transaction(frm, to, amount, signature):
    print(frm,to,amount,signature)
    # In mincoin this might look something like
    # Transaction.make(sender=frm, recipient=to, amount=amount, signature=signature)
    # if it's invalid, throw an error. Encodium objects should be valid at all times.
    balance[frm] -= amount
    balance[to] += amount
    transactions[frm].append((to, -amount))
    transactions[to].append((frm, amount))
    return True

@Request.application
def application(request):
     # Dispatcher is dictionary {<method_name>: callable}
    for func in [get_balance, get_transactions, broadcast_transaction]:
        dispatcher[func.__name__] = func

    response = JSONRPCResponseManager.handle(request.data, dispatcher)
    return Response(response.json, mimetype='application/json')


if __name__ == '__main__':
    run_simple('localhost', 2737, application)
