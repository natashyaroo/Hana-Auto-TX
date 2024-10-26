import os
import time
import logging
from web3 import Web3
from dotenv import load_dotenv
import random
import pyfiglet
from colorama import Fore, Style, init

init()
load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def center_text(text):
    terminal_width = os.get_terminal_size().columns
    lines = text.splitlines()
    centered_lines = [line.center(terminal_width) for line in lines]
    return "\n".join(centered_lines)

def print_banner():
    banner = pyfiglet.figlet_format("JOMOK LABS", font="slant")
    print(Fore.CYAN + center_text(banner) + Style.RESET_ALL)

description = """
╔══════════════════════════════════════════╗
║             HANA NETWORK                 ║
║            BY : JOMOK LABS               ║
║                                          ║
╚══════════════════════════════════════════╝
"""

network = {
    'name': 'Base',
    'rpc_url': 'https://base.llamarpc.com',
    'chain_id': 8453,
    'contract_address': '0xC5bf05cD32a14BFfb705Fb37a9d218895187376c'
}

wallet = {
    'private_key': os.getenv("PRIVATE_KEY"),
    'address': os.getenv("WALLET_ADDRESS")
}

contract_abi = [
    {
        "constant": False,
        "inputs": [],
        "name": "depositETH",
        "outputs": [],
        "payable": True,
        "stateMutability": "payable",
        "type": "function"
    }
]

def get_optimal_gas_price(web3):
    try:
        latest_block = web3.eth.get_block('latest')
        base_fee = latest_block['baseFeePerGas']
        priority_fee = web3.to_wei(0.005, 'gwei')
        max_fee = int(base_fee * 1.1) + priority_fee
        return priority_fee, max_fee
    except Exception as e:
        logging.error(f"Error getting optimal gas price: {e}")
        return web3.to_wei(0.005, 'gwei'), web3.to_wei(0.1, 'gwei')

def wait_for_transaction_receipt(web3, tx_hash, max_retries=30):
    """Wait for transaction receipt and return status"""
    for _ in range(max_retries):
        try:
            receipt = web3.eth.get_transaction_receipt(tx_hash)
            if receipt is not None:
                return receipt['status']  
        except Exception as e:
            pass
        time.sleep(1)
    return None

def format_tx_output(tx_hash, status):
    """Format transaction output with status"""
    status_str = ""
    if status == 1:
        status_str = Fore.GREEN + "SUCCESS" + Style.RESET_ALL
    elif status == 0:
        status_str = Fore.RED + "FAILED" + Style.RESET_ALL
    else:
        status_str = Fore.YELLOW + "PENDING" + Style.RESET_ALL
    
    return f"Network: {network['name']} | Tx Hash: {tx_hash} | Status: {status_str}"

def deposit_to_contract(network, private_key, from_address, amount_in_eth):
    web3 = Web3(Web3.HTTPProvider(network['rpc_url']))
    retries = 3
    
    for attempt in range(retries):
        if web3.is_connected():
            break
        elif attempt < retries - 1:
            time.sleep(5) 
            logging.warning(f"Retrying connection... ({attempt + 1}/{retries})")
        else:
            logging.error(f"Failed to connect to {network['name']} after {retries} attempts.")
            return None, None

    contract = web3.eth.contract(address=network['contract_address'], abi=contract_abi)
    nonce = web3.eth.get_transaction_count(from_address)
    transaction_value = web3.to_wei(amount_in_eth, 'ether')
    
    try:
        gas_estimate = contract.functions.depositETH().estimate_gas({
            'from': from_address,
            'value': transaction_value
        })
        gas_limit = int(gas_estimate * 1.05)
    except Exception as e:
        logging.error(f"Error estimating gas: {e}")
        return None, None

    max_priority_fee_per_gas, max_fee_per_gas = get_optimal_gas_price(web3)

    estimated_gas_cost = web3.from_wei(max_fee_per_gas * gas_limit, 'ether')
    print(Fore.YELLOW + f"Estimated gas cost: {estimated_gas_cost:.8f} ETH" + Style.RESET_ALL)

    balance = web3.eth.get_balance(from_address)
    total_cost = transaction_value + (gas_limit * max_fee_per_gas)
    
    if balance < total_cost:
        logging.error(f"Insufficient funds. Balance: {web3.from_wei(balance, 'ether')} ETH, Required: {web3.from_wei(total_cost, 'ether')} ETH")
        return None, None

    transaction = contract.functions.depositETH().build_transaction({
        'nonce': nonce,
        'value': transaction_value,
        'gas': gas_limit,
        'maxFeePerGas': max_fee_per_gas,
        'maxPriorityFeePerGas': max_priority_fee_per_gas,
        'chainId': network['chain_id'],
    })

    try:
        signed_txn = web3.eth.account.sign_transaction(transaction, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
        tx_hash_hex = web3.to_hex(tx_hash)
        
        tx_status = wait_for_transaction_receipt(web3, tx_hash)
        
        return tx_hash_hex, tx_status
    except Exception as e:
        logging.error(f"Transaction error: {e}")
        return None, None

def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    print_banner()
    print(Fore.GREEN + center_text(description) + Style.RESET_ALL)
    print("\n")
    while True:
        try:
            num_transactions = int(input(Fore.YELLOW + "Enter number of transactions to perform: " + Style.RESET_ALL))
            if num_transactions > 0:
                break
            print(Fore.RED + "Please enter a positive number." + Style.RESET_ALL)
        except ValueError:
            print(Fore.RED + "Please enter a valid number." + Style.RESET_ALL)

    amount_in_eth = 0.00000000001
    interval = random.randint(20, 90)
    
    transaction_count = 0
    successful_count = 0
    
    print("\n" + Fore.CYAN + "Starting transactions..." + Style.RESET_ALL + "\n")

    while transaction_count < num_transactions:
        start_time = time.time()

        print(Fore.YELLOW + f"Processing transaction {transaction_count + 1}/{num_transactions}" + Style.RESET_ALL)
        
        tx_hash, tx_status = deposit_to_contract(network, wallet['private_key'], wallet['address'], amount_in_eth)

        end_time = time.time()
        duration = end_time - start_time

        if tx_hash:
            print(format_tx_output(tx_hash, tx_status))
            if tx_status == 1:
                successful_count += 1
            transaction_count += 1
        else:
            print(Fore.RED + "Transaction failed to submit" + Style.RESET_ALL)

        print(Fore.CYAN + f"Transaction execution time: {duration:.2f} seconds" + Style.RESET_ALL)
        print(Fore.YELLOW + f"Waiting {interval} seconds before next transaction..." + Style.RESET_ALL + "\n")
        
        if transaction_count < num_transactions:
            time.sleep(interval)

    print(Fore.GREEN + f"\n✅ Completed {successful_count}/{num_transactions} transactions successfully!" + Style.RESET_ALL)

if __name__ == "__main__":
    main()