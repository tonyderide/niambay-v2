import os, time, logging

os.environ['SAMBANOVA_API_KEY'] = '4fad50d2-e867-47d1-be65-e4b03571128e'
os.environ['MISTRAL_API_KEY'] = 'uTu0O4NS4FsYeNLqgnq1CVOOhDZTUMY6'
os.environ['NIAMBAY_EMAIL_PWD'] = 'tonytony!01'

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s',
    handlers=[logging.FileHandler('selfcoder.log'), logging.StreamHandler()])
log = logging.getLogger('selfcoder')

from daemon.selfcoder.runner import SelfCoder

sc = SelfCoder()
log.info("Self-coder started in '%s' mode", sc.config.mode)

while True:
    try:
        result = sc.run_cycle()
        log.info("Cycle: %s", result.get('status', 'unknown'))
    except Exception as e:
        log.error("Error: %s", e)
    
    # 10 min cooldown (avoid rate limits)
    log.info("Sleeping 10 minutes...")
    time.sleep(600)
