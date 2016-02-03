#!/bin/bash
#
# Example of the use of gcamProtectLand.py to protect forest and pasture land
# in various regions at low, medium, and high levels, based on my subjective
# assessment without looking at any actual data on land protection...
#

# Protection levels. Assume the same levels for forest and pasture.
HIGH=0.9
MEDIUM=0.5
LOW=0.25

CLASSES=UnmanagedForest,UnmanagedPasture

REGS_HIGH='Australia_NZ,Canada,EU-12,EU-15,Japan,Middle East,Taiwan,USA'
REGS_MED='Argentina,Brazil,Europe_Eastern,Europe_Non_EU,European Free Trade Association,South Korea'
REGS_LOW='Africa_Eastern,Africa_Northern,Africa_Southern,Africa_Western,Central America and Caribbean,Central Asia,China,Colombia,India,Indonesia,Mexico,Pakistan,Russia,South Africa,South America_Northern,South America_Southern,South Asia,Southeast Asia'

INFILES='-i land_input_2.xml -i land_input_3.xml'
PROT_INFILES='-i prot_land_input_2.xml -i prot_land_input_3.xml'

OUTDIR="$HOME/tmp/xml"

# The first call copies the reference files, and modifies the copies, renaming them with "prot_" prefix.
gcamProtectLand.py -f "$HIGH" "$INFILES" -l "$CLASSES" -r "$REGS_HIGH" -o "$OUTDIR" -t 'prot_{filename}'

# Subsequent calls reference the copies and maintain the existing filename

# NEED TO ADD AN "inplace" flag, e.g., --inPlace, which creates a backup with a ~ at the end...

gcamProtectLand.py -f "$MEDIUM" "$PROT_INFILES" -l "$CLASSES" -r "$REGS_MED" -o "$OUTDIR" -t '{filename}'

gcamProtectLand.py -f "$LOW" "$PROT_INFILES" -l "$CLASSES" -r "$REGS_MED" -o "$OUTDIR" -t '{filename}'
