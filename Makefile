MAKEFILE_DIR=$(dir $(lastword $(MAKEFILE_LIST)))

# List of images.
IMAGES=$(wildcard *.jpg) $(wildcard *.gif) $(wildcard *.png)
IMAGES_ADDRESSES=$(IMAGES:%=%.address)

# HTML output depends on article itself and addresses of uploaded
# images.
article.html: article.txt $(IMAGES_ADDRESSES) $(MAKEFILE_DIR)/habraml.py
	$(MAKEFILE_DIR)/habraml.py < article.txt > article.html

# Copy HTML to clipboard.
.PHONY: copy
copy: article.html
	xsel --input --clipboard < article.html

.PHONY: upload-images
upload-images: $(IMAGES_ADDRESSES)

%.address: %
	photo-upload --service=imageshack.us $< | grep "^http://" > $@

