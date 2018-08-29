# vopd
Code supporting the Voices of Polarization and Demoization project

## Running the program

usage: `python vopd.py [-h] [--window WINDOW] [--context CONTEXT] [--ask] transcript`

```positional arguments:
  transcript         filepath to transcript pdf or directory

optional arguments:
  -h, --help         show this help message and exit
  --window WINDOW    number of words that subject and keyword must be within (default = 10)
  --context CONTEXT  number of words before and after subject and keyword to extract (default = 20)
  --subjectfile SUBJECTFILE   subject list file (default = subjects.csv)
  --keywordfile KEYWORDFILE   keyword list file (default = keywords.csv)
  --normalizefile NORMALIZEFILE   normalize terms file (default = normalize_terms.csv)
  --ask              Ask about each instance of co-location to manually code as relevant or not (default = code all as relevant)
```

Transcript files must be named using the following pattern:

`MM_DD_YYYY_NNN_Name Of The Show.pdf`

where:
`MM_DD_YYYY` is the date of the show
`NNN` is the show code/number
(any separator character is okay - but positions of the values are important)


## Output files

**`keyword_extracts.csv`** - All found instances of keywords

**`subject_extracts.csv`** - All found instances of subjects

**`pos_extracts.csv`** - Co-located pairs of keywords and subjects coded as relevant 

**`neg_extracts.csv`** - Co-located pairs of keywords and subjects coded as *not* relevant


