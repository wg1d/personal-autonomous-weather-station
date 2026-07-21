# ==============================================================================
# Makefile for generating SVG diagrams from LaTeX source files
# 
# Purpose:
# This Makefile automatically finds all `.tex` files in the current directory,
# compiles them into PDFs using `latexmk`, and then converts those PDFs into 
# SVG images using `pdf2svg`. The resulting SVG files are saved in the 
# `../diagrams/` directory. Temporary compilation files are cleaned up afterwards.
# 
# Dependencies:
# - latexmk
# - pdf2svg
# - texlive-science and texlive-pictures (for circuitikz/siunitx)
# ==============================================================================

OUT=../diagrams/

TEX=$(shell grep -l '\\begin{document}' *.tex)
SVG=$(patsubst %.tex,$(OUT)/%.svg,$(TEX))

all: $(SVG)

$(OUT)/%.svg: %.tex
	mkdir -p $(OUT)
	latexmk -pdf -silent $<
	pdf2svg $*.pdf $@
	latexmk -C $<

clean:
	rm -rf *.aux *.log *.fb_latexmk *.fls *.pdf

.PHONY: all clean
