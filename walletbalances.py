import json
import subprocess
import requests

def fetch_prices_from_coingecko():
    url = 'https://api.coingecko.com/api/v3/simple/price?ids=tbtc&vs_currencies=usd'
    response = requests.get(url)
    data = response.json()
    price = data['tbtc']['usd']
    return price

def parse_and_insert():
    values_list = []
    command_to_run = "./verus listcurrencies"
    result = subprocess.run(command_to_run, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    data = json.loads(result.stdout)
    for item in data:
        try:
            iid = item["currencydefinition"]["currencyid"]
            name = item["currencydefinition"]["fullyqualifiedname"]
            options = item["currencydefinition"]["options"]
            pp = item["currencydefinition"]["proofprotocol"]
            idfee = item["currencydefinition"]["idregistrationfees"]
            supply = item["bestcurrencystate"]["supply"]
            flag = item["bestcurrencystate"]["flags"]
            rescurrencies = []
            rescurrlist = []
            if int(options) % 2 == 1: 
                rescurrencies = item["bestcurrencystate"]["reservecurrencies"]
                for currency in rescurrencies:
                    try:
                        resiaddy = currency["currencyid"]
                        getcurrency = f"./verus getcurrency {resiaddy}"
                        resinfo = subprocess.run(getcurrency, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
                        resinfo = json.loads(resinfo.stdout)
                        rescurrname = resinfo["fullyqualifiedname"]
                        rescurrlist.append((rescurrname))
                    except KeyError as e:
                        print(f"Key error: {e} not found in item {item} \n")
            values_list.append((iid, name, options, pp, idfee, supply, json.dumps(rescurrencies), json.dumps(rescurrlist), flag))
        except KeyError as e:
            print(f"Key error: {e} not found in item {item} \n")
    return values_list

def getcurrencynamefromid(iaddr):
    getcurrency = f"./verus getcurrency {iaddr}"
    resinfo = subprocess.run(getcurrency, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    resinfo = json.loads(resinfo.stdout)
    name = resinfo["fullyqualifiedname"]
    return name

def getbridgereservesandmcap(rows):
    for row in rows:
        if row[0] == "i3f7tSctFkiPpiedY8QR5Tep9p4qDVebDx":
            try:
                bridgesupply = row[5]
                reservestring = row[6]
                reservejson = json.loads(reservestring)
                for reserve in reservejson:
                    rescurrencyid = reserve["currencyid"]
                    if rescurrencyid == "iGBs4DWztRNvNEJBt4mqHszLxfKTNHTkhM":
                        daisupply = reserve["reserves"]
                        bridgemcap = daisupply*4
                        bridgetokenprice = bridgemcap/bridgesupply
                        return bridgesupply, reservestring, bridgemcap, bridgetokenprice
            except KeyError as e:
                print(f"Key error: {e} not found in item {rows} \n")
        
def getbridgeprices(rows):
    bridgesupply, reservestring, bridgemcap, bridgetokenprice = getbridgereservesandmcap(rows)
    reservejson = json.loads(reservestring)
    for reserve in reservejson:
        rescurrencyid = reserve["currencyid"]
        rescurrencyreserves = reserve["reserves"]
        if rescurrencyid == "i5w5MuNik5NtLcYmNzcvaoixooEebB6MGV":
            veruschainpriceraw = bridgemcap/4/rescurrencyreserves
            veruschainprice = round(veruschainpriceraw,3)
        if rescurrencyid == "iCkKJuJScy4Z6NSDK7Mt42ZAB2NEnAE1o4":
            mkrvethchainpriceraw = bridgemcap/4/rescurrencyreserves
            mkrvethchainprice = round(mkrvethchainpriceraw,3)
        if rescurrencyid == "i9nwxtKuVYX4MSbeULLiK2ttVi6rUEhh4X":
            vethchainpriceraw = bridgemcap/4/rescurrencyreserves
            vethchainprice = round(vethchainpriceraw,3)
    return bridgesupply,bridgemcap,bridgetokenprice,veruschainprice,mkrvethchainprice,vethchainprice

def getbasketcurrencies(rows):
    basketcurrlist = []
    nonrescurrlist = []
    ethmappedcurrlist = []
    for row in rows:
        currid = row[0]
        name = row[1]
        pp = row[3]
        supply = row[5]
        rescurrlist = row[6]
        if rescurrlist:
            basketcurrlist.append((name,currid,supply,rescurrlist))
        if not rescurrlist and pp == 3:
            ethmappedcurrlist.append(name)
        if not rescurrlist and pp != 3 and name != "VRSC":
            nonrescurrlist.append(name)
    return basketcurrlist, ethmappedcurrlist, nonrescurrlist

def finalize_prices(onchainbasketprices,onchainprices):
    basket_mcap = {basket[0]: basket[2] for basket in onchainbasketprices}
    token_baskets = {}
    for token, price, basket in onchainprices:
        if token in token_baskets:
            token_baskets[token].append(basket)
        else:
            token_baskets[token] = [basket]

    for token, baskets in token_baskets.items():
        if len(baskets) > 1:
            total_mcap = sum(basket_mcap[basket] for basket in baskets)
            weighted_price = 0
            for _, price, basket in filter(lambda x: x[0] == token, onchainprices):
                weight = basket_mcap[basket] / total_mcap
                weighted_price += price * weight

            onchainprices.append((token, weighted_price, "weighted"))
    filtered_onchainprices = {}
    for name, price, basket in onchainprices:
        if name not in filtered_onchainprices or basket == "weighted":
            filtered_onchainprices[name] = price

    onchainbasketprices_simple = [(name, price) for name, price, _ in onchainbasketprices]
    onchainprices_simple = [(name, price) for name, price in filtered_onchainprices.items()]
    # Combine the two lists, ensuring unique names
    final_onchainprices = {name: price for name, price in onchainbasketprices_simple + onchainprices_simple}
    final_onchainprices_list = list(final_onchainprices.items())
    return final_onchainprices_list

def test():
    tbtcprice = fetch_prices_from_coingecko()
    rows = parse_and_insert()
    basketcurrlist, ethmappedcurrlist, nonrescurrlist = getbasketcurrencies(rows)
    bridgesupply,bridgemcap,bridgetokenprice,veruschainprice,mkrvethchainprice,vethchainprice = getbridgeprices(rows)
    onchainprices = [
        ('VRSC', veruschainprice, "Bridge.vETH"),
        ('MKR.vETH', mkrvethchainprice, "Bridge.vETH"),
        ('vETH', vethchainprice, "Bridge.vETH"),
        ('DAI.vETH', 1.00, "Bridge.vETH")
    ]
    onchainbasketprices = []
    for baskcurr in basketcurrlist:
        entryname = baskcurr[0]
        entrycurrid = baskcurr[1]
        entrysupply = baskcurr[2]
        entrycurrlist = baskcurr[3]
        vrscresmcap = 0
        dairesmcap = 0
        mkrresmcap = 0
        ethresmcap = 0
        tbtcresmcap = 0
        otherreservelist = []
        if entrysupply == 0:
            continue
        if entrysupply != 0:
            entrycurrlist_loads = json.loads(entrycurrlist)
            for entry in entrycurrlist_loads:
                rescurrencyid = entry["currencyid"]
                rescurrencyweight = entry["weight"]
                rescurrencyreserves = entry["reserves"]
                if rescurrencyid == "i5w5MuNik5NtLcYmNzcvaoixooEebB6MGV":
                    vrscresmcap = rescurrencyreserves*veruschainprice
                if rescurrencyid == "iGBs4DWztRNvNEJBt4mqHszLxfKTNHTkhM":
                    dairesmcap = rescurrencyreserves*1
                if rescurrencyid == "iCkKJuJScy4Z6NSDK7Mt42ZAB2NEnAE1o4":
                    mkrresmcap = rescurrencyreserves*mkrvethchainprice
                if rescurrencyid == "i9nwxtKuVYX4MSbeULLiK2ttVi6rUEhh4X":
                    ethresmcap = rescurrencyreserves*vethchainprice
                if rescurrencyid == "iS8TfRPfVpKo5FVfSUzfHBQxo9KuzpnqLU":
                    tbtcresmcap = rescurrencyreserves*tbtcprice
                if rescurrencyid not in ["i5w5MuNik5NtLcYmNzcvaoixooEebB6MGV","iGBs4DWztRNvNEJBt4mqHszLxfKTNHTkhM","iCkKJuJScy4Z6NSDK7Mt42ZAB2NEnAE1o4","i9nwxtKuVYX4MSbeULLiK2ttVi6rUEhh4X","iS8TfRPfVpKo5FVfSUzfHBQxo9KuzpnqLU"]:
                    otherreservelist.append((entryname,rescurrencyid,rescurrencyweight,rescurrencyreserves))

        reservemcapraw = vrscresmcap+dairesmcap+mkrresmcap+ethresmcap+tbtcresmcap
        reservemcap = round(reservemcapraw,8)
        pricepertokenraw = reservemcapraw/entrysupply
        pricepertoken = round(pricepertokenraw,8)
        onchainbasketprices.append((entryname,pricepertoken,reservemcap))
        if otherreservelist:
            for standalonetoken in otherreservelist:
                basketname = standalonetoken[0] 
                standalonetokenid = standalonetoken[1]
                standalonetokenweight = standalonetoken[2]
                standalonetokensupplyinreserves = standalonetoken[3]
                standalonetokenprice = reservemcap*standalonetokenweight/standalonetokensupplyinreserves
                standalonetokenname = getcurrencynamefromid(standalonetokenid)
                #print(f"In Basket Currency {basketname}, {standalonetokenid} has a current price of {standalonetokenprice}")
                onchainprices.append((standalonetokenname,standalonetokenprice,basketname))
    final_price_list = finalize_prices(onchainbasketprices,onchainprices)
    return final_price_list,tbtcprice

def main():
    finalized_prices, tbtcprice = test()
    for price in finalized_prices:
        currencyname = price[0]
        currencyprice = price[1]
        if currencyname == "Bridge.vETH":
            bridgetokenprice = currencyprice
        if currencyname == "VRSC":
            veruschainprice = currencyprice
        if currencyname == "MKR.vETH":
            mkrvethchainprice = currencyprice
        if currencyname == "vETH":
            vethchainprice = currencyprice
    totalonchainvalue = 0
    result = subprocess.run(['./verus', 'getcurrencybalance', '*'], capture_output=True, text=True)
    try:
        data = json.loads(result.stdout)
        if "VRSC" in data:
            vrscbalance = data["VRSC"]
            vrscvalue = vrscbalance * veruschainprice
            formatted_vrscvalue = round(vrscvalue,2)
            print(f"VRSC Balance: {vrscbalance}, Value: ${formatted_vrscvalue}")
            totalonchainvalue += vrscvalue
        if "Bridge.vETH" in data:
            bridgebalance = data["Bridge.vETH"]
            bridgevalue = bridgebalance * bridgetokenprice
            formatted_bridgevalue = round(bridgevalue,2)
            print(f"Bridge.vETH Balance: {bridgebalance}, Value: ${formatted_bridgevalue}")
            totalonchainvalue += bridgevalue
        if "DAI.vETH" in data:
            daibalance = data["DAI.vETH"]
            formatted_daibalance = round(daibalance,2)
            print(f"DAI Balance: {daibalance}, Value: ${formatted_daibalance}")
            totalonchainvalue += daibalance
        if "MKR.vETH" in data:
            mkrbalance = data["MKR.vETH"]
            mkrvalue = mkrbalance * mkrvethchainprice
            formatted_mkrvalue = round(mkrvalue,2)
            print(f"MKR Balance: {mkrbalance}, Value: ${formatted_mkrvalue}")
            totalonchainvalue += mkrvalue
        if "vETH" in data:
            vethbalance = data["vETH"]
            ethvalue = vethbalance * vethchainprice
            formatted_ethvalue = round(ethvalue,2)
            print(f"vETH Balance: {vethbalance}, Value: ${formatted_ethvalue}")
            totalonchainvalue += ethvalue
        if "tBTC.vETH" in data:
            tbtcbalance = data["tBTC.vETH"]
            tbtcvalue = tbtcbalance * tbtcprice
            formatted_tbtcvalue = round(tbtcvalue,2)
            print(f"tBTC Balance: {tbtcbalance}, Value: ${formatted_tbtcvalue}")
            totalonchainvalue += tbtcvalue

        for key, value in data.items():
            if key not in ["VRSC", "Bridge.vETH", "DAI.vETH", "MKR.vETH", "vETH","tBTC.vETH"]:
                for entry in finalized_prices:
                    entryname = entry[0]
                    entryprice = entry[1]
                    if key == entryname:
                        tokenusdvalue = value * entryprice
                        formatted_tokenusdvalue = round(tokenusdvalue,2)
                        print(f"{entryname} Balance: {value}, Value: ${formatted_tokenusdvalue}")
                        totalonchainvalue += tokenusdvalue
        
        totalonchainUSDvalue = round(totalonchainvalue,2)
        print(f"TOTAL WALLET VALUE: ${totalonchainUSDvalue}")

    except json.JSONDecodeError:
        print("Error: The output is not in JSON format.")
    except Exception as e:
        print(f"An error occurred: {e}")

main()