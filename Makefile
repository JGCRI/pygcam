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

clean: clean-html clean-setup clean-requirements

dev:
	pip install -e

EMPTY :=
SPACE := $(EMPTY) $(EMPTY)
RQMTS := $(shell cat requirements.in)
MODS  := $(subst $(SPACE),|,$(RQMTS))
EXPR  := $(shell printf "^(%s)=\n" '$(MODS)')

RTD_RQMTS = rtd.requirements.txt

clean-requirements:
	rm $(RTD_RQMTS)

rtd-reqs $(RTD_RQMTS): requirements.in
	pip freeze | egrep '$(EXPR)' > $(RTD_RQMTS)

