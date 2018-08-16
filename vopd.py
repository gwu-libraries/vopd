import argparse
from pdfminer.high_level import extract_text_to_fp
import io
import os
import sys
import csv
import re
from nltk.tokenize import word_tokenize
import nltk
from normalize_terms import normalize_terms
from subjects import subject_map
from keywords import keyword_map

nltk.download('punkt')

subjects = list(subject_map.keys())
keywords = list(keyword_map.keys())


def extract_text(pdf_filepath):
    with open(pdf_filepath, "rb") as fp:
        text_fp = io.StringIO()
        extract_text_to_fp(fp, text_fp)
        return text_fp.getvalue()


def tokenize(transcript_text):
    # Convert to lower case
    clean_transcript_text = transcript_text.lower()
    # Split words by periods
    clean_transcript_text = re.sub(r'([a-z])\.([a-z])', r'\1. \2', clean_transcript_text)

    for term, normalized_term in normalize_terms.items():
        clean_transcript_text = clean_transcript_text.replace(term, normalized_term)
    return word_tokenize(clean_transcript_text)


def window_iter(transcript_words, window_size):
    pos = 0
    while pos + window_size <= len(transcript_words):
        yield pos, pos + window_size, transcript_words[pos:pos + window_size]
        pos += 1


def back_window_iter(transcript_words, window_size):
    pos = len(transcript_words)
    while pos - window_size >= 0:
        yield pos - window_size, pos, transcript_words[pos - window_size:pos]
        pos -= 1


def matching_word_list(words, word_list):
    for pos, word in enumerate(words):
        if word in word_list:
            return pos, word
    return None, None


def context(transcript_words, word_pos1, word_pos2, context_size=10):
    context_start = max(word_pos1 - context_size, 0)
    context_end = min(word_pos2 + context_size, len(transcript_words))
    return transcript_words[context_start:context_end]


def process_transcript_iter(transcript_words, window_size=10):
    # Look forwards
    for start, end, window_words in window_iter(transcript_words, window_size):
        subject_pos, subject = matching_word_list(window_words[0:1], subjects)
        if subject_pos is not None:
            keyword_pos, keyword = matching_word_list(window_words, keywords)
            if keyword_pos is not None:
                # A subject and keyword found
                yield subject, start + subject_pos, keyword, start + keyword_pos
            else:
                # Only a subject found
                yield subject, start + subject_pos, None, None
        else:
            # Look for keyword without a subject
            keyword_pos, keyword = matching_word_list(window_words[0:1], keywords)
            if keyword_pos is not None:
                subject_pos, subject = matching_word_list(window_words, subjects)
                if subject_pos is None:
                    yield None, None, keyword, start + keyword_pos

    # Look backwards
    for start, end, window_words in back_window_iter(transcript_words, window_size):
        subject_pos, subject = matching_word_list(window_words[len(window_words) - 1:], subjects)
        if subject_pos is not None:
            keyword_pos, keyword = matching_word_list(window_words, keywords)
            if keyword_pos is not None:
                # A subject and keyword found
                yield subject, start + len(window_words) - 1, keyword, start + keyword_pos


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--window', help='number of words that subject and keyword must be within (default=10)', type=int,
                        default=10)
    parser.add_argument('--context', help='number of words before and after subject and keyword to extract (default=10)', type=int,
                        default=10)
    parser.add_argument('--ask', action='store_true', help='Ask about each instance of co-location to manually code as relevant or not (default = code all as meaningful)')
    parser.add_argument('transcript', help='filepath to transcript pdf or directory')

    args = parser.parse_args()
    if not os.path.exists(args.transcript):
        print('{} does not exist'.format(args.transcript))
        sys.exit(1)
    m_transcript_filepaths = []
    if os.path.isdir(args.transcript):
        for filename in os.listdir(args.transcript):
            filepath = os.path.join(args.transcript, filename)
            if os.path.isfile(filepath) and filename.lower().endswith('.pdf'):
                m_transcript_filepaths.append(filepath)
    else:
        m_transcript_filepaths.append(args.transcript)

    headers = ['file', 'subject', 'subject_code', 'keyword', 'keyword_code', 'extract']

    with open('pos_extracts.csv', 'w') as extract_file, \
            open('neg_extracts.csv', 'w') as neg_extract_file, \
            open('keyword_extracts.csv', 'w') as keyword_extract_file, \
            open('subject_extracts.csv', 'w') as subject_extract_file:
        extract_csv = csv.writer(extract_file)
        extract_csv.writerow(headers)
        neg_extract_csv = csv.writer(neg_extract_file)
        neg_extract_csv.writerow(headers)
        keyword_extract_csv = csv.writer(keyword_extract_file)
        keyword_extract_csv.writerow(['file', 'keyword', 'keyword_code', 'extract'])
        subject_extract_csv = csv.writer(subject_extract_file)
        subject_extract_csv.writerow(['file', 'subject', 'subject_code', 'extract'])

        for m_transcript_filepath in m_transcript_filepaths:
            print('Processing {}'.format(m_transcript_filepath))
            m_transcript_text = extract_text(m_transcript_filepath)
            m_transcript_words = tokenize(m_transcript_text)
            for m_subject, m_subject_pos, m_keyword, m_keyword_pos in process_transcript_iter(m_transcript_words,
                                                                                              window_size=args.window):
                if m_keyword is None:
                    extract = ' '.join(
                        context(m_transcript_words, m_subject_pos,
                                m_subject_pos,
                                context_size=args.context))
                    subject_extract_csv.writerow([m_transcript_filepath,
                                                  m_subject,
                                                  subject_map[m_subject],
                                                  extract])
                elif m_subject is None:
                    extract = ' '.join(
                        context(m_transcript_words, m_keyword_pos,
                                m_keyword_pos,
                                context_size=args.context))
                    keyword_extract_csv.writerow([m_transcript_filepath,
                                                  m_keyword,
                                                  keyword_map[m_keyword],
                                                  extract])
                else:
                    extract = ' '.join(
                        context(m_transcript_words, min(m_subject_pos, m_keyword_pos),
                                max(m_subject_pos, m_keyword_pos),
                                context_size=args.context))
                    cur_extract_csv = extract_csv

                    if args.ask:
                        res = input('{} ({} -> {}) [Yn] '.format(extract, m_subject, m_keyword))
                        if res in ('n', 'N'):
                            cur_extract_csv = neg_extract_csv

                    cur_extract_csv.writerow([m_transcript_filepath,
                                              m_subject,
                                              subject_map[m_subject],
                                              m_keyword,
                                              keyword_map[m_keyword],
                                              extract])
