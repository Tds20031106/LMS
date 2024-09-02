from models import db, Book, Section, User, Role
from werkzeug.security import generate_password_hash
from datastorefile import datastore
from datetime import datetime

def initialize_sample_data():
    from main import app
    with app.app_context():
        db.create_all()
        
        datastore.find_or_create_role(name='user', description='This is the user role')
        datastore.find_or_create_role(name='librarian', description='This is the librarian role')
        db.session.commit()

        # Create librarian user if not exists
        if not datastore.find_user(email='librarian@email.com'):
            datastore.create_user(
            email='librarian@email.com',
            username='librarian',
            password=generate_password_hash('librarian'),
            roles=['librarian']
            )
        db.session.commit()


        # Sample sections
        sections = [
            Section(section_name="Fiction", description="Fictional works including novels, short stories, etc."),
            Section(section_name="Science", description="Books related to science and technology."),
            Section(section_name="History", description="Books on historical events and figures."),
            Section(section_name="Biography", description="Biographies and autobiographies of famous personalities."),
            Section(section_name="Philosophy", description="Books on philosophical thoughts and theories."),
        ]

        # Adding sections if they don't already exist
        for section in sections:
            existing_section = Section.query.filter_by(section_name=section.section_name).first()
            if not existing_section:
                db.session.add(section)

        # Sample books
        books = [
    Book(book_name="Shadows of Justice", author="Harper Lee", description="A powerful narrative on social inequality and the quest for justice.", content="This novel paints a vivid picture of a small town grappling with deep-seated racial issues. Through the eyes of a young girl, we witness her father, a lawyer, take on a case that challenges the town's moral compass. The story is a poignant reflection on courage, compassion, and the fight against prejudice.", section_id=1, likes=12, dislikes=3),
    
    Book(book_name="The Universe Unveiled", author="Stephen Hawking", description="An exploration of the universe's most intriguing mysteries.", content="In this book, Stephen Hawking delves into the wonders of the cosmos, making complex scientific theories accessible to all. He discusses the origins of the universe, black holes, and the nature of time, inviting readers to ponder the vastness of space and our place within it.", section_id=2, likes=15, dislikes=2),
    
    Book(book_name="Reflections of Hope", author="Anne Frank", description="The remarkable story of a young girl during a time of great turmoil.", content="This book offers an intimate glimpse into the life of a young girl hiding during a period of intense conflict. Her diary entries reveal her thoughts on life, love, and the human spirit, serving as a powerful reminder of the resilience and hope that can emerge even in the darkest of times.", section_id=3, likes=25, dislikes=1),
    
    Book(book_name="The Innovator's Journey", author="Walter Isaacson", description="A detailed look into the life of a groundbreaking tech visionary.", content="This biography captures the essence of a technology pioneer whose innovations have left a lasting impact on the world. The book explores the highs and lows of his career, the challenges he faced, and the drive that led him to create some of the most iconic products of our time.", section_id=4, likes=10, dislikes=0),
    
    Book(book_name="Thoughts to Live By", author="Marcus Aurelius", description="A collection of philosophical insights from an ancient ruler.", content="In this work, Marcus Aurelius shares his personal reflections on life, leadership, and the pursuit of virtue. Written as a series of meditations, these timeless thoughts offer guidance on how to navigate life's challenges with wisdom and integrity.", section_id=5, likes=20, dislikes=4)
]

        # Adding books if they don't already exist
        for book in books:
            existing_book = Book.query.filter_by(book_name=book.book_name).first()
            if not existing_book:
                db.session.add(book)

        db.session.commit()
        print("Sample data initialized successfully.")
