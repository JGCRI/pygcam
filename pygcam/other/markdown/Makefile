# Convert markdown files to rst for use with Sphinx

RST = runProject.rst

all: $(RST)

$(RST): %.rst: %.md
	pandoc --from=markdown --to=rst --output=$@ $<
