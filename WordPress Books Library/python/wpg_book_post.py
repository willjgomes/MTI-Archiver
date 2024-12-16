
import requests
import base64

# WordPress site details
wp_site_url = "http://mti-sandbox-1.test"
wp_username = "wgomes"  # Your WordPress username
wp_password = "84m8 RNK7 gzpH 5q9u EzOd 1eeI"  # Your WordPress application password

post_status = "publish"  # Options: 'publish', 'draft', etc.

# Combine username and password in the format "username:password"
credentials = f"{wp_username}:{wp_password}"

# Base64 encode the credentials
base64_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')

# Set the endpoint for creating a post
# api_url = f"{wp_site_url}/wp-json/wp/v2/posts"

api_url = f"{wp_site_url}/wp-json/wp/v2/books"

# Prepare the Authorization header with Base64 encoded credentials
headers = {
    "Authorization": "Basic " + base64_credentials
}

class WPGBook:
    title = ""
    description = ""
    author = ""

    def __init__(self, title, description, author):
        self.title = title
        self.description = description
        self.author = author

    def __str__(self):
        return f"Book(title={self.title}, author={self.author}, description={self.description})"
    
    
def createBook(book: WPGBook):
    # Post details
    post_status = "publish"  # Options: 'publish', 'draft', etc.

    # Prepare the post data
    post_data = {
        "title": book.title,
        "content": book.description,
        "status": post_status,
        "wbg_author": book.author,
        "wbg_status": "active",
    }

    # Send the POST request to create a new post
    response = requests.post(
        api_url,
        json=post_data,
        headers=headers  # Use the headers with the Authorization
    )

    # Check the response status
    if response.status_code == 201:
        print("Post created successfully!")
        print("Post ID:", response.json()['id'])
    else:
        print("Failed to create post.")
        print("Response:", response.text)

