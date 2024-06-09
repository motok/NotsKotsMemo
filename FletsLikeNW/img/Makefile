all: interfaces.svg nw.svg seq.svg

clean:
	-rm -f interfaces.svg interfaces.png
	-rm -f nw.svg nw.png
	-rm -f seq.svg seq.png

interfaces.svg: interfaces.dot
	dot -T svg -o $@ $<

interfaces.png: interfaces.dot
	dot -T png -o $@ $<

nw.svg: nw.dot
	dot -T svg -o $@ $<

nw.png: nw.dot
	dot -T png -o $@ $<

seq.svg: seq.diag
	seqdiag -T svg -o $@ $<

seq.png: seq.diag
	seqdiag -T png -o $@ $<
