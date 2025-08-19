from dotenv import load_dotenv
from data.database import init_db

def main():
    load_dotenv()
    init_db()


if __name__ == "__main__":
    main()
