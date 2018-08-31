import argparse
from pdfminer.high_level import extract_text_to_fp
import datetime
import io
import os
import sys
import csv
import re
from nltk.tokenize import word_tokenize
import nltk

nltk.download('punkt')

# global variables
subject_map = {}
keyword_map = {}
subjects = []
keywords = []
normalize_terms = {}


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


def show_data(show_file_path):
    show_file_name = os.path.split(show_file_path)[1]

    show_info = {}
    month = show_file_name[0:2]
    day = show_file_name[3:5]
    year = show_file_name[6:10]

    show_info['show_date'] = month+'/'+day+'/'+year
    show_info['show_id'] = show_file_name[11:14]
    show_info['show_name'] = show_file_name[15:-4] # leave off .PDF

    return show_info

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


def context(transcript_words, word_pos1, word_pos2, context_size=20):
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
                # A subject and keyword found, where the subject is to the left of the keyword
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
        # if the right-most word in the window is a subject term
        if subject_pos is not None:
            keyword_pos, keyword = matching_word_list(window_words, keywords)
            if keyword_pos is not None:
                # A subject and keyword found
                yield subject, start + len(window_words) - 1, keyword, start + keyword_pos


# Check if the file has a newline as the last character; if not, add it
def fix_newline(f):
    f_length = f.tell()
    f.seek(f_length-1, 0)
    lastchar = f.read(1)
    if lastchar != '\n':
        f.write('\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--window', help='number of words that subject and keyword must be within (default = 10)', type=int,
                        default=10)
    parser.add_argument('--context', help='number of words before and after subject and keyword to extract (default = 20)', type=int,
                        default=20)
    parser.add_argument('--subjectfile', help='subject list file (default = subjects.csv)', type=argparse.FileType('r'),
                        default='subjects.csv')
    parser.add_argument('--keywordfile', help='keyword list file (default = keywords.csv)', type=argparse.FileType('r'),
                        default='keywords.csv')
    parser.add_argument('--normalizefile', help='normalize terms file (default = normalize_terms.csv)', type=argparse.FileType('r'),
                        default='normalize_terms.csv')
    parser.add_argument('transcript', help='filepath to transcript pdf or directory')

    args = parser.parse_args()

    # Read subjects, keywords, and normalize_terms
    with args.subjectfile as subjects_file:
        subjects_csv = csv.reader(subjects_file)
        for row in subjects_csv:
            subjects += [row[0]]
            subject_map[row[0]] = row[1]

    with args.keywordfile as keywords_file:
        keywords_csv = csv.reader(keywords_file)
        for row in keywords_csv:
            keywords += [row[0]]
            keyword_map[row[0]] = row[1]

    with args.normalizefile as normalize_terms_file:
        normalize_terms_csv = csv.reader(normalize_terms_file)
        for row in normalize_terms_csv:
            normalize_terms[row[0]] = row[1]

    # Compose m_transcript_filepaths list
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

    # Start processing
    headers = ['extract_date', 'file', 'show_date', 'show_id', 'show_name', 'subject', 'subject_code', 'keyword', 'keyword_code', 'relevant?', 'extract']

    if os.path.exists('extracts.csv'):
        append_extracts = True
        file_mode = 'a+'
    else:
        append_extracts = False
        file_mode = 'w'

    with open('extracts.csv', file_mode) as extract_file:
        # If the file was previously saved using Excel, it will be lacking a final \n character.
        # So, we need to check if it's missing; if so, add it so that appending starts on a new line.
        if append_extracts:
            fix_newline(extract_file)
        extract_csv = csv.writer(extract_file)
        if not append_extracts:
            extract_csv.writerow(headers)

        for m_transcript_filepath in m_transcript_filepaths:
            show_info = show_data(m_transcript_filepath)

            print('Processing {}'.format(m_transcript_filepath))
            m_transcript_text = extract_text(m_transcript_filepath)
            m_transcript_words = tokenize(m_transcript_text)
            for m_subject, m_subject_pos, m_keyword, m_keyword_pos in process_transcript_iter(m_transcript_words,
                                                                                              window_size=args.window):
                extract_date = datetime.datetime.now().strftime("%m/%d/%y %H:%M:%S")

                if m_keyword is None:
                    extract = ' '.join(
                        context(m_transcript_words, m_subject_pos,
                                m_subject_pos,
                                context_size=args.context))
                    extract_csv.writerow([extract_date,
                                          m_transcript_filepath,
                                          show_info['show_date'],
                                          show_info['show_id'],
                                          show_info['show_name'],
                                          m_subject,
                                          subject_map[m_subject],
                                          '',
                                          '',
                                          '',
                                          extract])
                elif m_subject is None:
                    extract = ' '.join(
                        context(m_transcript_words, m_keyword_pos,
                                m_keyword_pos,
                                context_size=args.context))

                    extract_csv.writerow([extract_date,
                                          m_transcript_filepath,
                                          show_info['show_date'],
                                          show_info['show_id'],
                                          show_info['show_name'],
                                          '',
                                          '',
                                          m_keyword,
                                          keyword_map[m_keyword],
                                          '',
                                          extract])
                else:
                    extract = ' '.join(
                        context(m_transcript_words, min(m_subject_pos, m_keyword_pos),
                                max(m_subject_pos, m_keyword_pos),
                                context_size=args.context))

                    extract_csv.writerow([extract_date,
                                          m_transcript_filepath,
                                          show_info['show_date'],
                                          show_info['show_id'],
                                          show_info['show_name'],
                                          m_subject,
                                          subject_map[m_subject],
                                          m_keyword,
                                          keyword_map[m_keyword],
                                          '',
                                          extract])