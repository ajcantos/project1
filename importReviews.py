from sqlalchemy import create_engine
from sqlalchemy.sql import text
from os import getenv

# Declare file to import
reviews_csv_file = 'reviews.csv'

def split_line(line):

    # Declare local variables
    joining = False
    values_to_join = []
    line_list = []

    # Split by commas
    comma_separated_values = line.split(',')

    # Make corrections (merge incorrectly splitted commas)
    for comma_separated_value in comma_separated_values:
        if comma_separated_value.startswith('\"'):
            joining = True
            values_to_join.append(comma_separated_value[1:])
        elif comma_separated_value.endswith('\"'):
            joining = False
            values_to_join.append(comma_separated_value[:-1])
            line_list.append(','.join(values_to_join))
        elif joining:
            values_to_join.append(comma_separated_value)
        else:
            line_list.append(comma_separated_value)

    return line_list

def main():

    # Check for environment variable
    if not getenv("DATABASE_URL"):
        raise RuntimeError("DATABASE_URL is not set")

    # Set up database
    db = create_engine(getenv("DATABASE_URL"))

    # Open file
    fcsv = open(reviews_csv_file, 'r')

    # Process information
    for line in fcsv:
        line_clean = line.strip()
        if line_clean:
            line_list = split_line(line_clean)
            if line_list[0] == 'user_id':
                print('Inserting the following reviews in the database:')
            else:
                for book_id in range(1, 5000):
                    print(book_id, ': ', line_list)
                    statement = text("""INSERT INTO reviews (book_id, user_id, rating, comment) VALUES (:book_id, :user_id, :rating, :comment)""")
                    db.execute(statement, {"book_id": str(book_id), "user_id": line_list[0], "rating": line_list[1], "comment": line_list[2]})

    # Close file
    fcsv.close()

    return

if __name__ == "__main__":
    main()