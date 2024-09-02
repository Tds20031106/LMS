from flask import current_app as app, jsonify, render_template, request, send_file
from flask_security import auth_required, roles_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Book,Section,Role  
from datastorefile import datastore
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os
from datetime import datetime,timedelta
#from forms import *
from flask_login import LoginManager,login_required,current_user,UserMixin,login_user, logout_user, login_required
from celery.result import AsyncResult
from cache import cache
from tasks import create_resource_csv



@app.get('/')
def home():
    return render_template('index.html')


@app.post('/librarian_login')
def librarian_login():
    input_data=request.get_json()
    input_email = input_data.get('email')
    input_password = input_data.get('password')

    if not input_email or not input_password:
        return jsonify({'message': 'Email and Password are required.'}), 400
    
    if input_email != 'librarian@email.com':
        return jsonify({'message': 'Invalid Email ID'}), 400

    user = datastore.find_user(email=input_email)

    if not user:
        return jsonify({'message': 'User not found'}), 404

    if not user.check_password(input_password):
        return jsonify({'message': 'Incorrect Password'}), 400

    user.last_activity = datetime.utcnow()
    db.session.commit()
    books=Book.query.all()
    sections=Section.query.all()
    rating_graph(books)
    section_book_count_graph(sections)
    return jsonify({'auth_token': user.get_auth_token(), 'role': [role.name for role in user.roles]}), 200




@app.route('/get_sections')
@auth_required('token')
@roles_required('librarian')
def get_sections():
    try:
        sections = Section.query.all()
        sections_data = [{'id': section.id, 'section_name': section.section_name} for section in sections]
        return jsonify(sections_data), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

@app.get('/app_data')
@auth_required('token')
@roles_required('librarian')
@cache.cached(timeout=50) 
def app_data():

    role=Role.query.all()
    users = User.query.all()
    all_users = [{'id': user.id, 'email': user.email, 'username': user.username, 'active': user.active,'roles': [role.name for role in user.roles],'book_count': user.book_counts} for user in users]
    books=Book.query.all()
    all_books=[{'id':book.id,'book_name':book.book_name,'author':book.author,'description':book.description,'content':book.content,'section_id':book.section_id,'section_name':Section.query.get(book.section_id).section_name if Section.query.get(book.section_id) else None,'likes':book.likes,'dislikes':book.dislikes,'date_created':book.date_created,'user_id':book.user_id,'username':User.query.get(book.user_id).username if User.query.get(book.user_id) else None,'is_approved':book.is_approved,'is_requested':book.is_requested} for book in books]
    sections=Section.query.all()
    all_sections=[{'id':section.id,'section_name':section.section_name,'date_created':section.date_created,'description':section.description,'books':[book.book_name for book in section.books]} for section in sections]


    return jsonify({'users': all_users, 'books': all_books, 'sections': all_sections}), 200



@app.post('/delete_section/<int:section_id>')
@auth_required('token')
@roles_required('librarian')
def delete_section(section_id):
    section=Section.query.get(section_id)
    if not section:
        return jsonify({'message':'Section not found'}),404
    
    for book in section.books:
        # Check if the book is associated with a user
        if book.user_id is not None:
            user = User.query.get(book.user_id)
            if user:
                user.book_counts -= 1
    db.session.delete(section)
    db.session.commit()
    return jsonify({'message':'Section deleted successfully'})


@app.put('/update_section/<int:section_id>')
@auth_required('token')
@roles_required('librarian')
def update_section(section_id):
    section = Section.query.get(section_id)
    if not section:
        return jsonify({'message': 'Section not found'}), 404

    # Get the data from the request
    data = request.get_json()

    # Extract section name and description from the data
    new_name = data.get('section_name')
    new_description = data.get('description')

    # Update the section with the new data
    section.section_name = new_name
    section.description = new_description

    db.session.commit()

    return jsonify({'message': 'Section updated successfully'}), 200


@app.post('/add_section')
@auth_required('token')
@roles_required('librarian')
def add_section():
    # Get the data from the request
    data = request.get_json()

    # Extract section name and description from the data
    section_name = data.get('section_name')
    description = data.get('description')

    # Validate the data (you can add custom validation logic here if needed)
    if not section_name or not description:
        return jsonify({'message': 'Missing required data'}), 400

    # Create a new Section object
    new_section = Section(section_name=section_name, description=description)

    # Add the new section to the database session
    db.session.add(new_section)
    db.session.commit()

    return jsonify({'message': 'Section created successfully'}), 201


def rating_graph(books):
    ratings = [book.rating for book in books]
    book_names = [book.book_name for book in books]
    
    plt.figure(figsize=(8, 6))  # Adjust figure size as needed
    plt.barh(book_names, ratings, color='blue')
    plt.xlabel('Rating (%)', fontweight='bold')
    plt.ylabel('Book Names', fontweight='bold')
    plt.title('Rating of Books', fontweight='bold')
    plt.tight_layout()
    # Save the graph as an image file in the static folder
    plt.savefig('static/images/rating_graph.png')



def section_book_count_graph(sections):
    section_names = [section.section_name for section in sections]
    book_counts = [len(section.books) for section in sections]
    
    plt.figure(figsize=(10, 6))  # Adjust figure size as needed
    plt.bar(section_names, book_counts, color='orange')
    plt.xlabel('Sections', fontweight='bold')
    plt.ylabel('Number of Books', fontweight='bold')
    plt.title('Number of Books in Each Section', fontweight='bold')
    plt.xticks(rotation=45, ha='right')  # Rotate x-axis labels for better readability
    plt.tight_layout()
    # Save the graph as an image file in the static folder
    plt.savefig('static/images/section_book_count_graph.png')



@app.post('/user_register')
def user_register():
    input_data= request.get_json()
    input_email= input_data.get('email')
    input_username= input_data.get('username')
    input_password= input_data.get('password')

    if not input_email or not input_username or not input_password:
        return jsonify({'message': 'Email, Username and Password are required.'}), 400
    
    if not datastore.find_user(email=input_email):
        datastore.create_user(email=input_email, username= input_username, password= generate_password_hash(input_password), roles=['user'])
        db.session.commit()
        return jsonify({'message': 'User registered successfully. You can login now.'}), 200
    else:
        return jsonify({'message': 'Email already registered.'}), 409


@app.post('/user_login')
def user_login():
    input_data = request.get_json()
    input_email = input_data.get('email')
    input_password = input_data.get('password')

    if not input_email or not input_password:
        return jsonify({'message': 'Email and Password are required.'}), 400
    
    if input_email == 'librarian@email.com':
        return jsonify({'message': 'Invalid Email ID'}), 400
    
    user = datastore.find_user(email=input_email)

    if not user:
        return jsonify({'message': 'User not found. Register first.'}), 404
    if not user.check_password(input_password):
        return jsonify({'message': 'Incorrect Password'}), 401
    login_user(user)
    user.last_activity = datetime.utcnow()
    db.session.commit()
    return jsonify({'auth_token': user.get_auth_token(), 'role': [role.name for role in user.roles]}), 200

@app.post('/check_overdue_books')
@auth_required('token')
@roles_required('librarian')
def check_overdue_books():
    overdue_books = Book.query.filter_by(is_approved=True).filter(Book.due_date < datetime.now()).all()

    for book in overdue_books:
        # Revoke access to the book
        user = User.query.get(book.user_id)
        if user:
            user.book_counts -= 1

        book.user_id = None
        book.is_approved = False
        book.due_date = None
        book.is_requested = False

    db.session.commit()
    response = {'message': 'Overdue books checked and access revoked successfully!'}
    return jsonify(response)


@app.get('/get_all_books')
@auth_required('token')
@roles_required('user')
def get_all_books():
    books=Book.query.all()
    all_books=[{'id':book.id,'book_name':book.book_name,'author':book.author,'description':book.description,'content':book.content,'section_id':book.section_id,'likes':book.likes,'dislikes':book.dislikes,'due_date':book.due_date,'date_created':book.date_created,'user_id':book.user_id,'is_approved':book.is_approved,'is_requested':book.is_requested} for book in books]
    return jsonify({'books':all_books}),200

@app.post('/like_book/<int:book_id>')
@auth_required('token')
@roles_required('user')
def like(book_id):
    book=Book.query.get(book_id)
    if not book:
        return jsonify({'message':'Book not found.'}),404
    book.likes+=1
    db.session.commit()
    return jsonify({'message':'Book liked successfully'}),200


@app.post('/dislike_book/<int:book_id>')
@auth_required('token')
@roles_required('user')
def dislikes(book_id):
    book=Book.query.get(book_id)
    if not book:
        return jsonify({'message':'Book not found'}),404
    book.dislikes+=1
    db.session.commit()
    return jsonify({'message':'Book disliked successfully'}),200


@app.post('/delete_book/<int:book_id>')
@auth_required('token')
@roles_required('librarian')
def delete_book(book_id):
    book = Book.query.get(book_id)
    if not book:
        return jsonify({'message': 'Book not found'}), 404

    if book.user_id:
       
        user = User.query.get(book.user_id)
        user.book_counts -= 1
        db.session.commit()  

    db.session.delete(book)
    db.session.commit()
    return jsonify({'message': 'Book deleted successfully'}),200

@app.get('/user_name')
@login_required
@auth_required('token')
@roles_required('user')
def get_user_name():
    return jsonify({'username': current_user.username})



@app.post('/add_book')
@auth_required('token')
@roles_required('librarian')
def add_book():
    input_data = request.get_json()

    name = input_data.get('book_name')
    content = input_data.get('content')
    author = input_data.get('author')
    section_id = input_data.get('section_id')
    description=input_data.get('description')

    if not all([name, content, author, section_id,description]):
        return jsonify({'message': 'All fields (name, content, author, section_id) are required'}), 400

    # Find the section
    section = Section.query.get(section_id)
    if not section:
        return jsonify({'message': 'Section not found'}), 404

    # Create a new Book instance
    new_book = Book(book_name=name, description=description,content=content, author=author, section_id=section_id)

    # Add the new book to the database session
    db.session.add(new_book)

    # Commit the changes to the database
    db.session.commit()

    # Return success response
    return jsonify({'message': 'Book created successfully', 'book_id': new_book.id}), 201


@app.put('/update_book/<int:book_id>')
@auth_required('token')
@roles_required('librarian')
def update_book(book_id):
    book = Book.query.get(book_id)
    if not book:
        return jsonify({'message': 'Book not found'}), 404

    input_data = request.get_json()

    new_name = input_data.get('name')
    new_description = input_data.get('description')
    new_author = input_data.get('author')

    if not all([new_name, new_description, new_author]):
        return jsonify({'message': 'All fields (name, description, author) are required'}), 400

    book.book_name = new_name
    book.description = new_description
    book.author = new_author

    db.session.commit()

    return jsonify({'message': 'Book updated successfully'}), 200


@app.route('/user_books')
@login_required
@auth_required('token')
@roles_required('user')
def user_books():
    # Get all requested and approved books for the current user
    requested_and_approved_books = Book.query.filter_by(
        is_requested=True,
        is_approved=True,
        user_id=current_user.id
    ).all()
    
    # Iterate over the original list to disassociate books with passed due dates from the user
    for book in requested_and_approved_books:
        if book.due_date and book.due_date < datetime.now():
            # Disassociate book from user and reset attributes
            current_user.book_counts -= 1
            book.user_id = None
            book.is_requested = False
            book.is_approved = False
            book.due_date = None
    
    db.session.commit()

    # Filter out books with due dates that have not passed
    requested_and_approved_books = Book.query.filter_by(
        is_requested=True,
        is_approved=True,
        user_id=current_user.id
    ).all()

    # Construct JSON response with book details
    books_data = []
    for book in requested_and_approved_books:
        book_data = {
            'id': book.id,
            'author': book.author,
            'description': book.description,
            'section_id': book.section_id if book.section_id else None,
            'content': book.content,
            'book_name': book.book_name,
        }
        books_data.append(book_data)

    return jsonify({'books': books_data})


@app.post('/revoke_access/<int:book_id>')
@auth_required('token')
@roles_required('librarian')
def revoke_access(book_id):
    book = Book.query.get(book_id)
    if book:
        user = User.query.get(book.user_id)
        if user:
            book.user_id = None
            book.is_requested = False
            book.is_approved = False
            book.due_date = None
            user.book_counts -= 1
            db.session.commit()
            return jsonify({'message': 'Access revoked successfully'}), 200
        else:
            return jsonify({'message': 'Unable to revoke access. User not found'}), 404
    else:
        return jsonify({'message': 'Unable to revoke access. Book not found'}), 404



@app.post('/approve_book/<int:book_id>')
@auth_required('token')
@roles_required('librarian')
def approve_book(book_id):
    book = Book.query.get(book_id)

    if book and book.is_requested and not book.is_approved:
        # Approve the book
        book.is_approved = True 

        # Set the due date to be 3 days from the current date
        book.due_date = datetime.utcnow() + timedelta(days=3)

        db.session.commit()
        return jsonify({'message': 'Book approved successfully!'}), 200
    else:
        return jsonify({'message': 'Unable to approve the book.'}), 400



@app.get('/issued_books')
@auth_required('token')
@roles_required('librarian')
def issued_books():
    # Query the database for issued books
    issued_books = Book.query.filter_by(is_approved=True).all()

    # Extract user_id, username, book_name, author, and description from issued_books
    issued_books_info = [
        {
            'user_id': book.user_id,
            'username': book.user.username,
            'book_name': book.book_name,
            'author': book.author,
            'description': book.description
        }
        for book in issued_books
    ]

    # Return a JSON response containing the list of issued books information
    return jsonify({'issued_books_info': issued_books_info}), 200



@app.get('/available_books')
@auth_required('token')
@roles_required('user')
def available_books():
    # Query for all available books (not requested, not approved, and not assigned to any user)
    books = Book.query.filter_by(is_requested=False, is_approved=False, user_id=None).all()

    # Extract relevant book information
    available_books_info = [
        {
            'book_id': book.id,
            'book_name': book.book_name,
            'author': book.author,
            'description': book.description
        }
        for book in books
    ]

    # Return a JSON response containing the list of available books information
    return jsonify({'available_books_info': available_books_info}), 200

@app.post('/return_book/<int:book_id>')
@auth_required('token')
@roles_required('user')
def return_book(book_id):
    book = Book.query.get(book_id)
    if not book:
        return jsonify({'error': 'Book not found'}), 404
    
    user = User.query.get(book.user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    user.book_counts -= 1
    book.user_id = None
    book.is_requested = False
    book.is_approved = False
    book.due_date = None
    db.session.commit()
    
    return jsonify({'message': 'Book returned successfully'}), 200


@app.post('/request_book/<int:book_id>')
@login_required
@auth_required('token')
@roles_required('user')
def request_book(book_id):
    #if not current_user.is_authenticated:
     #   return jsonify({'error': 'User not authenticated.'}), 400

    book = Book.query.get(book_id)
    if not book:
        return jsonify({'error': 'Book not found.'}), 404

    if current_user.book_counts >= 5:
        return jsonify({'error': 'You have reached the maximum limit of books.'}), 400

    if book.user_id:
        return jsonify({'error': 'This book is already requested by another user.'}), 400

    # If all conditions pass, proceed to request the book
    book.is_requested = True
    book.user_id = current_user.id
    current_user.book_counts += 1
    db.session.commit()

    return jsonify({'message': 'Book requested successfully!'}), 200




@app.get('/book_content/<int:book_id>')
@auth_required('token')
@roles_required('user')
def book_content(book_id):
    book = Book.query.get(book_id)

    if not book:
        return jsonify({'error': 'Book not found.'}), 404

    if not book.is_approved or book.user_id != current_user.id:
        return jsonify({'error': 'Forbidden access'}), 403

    return jsonify({
        'book': {
            'book_id': book.id,
            'book_name': book.book_name,
            'author': book.author,
            'description': book.description,
            'rating':book.rating,
            'content': book.content,  # Assuming this is the content attribute of the book
            # Add more book information as needed
        }
    }), 200




@app.get('/download')
def downloadcsv():
    task=create_resource_csv.delay()
    return jsonify({'taskid':task.id})


@app.get('/getcsv/<task_id>')
def getcsv(task_id):
    res=AsyncResult(task_id)
    if res.ready():
        filename=res.result
        return send_file(filename,as_attachment=True)
    else:
        return jsonify({'message':'Task Pending'}),404

