
import requests
import base64

# WordPress site details
wp_site_url = "http://mti-sandbox-1.test"
wp_username = "wgomes"  # Your WordPress username
wp_password = "84m8 RNK7 gzpH 5q9u EzOd 1eeI"  # Your WordPress application password

# Post details
post_title = "My New Post"
post_content = "This is the content of my new post."
post_status = "publish"  # Options: 'publish', 'draft', etc.

# Combine username and password in the format "username:password"
credentials = f"{wp_username}:{wp_password}"

# Base64 encode the credentials
base64_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')

# Set the endpoint for creating a post
api_post_url = f"{wp_site_url}/wp-json/wp/v2/posts"

# Set the endpoint for createing a custom post type. Note for this to work
# the custom post type has to be registered.  For custom post types of third
# party plugins, must use functions.php in the active theme for the site.
api_books_url = f"{wp_site_url}/wp-json/wp/v2/books"

# Prepare the post data
post_data = {
    "title": post_title,
    "content": post_content,
    "status": post_status
}

# Prepare the Authorization header with Base64 encoded credentials
headers = {
    "Authorization": "Basic " + base64_credentials
}

def make_post_request():

    # Send the POST request to create a new post
    response = requests.post(
        api_post_url,
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

def make_get_request():
    response = requests.get(api_post_url);
    response_json = response.json();
    print(response_json);

def make_get_books():
    response = requests.get(api_books_url);
    response_json = response.json();
    print(response_json);

make_get_books()