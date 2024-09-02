from celery import shared_task
from models import *
import flask_excel as excel


from smtplib import SMTP
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Template
from datetime import datetime,timedelta

SMTP_HOST='localhost'
SMTP_PORT=1025
SENDER_EMAIL='librarian@email.com'
SENDER_PASSWORD=''

@shared_task(ignore_result=False)
def create_resource_csv():
    # Query the Book model to get author and book_name
    book_data = Book.query.with_entities(Book.author, Book.book_name).all()

    # Create a CSV output from the query sets
    csv_output = excel.make_response_from_query_sets(book_data, ['author', 'book_name'], 'csv')

    # Define the filename for the CSV
    filename = 'Books.csv'

    # Write the CSV output to a file
    with open(filename, 'wb') as f:
        f.write(csv_output.data)

    # Return the filename of the created CSV file
    return filename


@shared_task(ignore_result=True)
def monthly_reminder():
    # Query all users
    users = User.query.join(user_roles).join(Role).filter(Role.name == 'user').all()

    # Read the HTML template
    with open('report.html', 'r') as f:
        template = Template(f.read())

    for user in users:
        # Fetch books currently issued to the user
        currently_issued_books = Book.query.filter_by(
            is_requested = True,
            is_approved = True,
            user_id = user.id
        ).all()

        # Fetch all books in the system
        all_books = Book.query.all()

        # Render the email content
        email_content = template.render(
            email=user.email,
            username=user.username,
            currently_issued_books=currently_issued_books,
            all_books=all_books
        )

        # Send the email
        try:
            send_email(user.email, 'Monthly Report', email_content)
        except Exception as e:
            # Log the error
            print(f"Failed to send email to {user.email}: {e}")

    return "Monthly Report Sent"

def send_email(to,subject,content_body):
    msg=MIMEMultipart()
    msg['To']=to
    msg['Subject']=subject
    msg['From']=SENDER_EMAIL
    msg.attach(MIMEText(content_body,'html'))

    client=SMTP(host=SMTP_HOST,port=SMTP_PORT)
    client.send_message(msg=msg)
    client.quit()


from json import dumps
from httplib2 import Http

@shared_task(ignore_result=False)
def daily_remainder():
    timestamp=datetime.utcnow()-timedelta(hours=24)
    #not_visited_users=User.query.filter(User.last_activity<timestamp).all()
    
    # FOR Testing
    not_visited_users = User.query.filter(User.last_activity < datetime.utcnow()).all()
    if not not_visited_users:
        return "no inactive users today"
    

    for user in not_visited_users:
        username=user.username
        if username!='librarian':
            send_notification(username)

    return 'Notification sent to google chat space'

def send_notification(username):
    url='https://chat.googleapis.com/v1/spaces/AAAAyW26Wpw/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=x5J4Ve8asV41ZpAqwD75Nq9CT3qA4pvI9SET2UvyUWU'
    app_message={'text':f'Hello {username}! You have not visited the library app today.Please visit the app and enjoy reading book to expand your knowledge.'} 
    message_headers={"content-type":"application/json;charset=UTF-8"}
    http_obj=Http()
    response=http_obj.request(
        uri=url,
        method="POST",
        headers=message_headers,
        body=dumps(app_message)
    )
    