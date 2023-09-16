import mysql.connector

mydb = mysql.connector.connect(
    host="localhost",
    user="ljc",
    password="8218haotd",
    database="thesis"
)


def add_code_pattern(code, occurrence):
    my_cursor = mydb.cursor()

    sql = "INSERT INTO code_pattern (code, occurrence) VALUES (%s, %s)"
    val = ("John", "Highway 21")
    my_cursor.execute(sql, val)

    mydb.commit()


def find_following_by_code(code):
    my_cursor = mydb.cursor()

    my_cursor.execute("SELECT * FROM following_code where pattern_code=%s order by occurrence desc", code)

    my_result = my_cursor.fetchall()

    for x in my_result:
        print(x)
