.SUFFIXES: .pic .grap .png .ps

.pic.png:
	pic2graph -transparent "#FFFFFF" -density 100 <$*.pic >$*.png
.grap.png:
	grap2graph -transparent "#FFFFFF" -density 100 <$*.grap >$*.png
# We don't use pic2graph/grap2graph below because we want ps vector graphics.
.pic.ps:
	(echo '.PS'; cat $*.pic; echo '.PE') | groff -p -T ps >$*.ps
.grap.ps:
	(echo '.G1'; cat $*.grap; echo '.G2') | groff -p -G -T ps >$*.ps

SOURCES = README Makefile gpsd.tex software-layers.pic dataflow.pic
chapter.tar.gz: $(SOURCES)
	tar -cvzf chapter.tar.gz $(SOURCES)

