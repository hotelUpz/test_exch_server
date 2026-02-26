import asyncio
import aiohttp
import time

# Настройки
REQUEST_TIMEOUT = 10      # секунд на каждый отдельный запрос
ALL_TASKS_TIMEOUT = 15    # общий мягкий лимит на все запросы вместе

async def fetch_and_log(session, name, url, price_extractor):
    ts = lambda: time.strftime('%H:%M:%S')
    try:
        async with session.get(url, timeout=REQUEST_TIMEOUT) as resp:
            status = resp.status
            print(f"[{ts()}] {name:<8} | Status: {status}", end=" ")

            if status == 200:
                try:
                    data = await resp.json()
                    price_info = price_extractor(data)
                    if price_info is not None:
                        print(f"→ price = {price_info} | OK")
                    else:
                        print(f"→ price = None | OK (no price field)")
                except Exception as je:
                    text = await resp.text()
                    print(f"→ JSON parse error: {je} | raw: {text[:180]}...")
            else:
                text = await resp.text()
                print(f"→ ERROR | {text[:280]}...")

    except asyncio.TimeoutError:
        print(f"[{ts()}] {name:<8} → TIMEOUT ({REQUEST_TIMEOUT}s)")
    except aiohttp.ClientError as ce:
        print(f"[{ts()}] {name:<8} → ClientError: {ce}")
    except Exception as e:
        print(f"[{ts()}] {name:<8} → Exception: {type(e).__name__} {e}")


async def fetch_binance(session):
    url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
    await fetch_and_log(session, "Binance", url,
                        lambda d: d.get("price"))


async def fetch_kucoin(session):
    url = "https://api.kucoin.com/api/v1/market/orderbook/level1?symbol=BTC-USDT"
    await fetch_and_log(session, "KuCoin", url,
                        lambda d: d.get("data", {}).get("price"))


async def fetch_bitget(session):
    url = "https://api.bitget.com/api/v2/spot/market/tickers?symbol=BTCUSDT"
    await fetch_and_log(session, "Bitget", url,
                        lambda d: d.get("data", [{}])[0].get("lastPr"))


async def fetch_phemex(session):
    url = "https://api.phemex.com/md/spot/ticker/24hr?symbol=sBTCUSDT"
    await fetch_and_log(session, "Phemex", url,
                        lambda d: (
                            f"{float(d.get('result', {}).get('lastEp', 0)) / 1e8:.2f}"
                            if d.get('result', {}).get('lastEp') is not None
                            else None
                        ))


async def main():
    start = time.time()
    print(f"[{time.strftime('%H:%M:%S')}] Запуск параллельных запросов к 4 биржам (BTC/USDT)...\n")

    timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        tasks = [
            fetch_binance(session),
            fetch_kucoin(session),
            fetch_bitget(session),
            fetch_phemex(session),
        ]

        try:
            await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=ALL_TASKS_TIMEOUT
            )
        except asyncio.TimeoutError:
            print(f"\n[{time.strftime('%H:%M:%S')}] Общий таймаут {ALL_TASKS_TIMEOUT}с превышен!")

    print(f"\n[{time.strftime('%H:%M:%S')}] Все запросы завершены за {time.time() - start:.2f} сек")


if __name__ == "__main__":
    asyncio.run(main())



# chmod 600 ssh_key.txt
# eval "$(ssh-agent -s)"
# ssh-add ssh_key.txt
# ssh -T git@github.com