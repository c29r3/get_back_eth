from web3 import Web3, HTTPProvider
import requests
import yaml
from time import sleep
import json
from multiprocessing.dummy import Pool as ThreadPool
import itertools
from tqdm import tqdm

with open("config.yml", 'r') as config:
    cfg = yaml.load(config, Loader=yaml.FullLoader)

eth_provider =            str(cfg["eth_provider_url"])
w3 =                      Web3(HTTPProvider(eth_provider))
file_name =               cfg["file_name"]
csv_delimiter =           str(cfg["csv_delimiter"])
csv_file_name =           file_name + ".csv"
recipient_address =       str(cfg["recipient_address"])
eth_gas_limit =           int(cfg["eth_gas_limit"])
eth_gas_price =           int(cfg["manual_gas_price"] * 1e9)
wait_for_gasprice_value = int(cfg["wait_for_gasprice_value"] * 1e9)
wait_for_gasprice =       str(cfg["wait_for_gasprice"])
sleep_before_tx =         cfg["sleep_before_tx"]
threads_count =           int(cfg["threads_count"])

contract_address = Web3.toChecksumAddress("0x1cc4426e36faeff09963d6b8b2da3b45f2f1deeb")
with open("utils/balance_checker_ABI.json") as f:
    info_json = json.load(f)
abi = info_json
contract = w3.eth.contract(contract_address, abi=abi)


def wait_until_fee_less(current_fee: int) -> int:
    """
    Do not start sending ETH until the fee is less than 'current_fee'
    :param current_fee: int
    :return: value less than current_fee
    """
    if current_fee > wait_for_gasprice_value:
        print(f"Gas price is too high {current_fee} wei\n"
              f"Waiting until the price of the commission decreases. Check period - 1 minute")
        while current_fee > wait_for_gasprice_value:
            sleep(60)
            current_fee = eth_price_gasstation()
            print(f'Current gas price {current_fee / 1e9} wei')
    return current_fee


def list_split(keypairs_list: list, list_size: int = 1000):
    """
    Divides large lists of pairs of addresses and private keys into a list of lists of a thousand items
    :param list_size: number of items in a sublist
    :param keypairs_list: ["address1;private_key1", "address2;private_key2" ...]
    :return: Object <class 'generator'>
    """
    keypairs_len = len(keypairs_list)
    if keypairs_len == 0:
        raise Exception("split_list(): list is empty --> exit")

    elif keypairs_len < list_size:
        return keypairs_list

    elif keypairs_len > list_size:
        for i in range(0, keypairs_len, list_size):
            yield keypairs_list[i:i + list_size]


def contract_check(keypair_list: list, contract_addr=None) -> list:
    """
    Checks the balance of thousands of addresses through a smart contract
    Returns addresses with a balance greater then zero
    :param keypair_list: ["address1;private_key1", "address2;private_key2" ...]
    :param contract_addr: ["0x0000000000000000000000000000000000000000"]
    :return: ["address;private_key;balance_value", ...]
    """

    non_empty_addreses = []
    if contract_addr is None:
        contract_addr = ['0x0000000000000000000000000000000000000000']

    addresses = []
    privs = []
    for i in range(len(keypair_list)):
        addresses.append(Web3.toChecksumAddress(keypair_list[i].split(";")[0]))
        privs.append(keypair_list[i].split(";")[1])

    raw_balance = contract.functions.balances(addresses, contract_addr).call()
    if sum(raw_balance) > 0:
        for i, amount in enumerate(raw_balance):
            if amount > 0:
                # print(f'https://etherscan.io/address/{addresses[i]} {privs[i]} {str(amount)}')
                non_empty_addreses.append([addresses[i], privs[i], str(amount)])
    pbar.update(1)
    return non_empty_addreses


def eth_price_gasstation():
    # getting safelow gas price for ETH from https://ethgasstation.info/
    try:
        req = requests.get("https://ethgasstation.info/api/ethgasAPI.json")
        if req.status_code == 200 and "safeLow" in str(req.content):
            safe_low_price = int(int(req.json()["safeLow"]) / 10 * 1e9)
            return safe_low_price

    except Exception as gas_price_err:
        print("Can't get current gas price --> getting web3 default value")
        return w3.eth.gasPrice


def write_log(string_to_write: str):
    with open(f"{file_name}_log.txt", 'a') as log:
        log.write(string_to_write + '\n')


def read_csv() -> list:
    print(f'Reading file {csv_file_name}...')
    filtered_incorrect = []
    with open(csv_file_name, 'r') as csv_file:
        csv_reader = csv_file.read()
        data_lst = csv_reader.split("\n")

    for line in data_lst:
        if line == "":
            continue
        line = line.split(";")
        addr = line[0]
        priv = line[1]
        if len(addr) != 42 or addr[:2] != "0x" or len(priv) != 64:
            print(f"Incorrect address or private key format {addr}")
            continue
        filtered_incorrect.append(f'{addr};{priv}')

    print(f'Found {len(data_lst)} lines in file {csv_file_name}')
    return filtered_incorrect


def get_actual_nonce(address: str) -> int:
    return w3.eth.getTransactionCount(Web3.toChecksumAddress(address))


def get_eth_balance(address: str) -> int:
    return w3.eth.getBalance(Web3.toChecksumAddress(address))


def get_eth_signed_tx(sender_nonce: int, private_key: str, amount: int) -> str:
    eth_signed_tx = w3.eth.account.signTransaction(dict(
        nonce=sender_nonce,
        gasPrice=eth_gas_price,
        gas=eth_gas_limit,
        to=Web3.toChecksumAddress(recipient_address),
        value=amount,
        data=b'',
      ),
      private_key
    )
    return eth_signed_tx


# read file
csv_data = read_csv()
split_by = 1000
splitted_lst = list(list_split(csv_data, split_by))
pool = ThreadPool(threads_count)
pbar = tqdm(total=len(splitted_lst))
non_empty_lst = pool.map(contract_check, splitted_lst)
# Merge sublists to one entire list
non_empty_lst = list(itertools.chain.from_iterable(non_empty_lst))
print(f'Found {len(non_empty_lst)} non empty addresses')

# Auto detect safelow fee if it NOT manually setup
if eth_gas_price == 0:
    eth_gas_price = eth_price_gasstation()
print(f'Current transaction price in wei: {Web3.fromWei(eth_gas_price, "gwei")}')

# Waiting for low commission to send if it "on" in config
if wait_for_gasprice == "on":
    eth_gas_price = wait_until_fee_less(eth_gas_price)

print(eth_gas_price)
print("Start sending process")
for i in range(0, len(non_empty_lst)):
    addr = non_empty_lst[i][0]
    priv = non_empty_lst[i][1]
    actual_balance = int(non_empty_lst[i][2])
    nonce = get_actual_nonce(addr)
    amount_to_send = actual_balance - (eth_gas_price * eth_gas_limit)
    if amount_to_send <= 0:
        print(f'{i+1} | https://etherscan.io/address/{addr} Insufficient funds {amount_to_send} --> SKIP')
        continue
    print(f'{i+1} | {addr} eth to send: {str(amount_to_send / 1e18)}')

    eth_signed_tx = get_eth_signed_tx(sender_nonce=nonce, private_key=priv, amount=amount_to_send)
    tx_id_bin = w3.eth.sendRawTransaction(eth_signed_tx.rawTransaction)
    tx_id_hex = Web3.toHex(tx_id_bin)
    tx_id = f'TX_ID: https://etherscan.io/tx/{tx_id_hex}'
    print(tx_id)

    write_log(f'{str(i+1)} {tx_id}')
    sleep(sleep_before_tx)
print('end of script')

