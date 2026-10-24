"""One-command private demo runner. Generates a strong admin password if absent."""
from pathlib import Path
import os
import secrets

root=Path(__file__).resolve().parent
os.chdir(root)
env=root/'.env'
if not env.exists():
    pw=secrets.token_urlsafe(24)
    env.write_text('OSINTALPHA_ADMIN_PASSWORD='+pw+'\nOSINTALPHA_DB_PATH=./instance/osintalpha.db\nOSINTALPHA_SECURE_COOKIE=0\nXAI_API_KEY=\nXAI_MODEL=grok-4.7\nTFL_APP_KEY=\n')
    try: env.chmod(0o600)
    except OSError: pass
    print('\nFIRST RUN: private .env generated.\nUsername: admin\nPassword:',pw,'\nChange it before sharing this machine.\n')
from dotenv import load_dotenv
load_dotenv(env)
import uvicorn
print('Open http://127.0.0.1:8000  (private local demo)')
uvicorn.run('app.main:app',host='127.0.0.1',port=8000,reload=False,log_level='info')
