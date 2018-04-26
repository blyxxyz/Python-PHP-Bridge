check:
	vendor/bin/psalm
	vendor/bin/phpcs --standard=PSR2 php
	python3 -m flake8 phpbridge
	python3 -m mypy phpbridge
