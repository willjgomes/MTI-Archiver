
import requests, base64, os, json
from rich.console import Console

class WPGBookAPIException(Exception):
   def __init__(self, message, response):
        self.message    = message
        self.response   = response
        super().__init__(self.message)

# WPGBook class to store needed attributes to create WPG Book Post
class WPGBook:

    # WPGBook Class Functions
    def __init__(self, title="", description="", author="", folder="", file="", cover_file="", base_path=""):
        self.title = title
        self.description = description
        self.author = author
        self.folder = folder
        self.file = file
        self.cover_file = cover_file
        self.base_path = base_path
        self.book_categories = []
        self.publisher = ""
        self.published_on = ""
        self.subtitle = ""

    def __str__(self):
        return f"Book(title={self.title}, author={self.author}, description={self.description})"
    
class WPGBookPostClient:

    def __init__(self, site_url, username, password):
        # Setup WordPress URLs
        self.__init_urls(site_url)

        # Setup WordPress Authorization
        self.__init_authorization(username, password)

        # Additional Properties
        self.dflt_post_cat_id =  self.get_category_id_by_slug("book")
    
    def __init_urls(self, site_url):
        # URL for Wordpress Site
        self.wp_site_url = site_url

        # Endpoint for standard WP post
        self.wp_post_api_url = f"{self.wp_site_url}/wp-json/wp/v2/posts"

        # Endpoint for WPG Books post
        self.wp_books_post_api_url = f"{self.wp_site_url}/wp-json/wp/v2/books"

        # Endpoint for uploading media
        self.wp_media_api_url = f"{self.wp_site_url}/wp-json/wp/v2/media"        

        # Endpoint for categories
        self.wp_categories_api_url = f"{self.wp_site_url}/wp-json/wp/v2/categories"        

        # Library content download base URL
        self.download_url = f"{self.wp_site_url}/wp-content/library/"

    def __init_authorization(self, username, password):
        self.wp_username = username  # Service Account Username
        self.wp_password = password  # Service Account Password

        self.post_status = "publish"  # Options: 'publish', 'draft', etc.

        # Combine username and password in the format "username:password"
        self.credentials = f"{username}:{password}"

        # Base64 encode the credentials
        self.base64_credentials = base64.b64encode(self.credentials.encode('utf-8')).decode('utf-8')

        # Prepare the Authorization header with Base64 encoded credentials
        self.headers = {
            "Authorization": "Basic " + self.base64_credentials
        }


    # WPG Book Post Module Functions, returns post ID if successful, throws error if not  
    def createBook(self, book: WPGBook, uploadPDF):
        console = Console()
        with console.status(f"[bold green][Loading       ] {book.title}") as status:
            return self._createBook(book, uploadPDF, status)
   
    def _createBook(self, book: WPGBook, uploadPDF, status_msg):
        # Post details
        post_status = "publish"  # Options: 'publish', 'draft', etc.

        # Prepare the post data
        post_data = {
            "title":                book.title,
            "content":              book.description,
            "status":               post_status,
            "categories":           self.dflt_post_cat_id,              #Array of category ids, will likely need to translate from csv file
            "wbg_author":           book.author,
            "wbg_status":           "active",
            "wbg_download_link":    f"{self.download_url}{book.folder}/{book.file}",
            "wbg_book_categories":  book.book_categories
        }

        # Add article specific fields to post data
        post_data.update({
            "wbg_publisher":        book.publisher,
            "wbg_published_on":     book.published_on,
            "wbg_subtitle":         f"{book.published_on} {book.publisher}"
        })

        # Upload book cover (if exists) and set its cover id
        if (book.cover_file):
            status_msg.update(f"[bold green][Loading Cover  ] {book.title}")
            cover_id = self.uploadBookCover(book)
            post_data["featured_media"] = cover_id

        # Upload book pdf file
        if (uploadPDF):
            status_msg.update(f"[bold green][Loading PDF    ] {book.title}")
            file_url = self.uploadBook(book)
            post_data["wbg_download_link"] = file_url

        # Send the POST request to create a new book
        status_msg.update(f"[bold green][Loading Details] {book.title}")
        response = requests.post(
            self.wp_books_post_api_url,
            json=post_data,
            headers=self.headers  # Use the headers with the Authorization
        )

        # Check the response status
        if response.status_code == 201:
            return response.json()['id']
        else:
            raise WPGBookAPIException("Failed to create book", response )

    def uploadBookCover(self, book: WPGBook):
        image_path = f"{book.base_path}\\{book.folder}\\{book.cover_file}"

        # Read the image file
        with open(image_path, 'rb') as img_file:
            image_data = img_file.read()

        # Extract image filename
        image_filename = os.path.basename(image_path)
    
        # Clean up the filename for WordPress title
        image_title = os.path.splitext(image_filename)[0]

        # Set headers for the media upload
        headers = {
            'Content-Disposition': f'attachment; filename="{image_filename}"',
            'Content-Type': 'image/jpeg', 
            "Authorization": "Basic " + self.base64_credentials
        }

        # Include the image title in the metadata
        metadata = {
            'title': image_title,
        }

        # Upload the image
        response = requests.post(
            self.wp_media_api_url,
            headers=headers,
            data=image_data,
            params=metadata,  
        )

        if response.status_code == 201:
            media_response = response.json()
            cover_id = media_response['id']
            return cover_id
        else:
            return ""

    def uploadBook(self, book: WPGBook):
        pdf_path = f"{book.base_path}\\{book.folder}\\{book.file}"

        # Read the image file
        with open(pdf_path, 'rb') as pdf_file:
            pdf_data = pdf_file.read()

        # Extract image filename
        pdf_filename = os.path.basename(pdf_path)
    
        # Clean up the filename for WordPress title
        pdf_title = os.path.splitext(pdf_filename)[0]        

        mime_type = 'application/pdf'

         # Prepare the payload for multipart form data
        files = {
            'file': (pdf_filename, pdf_data, mime_type)
        }

        # Upload the image
        response = requests.post(
            self.wp_media_api_url,
            headers=self.headers,
            files=files  
        )

        if response.status_code == 201:
            media_response = response.json()
            file_url = media_response.get('source_url')
            return file_url
        else:
            return ""

    def check_book_exists(self, title):
        params = {
            "search": title  # Search for posts with this title
        }

        response = requests.get(
            self.wp_books_post_api_url, 
            params=params, 
            headers=self.headers
        )

        if response.status_code == 200:
            posts = extract_json(response)
            if posts:
                return True, [post['id'] for post in posts]  # Return True and matching post IDs
            else:
                return False, []
        else:
            return False, []
    
    
    def get_category_id_by_slug(self, category_slug):
        resp = requests.get(f"{self.wp_categories_api_url}?slug={category_slug}")
        if resp.status_code == 200 and resp.json():
            return resp.json()[0]['id']
        else:
            raise ValueError(f"Category slug '{category_slug}' not found")

# Only use this if response.json() does not work even if API returns Content-Type: application/json
# This method attempts to extract the JSON from response when it is incorrectly including both HTML
# and JSON (like the Books POst API endpoint seems to be doing)
def extract_json(response):
    text = response.text

    start = text.index('[')
    end = text.rindex(']') + 1
    cleaned = text[start:end]

    return json.loads(cleaned)

