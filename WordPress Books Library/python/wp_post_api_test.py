
import requests
import base64
import os

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

api_media_url = f"{wp_site_url}/wp-json/wp/v2/media"

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

def upload_image_to_post(image_path, post_id):

    # Read the image file
    with open(image_path, 'rb') as img_file:
        image_data = img_file.read()

    # Extract image filename
    image_filename = os.path.basename(image_path)
    
    # Clean up the filename for WordPress title
    clean_title = os.path.splitext(image_filename)[0]

    # Set headers for the media upload
    headers = {
        'Content-Disposition': f'attachment; filename="{image_filename}"',
        'Content-Type': 'image/jpeg',  # Adjust MIME type if not JPEG,
        "Authorization": "Basic " + base64_credentials
    }

    # Include the clean title in the metadata
    metadata = {
        'title': clean_title,
    }


    # Upload the image
    response = requests.post(
        api_media_url,
        headers=headers,
        data=image_data,
        params=metadata,  # Add metadata as query params
        #auth=HTTPBasicAuth(username, password)
    )

    if response.status_code == 201:
        media_response = response.json()
        attachment_id = media_response['id']
        print(f"Image uploaded successfully. Media ID: {attachment_id}")

        #FIXME: Attaching an image to an existing post is not working, 
        #       the books update API must not be set correctly. 
        #       Attaching an image using featrured_media attribute when creating new book seems to work fine.

        # Attach the image to the post
        post_endpoint = f"{api_books_url}/{post_id}"
        print(post_endpoint)
        post_data = {
            'featured_media': attachment_id
        }

        post_response = requests.post(
            post_endpoint,
            json=post_data,
            headers=headers
        )

        if post_response.status_code == 200:
            print("Image attached to the post successfully.")
        else:
            print(f"Failed to attach image to post: {post_response.status_code}")
    else:
        print(f"Failed to upload image: {response.status_code}")

# Main section
#make_get_books()

image_path = "C:\laragon\www\MTI-Sandbox-1\wp-content\library\Antoine_Regis\Les-Saints-Catholiques-Face-a-L'Islam_cover.jpeg"
post_id = 123  # Replace with the ID of the post you want to attach the image to
upload_image_to_post(image_path, post_id)