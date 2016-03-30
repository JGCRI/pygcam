all: clean html pdf sdist wheel

html:
	make -C docs html

pdf:
	make -C docs latexpdf

sdist:
	python setup.py sdist

wheel: 
	python setup.py bdist_wheel

clean:
	python setup.py clean
	make -C docs clean

dev:
	pip install -e 
