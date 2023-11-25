import fitz  # PyMuPDF
import re
import csv
import pandas as pd
import hashlib

# Regex pattern to match year and following text
YEAR_PATTERN = r"(\b\d{4}\b.*?)(?=\b\d{4}\b|$)"
SCORE_PATTERN_SR = r"\b([A-Z]+\d+)\s+[A-Z0-9]+\^?\s+([^\n]+)\n(\d{2,3})" # for Statement of Results
SCORE_PATTERN_AT = r"\b([A-Z]{4}\d{5})\s([^\n]+)\n[\d\.]+\n(\d{2,3})" # for Academic Transcript
AT = "ACADEMIC TRANSCRIPT"
SR = "STATEMENT OF RESULTS"

def extract_subject_data(extracted_text):
    """
    Extracts subject data from the extracted text. Returns a list of tuples of the form:
    (subject_code, subject_name, grade, score, year)
    """
    if SR in extracted_text:
        SCORE_PATTERN = SCORE_PATTERN_SR
    elif AT in extracted_text:
        SCORE_PATTERN = SCORE_PATTERN_AT
    else:
        raise ValueError("Could not find Statement of Results or Academic Transcript.")

    matches = re.findall(YEAR_PATTERN, extracted_text, re.DOTALL)
    all_matches = []
    for match in matches:
        year = match[:4]
        score_pattern = re.compile(SCORE_PATTERN)
        score_matches = score_pattern.findall(match)
        score_matches = [(*match, int(year)) for match in score_matches]
        all_matches.extend(score_matches)

    # Find the student number to make sure that we dont have any duplicates
    student_number = re.findall(r"[\d]{6,7}", extracted_text)
    if student_number:
        student_number = student_number[0]
    else:
        student_number = None
    # hash the student number
    student_number = hashlib.sha256(student_number.encode()).hexdigest()
    return all_matches#, student_number


def store_subject_data(subject_data):
    """
    Appends the subject data to a CSV file.
    """
    if not subject_data:
        return False
    with open("all_scores.csv", "a", newline="") as f:
        writer = csv.writer(f)
        for data in subject_data:
            writer.writerow(data)
            # f.write(','.join([str(x) for x in data]) + '\n')
    return True


def read_subject_data(fn="all_scores.csv"):
    """
    Reads the subject data from the CSV file. Returns a dataframe.
    """
    df = pd.read_csv(
        fn, header=None, names=["subject_code", "subject_name", "score", "year"]
    )
    # cast year and score to int
    df["year"] = df["year"].astype(int)
    df["score"] = df["score"].astype(int)

    # get unique subject-year combinations
    df_duplicates = (
        df.groupby(["subject_code", "subject_name", "year"])
        .size()
        .reset_index(name="count")
    )
    # get a list of strings of the form '(year) subject_code - subject_name (count)'
    subject_year_dict = df_duplicates.apply(
        lambda row: {
            f"({row['year']}) {row['subject_code']} - {row['subject_name']} (n={row['count']})": (
                row["year"],
                row["subject_code"],
                row["subject_name"],
            )
        },
        axis=1,
    ).to_dict()
    # convert the dict from {n:{str:(year, subject_code, subject_name)}} to {str:(year, subject_code, subject_name)}
    subject_year_dict = {k: v for d in subject_year_dict.values() for k, v in d.items()}
    return df, subject_year_dict


if __name__ == "__main__":
    # Open the uploaded PDF file
    file_path = "./StatementofResults-1081696-24_Nov_2023.pdf"
    #file_path = './1642501988720.pdf'
    doc = fitz.open(file_path)
    # Extract text from each page
    extracted_text = "".join([page.get_text() for page in doc])
    # Close the document
    doc.close()
    print(extract_subject_data(extracted_text))
