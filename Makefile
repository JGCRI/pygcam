# From http://peterdowns.com/posts/first-time-with-pypi.html
# To register a package on PyPiTest:
# python setup.py register -r pypitest
#
# Then to upload the actual package:
# python setup.py sdist upload -r pypitest
#
# Do the same with pypi instead of pypitest to go live

all: clean html sdist wheel

version = `./version.sh`

test-upload: # sdist
	twine upload dist/pygcam-$(version).tar.gz -r testpypi

upload: pypi-upload

pypi-upload: sdist
	twine upload dist/pygcam-$(version).tar.gz

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
	pip install -e .

remove-pygcam:
	conda env remove -n pygcam3

UNAME=$(strip $(shell uname))

ifeq ($(UNAME), Darwin)
    YML_FILE=py3_pygcam_macos.yml
else ifeq ($(UNAME), Linux)
    YML_FILE=py3_pygcam_linux.yml
else
    # of limited use since probably no "make" cmd
    YML_FILE=py3_opgee_win10.yml
endif

create-pygcam: $(YML_FILE)
	conda env create -f $(YML_FILE)

install-pygcam:
	bash -l -c 'conda activate pygcam3 && pip install -e .'

rebuild-pygcam: remove-pygcam create-pygcam install-pygcam


EMPTY :=
SPACE := $(EMPTY) $(EMPTY)
RQMTS := $(shell cat requirements.in)
MODS  := $(subst $(SPACE),|,$(RQMTS))
EXPR  := $(shell printf "^(%s)=\n" '$(MODS)')

RTD_RQMTS = rtd.requirements.txt

clean-requirements:
	rm $(RTD_RQMTS)

rtd-reqs $(RTD_RQMTS): requirements.in
	python -V|sed -e 's/Python /python==/' > $(RTD_RQMTS)
	pip freeze | egrep '$(EXPR)' >> $(RTD_RQMTS)
