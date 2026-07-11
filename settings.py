import configparser
import os

from utils.utils import bool_from_str

conf = configparser.ConfigParser()
conf.read("settings.ini", encoding="utf-8")

token = conf["kabusapi"]["token"]
password = conf["kabusapi"]["password"]
url = conf["kabusapi"]["url"]
product_code = conf["kabusapi"]["product_code"]

db_name = conf["db"]["name"]
db_driver = conf["db"]["driver"]

web_port = int(conf["web"]["port"])

trade_duration = conf["pytrading"]["trade_duration"].lower()
back_test = bool_from_str(conf["pytrading"]["back_test"])
use_percent = float(conf["pytrading"]["use_percent"])
past_period = int(conf["pytrading"]["past_period"])
stop_limit_percent = float(conf["pytrading"]["stop_limit_percent"])
num_ranking = int(conf["pytrading"]["num_ranking"])

results_dir = conf.get("paths", "results_dir", fallback="results")
backtest_results_file = conf.get("paths", "backtest_results_file", fallback=f"{results_dir}/backtest_results.json")
multi_stock_results_file = conf.get(
	"paths", "multi_stock_results_file", fallback=f"{results_dir}/multi_stock_backtest_results.json"
)
backtest_details_dir = conf.get("paths", "backtest_details_dir", fallback=f"{results_dir}/backtest_details")
backtest_rankings_dir = conf.get("paths", "backtest_rankings_dir", fallback=f"{results_dir}/backtest_rankings")
walkforward_dir = conf.get("paths", "walkforward_dir", fallback=f"{results_dir}/walkforward")
cache_dir = conf.get("paths", "cache_dir", fallback=f"{results_dir}/cache")

for path in [results_dir, backtest_details_dir, backtest_rankings_dir, walkforward_dir, cache_dir]:
	os.makedirs(path, exist_ok=True)
