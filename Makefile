all: php python

php: phpcs psalm

python: flake8 mypy

phpcs:
	vendor/bin/phpcs --standard=PSR2 php

psalm:
	vendor/bin/psalm

flake8:
	python3 -m flake8 phpbridge

mypy:
	python3 -m mypy --strict-optional phpbridge
