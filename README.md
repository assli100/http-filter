1. Install:
	- python3 -m venv env
	- source ~/env/bin/activate
	- pip install -r requirements.txt
	- gunicorn -w 1 -b 0.0.0.0:5000 app:app --log-level DEBUG --reload


2. Test:
	- from another shell:
		- curl -X POST http://www.google.co.il/bad --proxy http://127.0.0.1:5000
		- curl http://www.ynet.co.il --proxy http://127.0.0.1:5000
		- curl http://www.malicious.com/malicious --proxy http://127.0.0.1:5000
		- curl http://www.yahoo.com/ --proxy http://127.0.0.1:5000