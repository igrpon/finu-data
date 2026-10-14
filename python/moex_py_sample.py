#
# this code will load listed (see inside) tickers data from MOEX (via aiomoex) and pupulate that data into postgres database
#
import requests
from sqlalchemy import create_engine
import asyncio
import aiohttp
import aiomoex
import pandas as pd
 
async def load_moex_instruments():
    request_url = "https://iss.moex.com/iss/engines/stock/" "markets/shares/boards/TQBR/securities.json"
    arguments = {"securities.columns": ("SECID," "REGNUMBER," "LOTSIZE," "SHORTNAME")}

    async with aiohttp.ClientSession() as session:
        iss = aiomoex.ISSClient(session, request_url, arguments)
        data = await iss.get()
        df = pd.DataFrame(data["securities"])
        df.set_index("SECID", inplace=True)
        return df
    
async def load_moex_quotes():
    inst_list = ['IMOEX', 'ALRS', 'LKOH', 'MOEX', 'IMOEX', 'RTKM', 'SNGS', 'VTBR', 'GAZP', 'YNDX', 'SBER', 'CNYRUB_TOD', 'EURRUB_TOD', 'USDRUB_TOD']
    start = '2020-01-01'
    end = '2026-09-01'

    df_inst = None
    async with aiohttp.ClientSession() as session:
        for inst in inst_list:
            data = await aiomoex.get_board_candles(
                session,
                security=inst,
                board="index" if inst=='IMOEX' else 'TQBR',
                market="index" if inst=='IMOEX' else 'shares',
                start=start,
                end=end)
            df = pd.DataFrame(data)
            df['secid'] = inst
            if df_inst is None:
                df_inst = df
            else:
                df_inst = pd.concat([df, df_inst], ignore_index=True)

    df_inst['begin'] = pd.to_datetime(df_inst['begin'], format='ISO8601')
    df_inst['end'] = pd.to_datetime(df_inst['end'], format='ISO8601')

    return df_inst

def main():
    # create SQL engine
    # NB! here I assume that there is a local postgres connction with postgres:password credentials, and there is demo schema in that DB
    engine = create_engine("postgresql+psycopg2://postgres:password@localhost/demo")

    #
    #load moex instruments list
    #
    df = asyncio.run( load_moex_instruments() )

    #save it into sql database
    df.columns = df.columns.str.lower()
    df = df.rename_axis("id")
    df.to_sql("instruments", con=engine, schema="moex", if_exists="append", index=True)

    #
    # load quotes
    #
    df = asyncio.run( load_moex_quotes() )

    df.columns = df.columns.str.lower()
    df = df.rename_axis("id")
    df.rename(columns={'begin': 'dt', 'end': 'dt_end'}, inplace=True)
    df.to_sql("quotes", con=engine, schema="moex", if_exists="append", index=True)



main()

"""
#
# add this FK constraint (in case you need ref. integrity)
#

alter table quotes 
    add constraint fk_instruments
    foreign key (secid) 
    REFERENCES instruments (secid);

"""
