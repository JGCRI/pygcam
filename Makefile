all: sdist wheel

sdist:
	python setup.py sdist

wheel:
	python setup.py bdist_wheel

dev:
	pip install -e .
