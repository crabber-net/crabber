from PIL import Image, ExifTags

MAX_RES = 2048
ALPHA_BACKGROUND_COLOR = (255, 255, 255)


def size_to_quality(size):
    if size <= 64:
        return 98
    elif size <= 256:
        return 95
    elif size <= 512:
        return 90
    elif size <= 1024:
        return 75
    else:
        return 50


def exif_rotate(image):
    try:
        for orientation in ExifTags.TAGS.keys():
            if ExifTags.TAGS[orientation] == "Orientation":
                break

        exif = dict(image._getexif().items())

        if exif[orientation] == 3:
            image = image.rotate(180, expand=True)
        elif exif[orientation] == 6:
            image = image.rotate(270, expand=True)
        elif exif[orientation] == 8:
            image = image.rotate(90, expand=True)

        return image
    except (AttributeError, KeyError, IndexError):
        return image


def prep_and_save(img_bytes, filename):
    img: Image = Image.open(img_bytes)
    # Apply rotation/crop specified by EXIF data
    img = exif_rotate(img)

    # Resize image
    if max(img.size) > MAX_RES:
        img.thumbnail((MAX_RES, MAX_RES))

    # Flatten alpha to black if necessary
    if img.mode == "RGBA":
        flat_img = Image.new("RGB", img.size, ALPHA_BACKGROUND_COLOR)
        flat_img.paste(img, mask=img.split()[3])  # 3 is the alpha channel
    else:
        flat_img = img

    # Optimize and save image at 50% jpeg quality
    quality = max([size_to_quality(size) for size in flat_img.size])
    flat_img.convert("RGB").save(filename, optimize=True, quality=quality)
