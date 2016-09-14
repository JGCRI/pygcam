# From http://peterdowns.com/posts/first-time-with-pypi.html
# To register a package on PyPiTest:
# python setup.py register -r pypitest
#
# Then to upload the actual package:
# python setup.py sdist upload -r pypitest
#
# Do the same with pypi instead of pypitest to go live

all: clean html sdist wheel

pypitest-upload:
	python setup.py sdist upload -r pypitest

pypi-upload:
	python setup.py sdist upload -r pypi


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
