# get_back_eth
Collecting eth coins from many addresses to one

## Installing
```
git clone https://github.com/c29r3/get_back_eth.git && \ 
cd get_back_eth && cp config_example.yml > config.yml && \
pip3 install -r requirements.txt
```

## How to run
1. Place the csv file with addresses and private keys in the same directory  
    Format example:
    ```
    address1;private_key1\n
    address2;private_key2\n
    ...
    ```
2. Fill out the configuration file `config.yml`
3. Start script ``python3 main.py``