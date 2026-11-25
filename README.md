# geizhals-watch

Watches prices on [geizhals.de](https://geizhals.de) and sends a Telegram message when one drops.
One Python file, standard library only, no API key for Geizhals needed.

## Setup

1. Copy `watchlist.example.json` to `watchlist.json` and add the Geizhals product pages you care about.
   `target` is optional.
2. Optional: set `TELEGRAM_TOKEN` (from @BotFather) and `TELEGRAM_CHAT_ID`. Without them it only prints.
3. Run it on a schedule, e.g. twice a day:

```bash
python geizhals_watch.py --test   # self-test, no network
python geizhals_watch.py          # check once
# cron: 0 8,18 * * * cd /opt/geizhals-watch && python3 geizhals_watch.py >> watch.log 2>&1
```

## When it messages you

- 📉 the price falls below the lowest price it has seen so far
- 🎯 the price reaches your `target` (once, not every run)

The first price of a new item is only remembered. If Telegram fails, the state is not updated,
so the next run reports the drop again instead of losing it.

`state.json` keeps the last 60 prices per item if you want to chart them.

## Limits

It reads the price from the page title ("ab € 14,99"). If Geizhals changes that format, `price_from`
returns `None` and the run prints "no price on the page"; the self-test shows which format it expects.
Keep the schedule polite: a few requests a day.

## License

MIT
