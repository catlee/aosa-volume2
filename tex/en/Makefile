LATEX = pdflatex
BIBTEX = bibtex

CHAPTERS = \
  frontmatter \
	intro \
	diaspora \
	distsys \
	erlang \
	ffreleng \
	freertos \
	gdb \
	ghc \
	git \
	gpsd \
	inkscape \
	ironlang \
	itk \
	mailman \
	matplotlib \
	mediawiki \
	moodle \
	nginx \
	openmpi \
	oscar \
	osm \
	pjs \
	postgresql \
	puppet \
	pypy \
	scummvm \
	sqlalchemy \
	twisted \
	yesod \
	yocto \
	zeromq \
	colophon

SRC=$(foreach name,${CHAPTERS},${name}.tex)

all : aosa2.pdf

aosa2.pdf : aosa2.tex aosa2.bib ${SRC}
	${LATEX} aosa2
	${BIBTEX} aosa2
	${LATEX} aosa2
	${LATEX} aosa2

questions:
	@(for i in *.tex; do echo `fgrep aosaquestion $$i | wc -l` $$i; done) | sort -n -r

clean:
	@rm -f aosa2.pdf *.aux *.bak *.bbl *.blg *.log *.toc *~
