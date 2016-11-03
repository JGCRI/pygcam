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

upload: pypi-upload

pypi-upload:
	python setup.py sdist upload -r pypi

clean-html:
	make -C docs clean

html:
	make -C docs html

pdf:
	make -C docs latexpdf

clean-setup:
	python setup.py clean

sdist:
	python setup.py sdist

wheel: 
	python setup.py bdist_wheel

clean: clean-html clean-setup

dev:
	pip install -e 
