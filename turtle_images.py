from PIL import Image, ExifTags


def exif_rotate(image):
    try:
        for orientation in ExifTags.TAGS.keys():
            if ExifTags.TAGS[orientation] == 'Orientation':
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

    # Flatten alpha to black if necessary
    if img.mode == "RGBA":
        flat_img = Image.new("RGB", img.size, (0, 0, 0))
        flat_img.paste(img, mask=img.split()[3])  # 3 is the alpha channel
    else:
        flat_img = img

    # Optimize and save image at 50% jpeg quality
    flat_img.convert('RGB').save(filename, optimize=True, quality=50)
