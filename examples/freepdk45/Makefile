OUTPUT := \
  FreePDK45_pdkmaster.py \
  FreePDK45_coriolis.py \
  portfolio.html \
  inverter.html \
#END OUTPUTS
GENERATED := \
  FreePDK45_gen.py \
#END GENERATED
CACHE := \
  __pycache__ \
#END CACHE
SOURCE := \
  FreePDK45_gen.ipynb \
  portfolio.ipynb \
  inverter.ipynb \
#END SOURCE
TARBALL = tarballs/FreePDK45_all_$(shell date +%Y%m%d).tgz

all: $(OUTPUT)

FreePDK45_pdkmaster.py FreePDK45_coriolis.py : pdkgen
.INTERMEDIATE: pdkgen
pdkgen: FreePDK45_gen.py
	@echo "Generating from new notebook"
	@python3 FreePDK45_gen.py

%.py: %.ipynb
	@echo "Generating $@"
	@jupyter nbconvert --to python $<

%.html: %.ipynb
	@echo "Generating $@"
	@jupyter nbconvert --to html --execute $<

.PHONY: pack
pack: $(TARBALL)
$(TARBALL): $(OUTPUT) $(GENERATED) $(SOURCE) | tarballs
	@echo "Packing up"
	@tar czf $@ $^

tarballs:
	@mkdir $@

.PHONY: clean
clean:
	@rm -fr $(OUTPUT) $(CACHE)
	@echo "Spick&span"
.PHONY: clean_all
clean_all: clean
	@rm -fr $(GENERATED)
