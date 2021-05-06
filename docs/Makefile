# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = source
BUILDDIR      = build

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	rm -Rf build
	cd source
	find ./ -name '*.rst' -not -name 'index.rst' -delete
	cd ../
	sphinx-apidoc -f -o source ../crons --separate
	sphinx-apidoc -f -o source ../nodes --separate
	sphinx-apidoc -f -o source ../records --separate
	sphinx-apidoc -f -o source ../shared --separate
	sphinx-apidoc -f -o source ../services --separate
	sphinx-apidoc -f -o source ../tools --separate
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
