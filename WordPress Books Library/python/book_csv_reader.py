import csv

def read_csv_file(file_path):
    """
    Reads a CSV file with columns: firstname, middle name, last name, 
    book title, book file path, book cover image file path.

    Args:
        file_path (str): Path to the CSV file to be read.

    Yields:
        dict: A dictionary containing the data for a row.
    """
    try:
        with open(file_path, mode='r', encoding='utf-8') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            # Ensure the CSV has the expected columns
            
            expected_columns = ["FirstName","MiddleName","LastName","BookTitle","BookFile","BookCoverFile"]
            if csv_reader.fieldnames is None or any(col not in csv_reader.fieldnames for col in expected_columns):
                raise ValueError(f"CSV file must contain the following columns: {', '.join(expected_columns)}")

            for row in csv_reader:
                yield row
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
    except ValueError as ve:
        print(f"Error: {ve}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

