check:
	vendor/bin/psalm
	vendor/bin/phpcs --standard=PSR2 php
	python3 -m flake8 php-bridge.py
	python3 -m mypy php-bridge.py
