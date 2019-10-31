

# All the zml files
XML_FILES = profile/*/*.xml
# Source files put in the default profile zip.
ZIP_FILES = profile/version.txt profile/nls/*.txt ${XML_FILES}

all: ${ZIP_FILE}
profile: ${ZIP_FILE}

clean:
	rm -f ${ZIP_FILE}
#
# Run xmlint on all xml files
#
# sudo apt-get install libxml2-utils libxml2-dev
check:
	xmllint --noout ${XML_FILES}
