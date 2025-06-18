import requests, base64, os, json, textwrap, html
from rich.console import Console
from mti.mti_config import mticonfig

class WPGBookAPIException(Exception):
   def __init__(self, message, response):
        self.message    = message
        self.response   = response
        super().__init__(self.message)
    
   def print_details(self):
        req_details = ""
        try:
            req_details = json.loads(self.response.request.body)
        except:
            req_details = ""                

        print(textwrap.dedent(
            f'''
            ============================================================================
            Wordpress API Call Error Details: 
            ============================================================================
            Reason         : {self.message}
            Request URL    : {self.response.request.url}
            Request Headers: {self.response.request.headers}
            Request Details: {req_details}
            Response Status: {self.response.status_code}
            Response Content: {self.response.content}
            ''')
        )

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
    
    @staticmethod
    def get_author(first_name, middle_name, last_name):
        if (len(middle_name) > 0):
            author = first_name + " " + middle_name + " " + last_name
        else:
            author = first_name + " " + last_name

        return author
    
class WPGBookPostClient:

    def __init__(self, site_url, username, password):
        # Setup WordPress URLs
        self.__init_urls__(site_url)

        # Setup WordPress Authorization
        self.__init_authorization__(username, password)

        # Additional Properties
        self.dflt_post_cat_id =  self.get_category_id_by_slug("book")
    
    def __init_urls__(self, site_url):
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

    def __init_authorization__(self, username, password):
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

    def get_book(self, post_id):
        """
        Fetches a book post by its ID.
        Returns the book data as a dictionary if successful, raises an exception if not.
        """
        response = requests.get(
            f"{self.wp_books_post_api_url}/{post_id}",
            headers=self.headers
        )


        if response.status_code == 200:
            book_json = response.json()

            #print(book_json)
            book = WPGBook()

            # The title is html encoded, so we need unescape it
            book.post_id = post_id
            book.title = html.unescape(book_json["title"]["rendered"])
            book.description = html.unescape(book_json["content"]["rendered"])
            book.author = book_json.get("author")
            book.publisher = book_json.get("wbg_publisher")
            book.published_on = book_json.get("wbg_published_on")
            book.book_categories = book_json.get("wbg_book_categories", [])
            
            book.cover_file_id = book_json.get("featured_media")
            book.file_id = book_json.get("download_media_id")

            return book
        else:
            raise WPGBookAPIException("Failed to fetch book", response)


    # WPG Book Post Module Functions, returns post ID if successful, throws error if not 
    # If post_id is passed in it will update existing book
    def create_book(self, book: WPGBook, uploadMedia, post_id = None):
        console = Console()
        with console.status(f"[bold green][Loading       ] {book.title}") as status:
            return self._create_book(book, uploadMedia, status, post_id)
    
    # Internal function to create the book post so it can update the console status 
    # message. This was separated in a function so the entire body didn't have to be
    # indented in the with clause above.
    def _create_book(self, book: WPGBook, uploadMedia, status_msg, post_id):
        # Post details
        post_status = "publish"  # Options: 'publish', 'draft', etc.

        # Prepare the post data
        post_data = {
            "title":                book.title,
            "content":              book.description,
            "status":               post_status,
            "categories":           self.dflt_post_cat_id,              #Array of category ids, will likely need to translate from csv file            
            "wbg_status":           "active",            
            "wbg_book_categories":  book.book_categories
        }

        # This is to get around odd cause her API get request not properly returning
        # author for update operations
        if (book.author):
            post_data["wbg_author"] = book.author

        # Add article specific fields to post data
        post_data.update({
            "wbg_publisher":        book.publisher,
            "wbg_published_on":     book.published_on,
            "wbg_subtitle":         f"{book.published_on} {book.publisher}"
        })

        # Upload book cover (if exists) and set its cover id
        if (uploadMedia and book.cover_file):
            status_msg.update(f"[bold green][Loading Cover  ] {book.title}")
            cover_id = self.upload_book_cover(book)
            post_data["featured_media"] = cover_id

        # Upload book pdf file
        if (uploadMedia and book.file):
            status_msg.update(f"[bold green][Loading PDF    ] {book.title}")
            file_url = self.upload_book_file(book)
            post_data["wbg_download_link"] = file_url

        # Send the POST request to create a new book
        status_msg.update(f"[bold green][Loading Details] {book.title}")        
        response = requests.post(
            f"{self.wp_books_post_api_url}{"/"+post_id if post_id else ''}",
            json=post_data,
            headers=self.headers  # Use the headers with the Authorization
        )

        # Check the response status
        if response.status_code == 200 or response.status_code == 201:
            return response.json()['id']
        else:
            raise WPGBookAPIException("Failed to create/update book", response )

    
    def upload_book_cover(self, book: WPGBook):
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
            raise WPGBookAPIException("Failed to upload cover", response )

    def upload_book_file(self, book: WPGBook):
        pdf_path = f"{book.base_path}\\{book.folder}\\{book.file}"

        # Read the pdf file
        with open(pdf_path, 'rb') as pdf_file:
            pdf_data = pdf_file.read()

        # Extract pdf filename
        pdf_filename = os.path.basename(pdf_path)
    
        # Clean up the filename for WordPress title
        pdf_title = os.path.splitext(pdf_filename)[0]        

        mime_type = 'application/pdf'

         # Prepare the payload for multipart form data
        files = {
            'file': (pdf_filename, pdf_data, mime_type)
        }

        # Upload the pdf file
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
            raise WPGBookAPIException("Failed to upload PDF", response )

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
    
    def delete_media(self, media_id):
        response = requests.delete(
            f"{self.wp_media_api_url}/{media_id}?force=true",
            headers=self.headers
        )

        if response.status_code == 200 or response.status_code == 204:
            return True
        elif response.status_code == 404:
            return False
        else:
            raise WPGBookAPIException("Failed to delete media", response)
        
    def get_category_id_by_slug(self, category_slug):
        resp = requests.get(f"{self.wp_categories_api_url}?slug={category_slug}")
        if resp.status_code == 200 and resp.json():
            return resp.json()[0]['id']
        else:
            #raise ValueError(f"Category slug '{category_slug}' not found\n {resp}")
            return " "

def get_wbg_client():
    # Setup Book post client 
    # (TODO: Maybe only create this once per archiver instead of for every load event)
    wp_url      = mticonfig.ini['WordPress']['SiteURL']
    wp_username = mticonfig.ini['WordPress']['Username']
    wp_password = mticonfig.ini['WordPress']['Password']
    
    return WPGBookPostClient(wp_url, wp_username, wp_password)

# Only use this if response.json() does not work even if API returns Content-Type: application/json
# This method attempts to extract the JSON from response when it is incorrectly including both HTML
# and JSON (like the Books POst API endpoint seems to be doing)
def extract_json(response):
    text = response.text

    start = text.index('[')
    end = text.rindex(']') + 1
    cleaned = text[start:end]

    return json.loads(cleaned)

