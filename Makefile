
.PHONY: test
test:
	python setup.py test


.PHONY: lint
lint:
	flake8
