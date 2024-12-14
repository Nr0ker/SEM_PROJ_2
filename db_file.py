# def init_db():
#     conn = get_db()
#     conn.execute('''
#         CREATE TABLE IF NOT EXISTS advertisement (
#             id INTEGER PRIMARY KEY,
#             title TEXT NOT NULL,
#             text TEXT NOT NULL,
#         )
#     ''')