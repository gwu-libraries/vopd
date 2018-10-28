import argparse
from pdfminer.high_level import extract_text_to_fp
import datetime
import io
import os
import sys
import csv
import statistics

# global variables
subject_map = {}
keyword_score = {}
keyword_id = {}
subjects = []
keywords = []


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--codingfile', help='coding/analysis file (default = coding.csv)', type=argparse.FileType('r'),
                        default='coding.csv')
    parser.add_argument('--keywordfile', help='keyword list file (default = keywords.csv)', type=argparse.FileType('r'),
                        default='keywords.csv')
    parser.add_argument('--normalizefile', help='normalize terms file (default = normalize_terms.csv)', type=argparse.FileType('r'),
                        default='normalize_terms.csv')

    args = parser.parse_args()

    # Read through existing keywords file
    with args.keywordfile as keywords_file:
        keywords_csv = csv.reader(keywords_file)
        for row in keywords_csv:
            keywords += [row[0]]
            keyword_score[row[0]] = row[1]
            keyword_id[row[0]] = row[2]

    keyword_coded = {}
    with args.codingfile as coding_file:
        coding_csv = csv.reader(coding_file)
        next(coding_csv, None)  # Skip the header row

        for row in coding_csv:
            old_keyword = row[7]  # Column H
            new_score = row[13]  # Column N
            new_keyword = row[16] # Column Q

            if not new_score.isnumeric():
                # do nothing, go to the next line
                continue


            if new_keyword.strip() is not '':
                # keep in mind that the new keyword may or may not already exist in keywords
                if new_keyword in keyword_coded:
                    # if we've already seen it in this coding file
                    print("Updating new keyword ", new_keyword)
                    keyword_coded[new_keyword] += [int(new_score)]
                else:
                    print("Adding new keyword ", new_keyword)
                    keyword_coded[new_keyword] = [int(new_score)]
            else:
                # we have seen cases where there's nothing in either H or Q; just skip this
                if old_keyword.strip() is '':
                    continue
                if old_keyword in keyword_coded:
                    # if we've already seen it in this coding file
                    print("There's no new keyword; Updating old keyword ", old_keyword)
                    keyword_coded[old_keyword] += [int(new_score)]
                else:
                    print("There's no new keyword; Adding old keyword ", old_keyword)
                    keyword_coded[old_keyword] = [int(new_score)]

    keyword_mode_scores = {}
    for k, s in keyword_coded.items():
        try:
            keyword_mode_scores[k] = statistics.mode(s)
        except statistics.StatisticsError:
            m = round(statistics.mean(s))
            print("Where keyword =", k, " and scores =", s)
            print("Made a decision to go with ", m)
            keyword_mode_scores[k] = m

    # Now merge with keywords file
    keywords_new = keywords
    keyword_score_new = keyword_score
    keyword_id_new = keyword_id

    for k, s in keyword_mode_scores.items():
        if k in keywords:
            keyword_score_new[k] = keyword_mode_scores[k]
            keyword_id_new[k] = keyword_id[k]
        else:
            keywords_new += [k]
            keyword_score_new[k] = keyword_mode_scores[k]
            keyword_id_new[k] = ''

    with open('keywords_new.csv', 'w') as new_keyword_file:
        keywords_new_csv = csv.writer(new_keyword_file)

        for k in keywords_new:
            keywords_new_csv.writerow([k, keyword_id_new[k], keyword_score_new[k]])


