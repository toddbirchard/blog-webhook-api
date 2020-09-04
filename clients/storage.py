"""Google Cloud Storage client and image transformer."""
from typing import List, Optional
import io
import re
from io import BytesIO
from random import randint
from google.cloud import storage
from google.cloud.storage.blob import Blob
import requests
from PIL import Image
from clients.log import LOGGER


class GCS:
    """Google Cloud Storage image CDN."""

    def __init__(
            self,
            bucket_name: str,
            bucket_url: str,
            bucket_lynx: str
    ):
        self.bucket_name = bucket_name
        self.bucket_url = bucket_url
        self.bucket_lynx = bucket_lynx

    @property
    def client(self):
        """Google Cloud Storage client."""
        return storage.Client()

    @property
    def bucket(self):
        """Google Cloud Storage bucket where memes are stored."""
        return self.client.get_bucket(self.bucket_name)

    @property
    def bucket_http_url(self) -> str:
        """Publicly accessible URL for images.."""
        return self.bucket_url

    def get(self, prefix: str) -> List[Blob]:
        """
        Retrieve all blobs in a bucket containing a prefix.
        :param prefix: Substring to match against filenames.
        :type prefix: str
        """
        return self.bucket.list_blobs(prefix=prefix)

    def fetch_blobs(self, folder: str, image_type=None) -> List[Optional[Blob]]:
        """Retrieve images from GCS bucket matching directory & filter conditions."""
        files = self.get(prefix=folder)
        if image_type == 'retina':
            return [file for file in files if '@2x.jpg' in file.name and '_mobile' not in file.name]
        return [file for file in files if '@2x' not in file.name and '_mobile' not in file.name]

    @LOGGER.catch
    def purge_unwanted_images(self, folder: str) -> List[str]:
        """Delete images which have been compressed or generated multiple times."""
        images_purged = []
        LOGGER.info('Purging unwanted images...')
        substrings = ['@2x@2x', '_o', 'psd', '?', '_mobile', '@2x-', '-1-1', '-1-2']
        blobs = self.get(folder)
        image_blobs = [blob.name for blob in blobs]
        for image_blob in image_blobs:
            if any(substr in image_blob for substr in substrings):
                self.bucket.delete_blob(image_blob)
                images_purged.append(image_blob)
                LOGGER.info(f'Deleted {image_blob}')
            r = re.compile("-[0-9]-[0-9]@2x.jpg")
            repeat_blobs = list(filter(r.match, image_blobs))
            for repeat_blob in repeat_blobs:
                self.bucket.delete_blob(repeat_blob)
                images_purged.append(repeat_blob)
                LOGGER.info(f'Deleted {repeat_blob}')
        return images_purged

    def retina_transformations(self, folder: str) -> List[Optional[str]]:
        """Find images missing a retina-quality counterpart."""
        images_transformed = []
        LOGGER.info('Generating standard images...')
        for image_blob in self.fetch_blobs(folder):
            new_image_name = image_blob.name.replace('.jpg', '@2x.jpg')
            retina_blob = self.bucket.blob(new_image_name)
            if retina_blob.exists():
                pass
            existing_image_file = self._fetch_image_via_http(retina_blob.name)
            if existing_image_file is None:
                LOGGER.info(f'Creating retina image {retina_blob.name}')
                self._create_retina_image(image_blob, retina_blob.name)
                images_transformed.append(retina_blob.name)
        return images_transformed

    def webp_transformations(self, folder: str) -> List[Optional[str]]:
        """Find images missing a webp counterpart."""
        images_transformed = []
        LOGGER.info('Generating webp images...')
        for image_blob in self.fetch_blobs(folder, image_type='retina'):
            new_image_name = image_blob.name.split('.')[0] + '.webp'
            image_file = self._fetch_image_via_http(new_image_name)
            if image_file is not None:
                LOGGER.info(f'Creating webp image {new_image_name}')
                self.bucket.copy_blob(image_blob, self.bucket, new_image_name)
                images_transformed.append(new_image_name)
        return images_transformed

    @LOGGER.catch
    def mobile_transformations(self, folder: str) -> List[Optional[str]]:
        """Generate mobile responsive images."""
        images_transformed = []
        LOGGER.info('Generating mobile images...')
        for image_blob in self.fetch_blobs(folder, image_type='retina'):
            new_image_name = image_blob.name.replace("@2x", "_mobile@2x")
            mobile_blob = self.bucket.blob(new_image_name)
            if mobile_blob.exists():
                pass
            mobile_image = self._create_mobile_image(image_blob)
            if mobile_image:
                mobile_blob.upload_from_string(mobile_image, 'image/jpeg')
                images_transformed.append(mobile_blob.name)
                LOGGER.info(f'Creating mobile image {mobile_blob.name}')
        return images_transformed

    @LOGGER.catch
    def create_single_retina_image(self, image_url: str) -> str:
        """Create retina version of single image."""
        image_path = image_url.replace(self.bucket_url, '')
        image_blob = storage.Blob(image_path, self.bucket)
        new_image_name = image_blob.name.replace('.jpg', '@2x.jpg')
        retina_blob = self.bucket.blob(new_image_name)
        if retina_blob.exists():
            return f'{retina_blob.name} already exists.'
        image_file = self._fetch_image_via_http(retina_blob.name)
        if image_file is None:
            LOGGER.info(f'Creating retina image {retina_blob.name}')
            self._create_retina_image(image_blob, retina_blob.name)
        return f'{self.bucket_http_url}{new_image_name}'

    def fetch_random_lynx_image(self) -> str:
        """Fetch random Lynx image from GCS bucket."""
        lynx_images = self.get(prefix='roundup')
        images = [f"{self.bucket_http_url}{image.name}" for image in lynx_images if '@2x.jpg' in image.name]
        rand = randint(0, len(images) - 1)
        image = images[rand]
        LOGGER.info(f'Selected random Lynx image {image}')
        return image

    def _create_mobile_image(self, image_blob: Blob):
        """Create mobile responsive version of a given image."""
        img_bytes = self._fetch_image_via_http(image_blob.name)
        stream = BytesIO(img_bytes)
        im = Image.open(stream)
        width, height = im.size
        if width > 1000:
            im_resized = im.resize((600, 346))
            new_image_bytes = io.BytesIO()
            im_resized.save(
                new_image_bytes,
                'JPEG2000',
                quality=90,
                optimize=True
            )
            return new_image_bytes.getvalue()
        return None

    @LOGGER.catch
    def _create_retina_image(self, image_blob: Blob, new_image_name: str) -> None:
        """Create retina versions of standard-res images."""
        original_image = self._fetch_image_via_http(new_image_name)
        if original_image:
            img = Image.open(BytesIO(original_image))
            img.save()
            width, height = img.size
            if width > 1000:
                self.bucket.copy_blob(image_blob, self.bucket, new_image_name)

    @LOGGER.catch
    def _fetch_image_via_http(self, image_name: str):
        """Fetch raw image data via HTTP request."""
        url = f'{self.bucket_http_url}{image_name}'
        image_request = requests.get(url)
        if image_request.headers['Content-Type'] in ('application/octet-stream', 'image/jpeg'):
            return image_request.content
        return None
