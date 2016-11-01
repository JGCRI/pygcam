#
# Build a stand-alone version of pygcam's "gt" (GCAM tool)
#

NAME = $(shell uname -s)

# Change "Darwin" to "Mac"
ifeq ($(NAME),Darwin)
  NAME=mac
else ifeq ($(NAME),Linux)
  NAME=linux		# not currently used
else
  NAME=win
endif


# NOTE: A suggested solution is to eliminate mkl:
# conda install nomkl numpy scipy scikit-learn numexpr
# conda remove mkl mkl-service

LOG_LEVEL = DEBUG
#LOG_LEVEL = INFO
VERSION   = 1.0b1
TAR_FILE  = gt-$(VERSION).tgz

PYINSTALLER = pyinstaller --clean --log-level=$(LOG_LEVEL) -y gt.spec

default: clean one_dir

all: one_dir tarball

one_dir:
	$(PYINSTALLER) --onedir --distpath=dist

zip: zips
	cd dist && gzip -r -c -9 gt-$(NAME) > ../zips/gt-$(NAME).zip

clean:
	rm -rf build one_dir one_file zips

zips:
	-mkdir zips
