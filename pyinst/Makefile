#
# Build a stand-alone version of pygcam's "gt" (GCAM tool)
#

NAME := $(shell uname -s)

# Change "Darwin" to "Mac"
ifeq ($(NAME),Darwin)
  NAME=mac
else ifeq ($(NAME),Linux)
  NAME=linux		# not currently used
else
  NAME=win
endif

VERSION  := $(shell python gt.py --version 2>&1)
FULLNAME := $(VERSION)-$(NAME)

# NOTE: A suggested solution is to eliminate mkl:
# conda install nomkl numpy scipy scikit-learn numexpr
# conda remove mkl mkl-service

LOG_LEVEL = DEBUG
#LOG_LEVEL = INFO

PYINSTALLER = pyinstaller --clean --log-level=$(LOG_LEVEL) -y gt.spec

default: clean one_dir

one_dir:
	$(PYINSTALLER) --onedir --distpath=dist

zip:
	cd dist && zip -q -r $(FULLNAME).zip $(FULLNAME)

all: default zip

clean:
	rm -rf build dist one_dir one_file 
