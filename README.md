# get_back_eth
Collecting eth coins from many addresses to one
Inspired https://github.com/wbobeirne/eth-balance-checker

## Features
- Balance is checked through a contract (up to 1k addresses per 1 request)  
- If the addresses are > 1k, then the script will divide them into parts and will request results one by one  
- You can specify the `fee` manually or set `wait_for_gasprice_value`that the script will wait before starting sending  

## Installing
```
git clone https://github.com/c29r3/get_back_eth.git \ 
&& cd get_back_eth && cp config_example.yml config.yml \
&& pip3 install -r requirements.txt
```

## How to run
1. Place the csv file with addresses and private keys in the same directory  
    Format example:
    ```
    address1;private_key1
    address2;private_key2
    ...
    ```
2. `cp config_example.yml config.yml`
2. Fill out the configuration file `config.yml`
3. Start script `python3 main.py`
