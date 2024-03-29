"""Generate optimized images to be served from Google Cloud CDN."""

from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from clients import images
from config import settings
from database.schemas import PostUpdate
from log import LOGGER

router = APIRouter(prefix="/images", tags=["images"])


@router.post(
    "/",
    summary="Optimize single post image.",
    description="Generate retina and mobile feature_image for a single post upon update.",
)
async def optimize_post_image(post_update: PostUpdate) -> JSONResponse:
    """
    Generate retina version of a post's feature image if one doesn't exist.

    :param PostUpdate post_update: Incoming payload for an updated Ghost post.

    :returns: JSONResponse
    """
    new_images = []
    post = post_update.post.current
    feature_image = post.feature_image
    title = post.title
    if feature_image:
        new_images.append(images.create_retina_image(feature_image))
        new_images.append(images.create_mobile_image(feature_image))
        new_images = [image for image in new_images if image is not None]
        if bool(new_images):
            LOGGER.info(f"Generated {len(new_images)} images for post `{title}`: {new_images}")
            return JSONResponse(new_images)
        return JSONResponse({post.title: "Retina & mobile images already exist"})
    return JSONResponse({post.title: "No images exist for optimization"})


@router.get(
    "/",
    summary="Batch optimize CDN images.",
    description="Generates retina and mobile varieties of post feature_images. \
            Defaults to images uploaded within the current month; \
            accepts a `?directory=` parameter which accepts a path to recursively optimize images on the given CDN.",
)
async def bulk_transform_images(
    directory: Optional[str] = Query(
        default=None,
        title="directory",
        description="Subdirectory of remote CDN to transverse and transform images.",
        max_length=50,
    )
) -> JSONResponse:
    """
    Apply transformations to images uploaded within the current month.
    Optionally accepts a `directory` parameter to override image directory.

    :param Optional[str] directory: Remote directory to recursively fetch images and apply transformations.

    :returns: JSONResponse
    """
    try:
        if directory is None:
            directory = settings.GCP_BUCKET_FOLDER
        transformed_images = {
            "purged": images.purge_unwanted_images(directory),
            "retina": images.retina_transformations(directory),
            "mobile": images.mobile_transformations(directory),
            # "standard": gcs.standard_transformations(directory),
        }
        response = []
        for k, v in transformed_images.items():
            if v is not None:
                response.append(f"{len(v)} {k}")
            else:
                response.append(f"0 {k}")
        LOGGER.success(f"Transformed {', '.join(response)} images")
        return JSONResponse(transformed_images)
    except Exception as e:
        LOGGER.error(f"Unexpected exception raised when transforming images: {e}")
        return JSONResponse(e, status_code=500)


@router.get("/sort/")
async def bulk_organize_images(directory: Optional[str] = None) -> JSONResponse:
    """
    Sort retina and mobile images into their appropriate directories.

    :param Optional[str] directory: Remote directory to organize images into subdirectories.

    :returns: JSONResponse
    """
    if directory is None:
        directory = settings.GCP_BUCKET_FOLDER
    retina_images = images.organize_retina_images(directory)
    LOGGER.success(f"Moved {len(retina_images)} retina images.")
    return JSONResponse(
        {"retina": retina_images},
        status_code=200,
    )
