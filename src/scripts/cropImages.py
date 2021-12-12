import os
import sys
from PIL import Image, ImageFilter


class Static:
    img_size = (1024, 768)
    blurr_radius = 30


def execute_image_cropping():
    prefix = "../media/"
    filedir = "images/"
    perform_checks(prefix, filedir)
    crop_existing_images(prefix, filedir)


def perform_checks(prefix, filedir):
    filenames = os.listdir(prefix + filedir)

    falseOriginalLabels = []
    multipleMatchesError = []
    for filename in filenames:
        #cut the file extension
        lastDotOccurance = filename.rfind(".")
        filenameWithoutExtension = filename[:lastDotOccurance]

        lastDotOccurance = filename.rfind(".")
        filenameWithoutExtension = filename[:lastDotOccurance]
        extension = filename[lastDotOccurance:]
        #if the last 9 characters of the string equals "_original"
        #a blurred version already exists and therefore does not have to be created
        if filenameWithoutExtension[-9:] == "_original":
            converted = list(filter(lambda listElement: listElement.startswith(filenameWithoutExtension[:-9]), filenames))
            if len(converted) < 1:
                falseOriginalLabels.append(filename)
                print("False original label (no cropped version existing) for: " + filename)
                continue
        else:
            #check if an image exists, that has the same filename, but with the "_origianal" extension
            # => if it exists, the image has already been cropped and execution can be skipped
            matching = list(filter(lambda listElement: listElement.startswith(filenameWithoutExtension+"_original"), filenames))
            if(len(matching) > 1):
                multipleMatchesError.append(filenameWithoutExtension)
                print("Multiple matches for: " + filename)
                print(matching)
                continue

    if len(multipleMatchesError) > 0 or len(falseOriginalLabels) > 0:
        print("Conflicts in existing data, cropping aborted")
        print("Files with ambiguous names: " + str(len(multipleMatchesError)))
        print(multipleMatchesError)
        print("____________________________")
        print("Files with label '_original' that do not have a cropped file: " + str(len(falseOriginalLabels)))
        print(falseOriginalLabels)
        print("Please resolve the conflicts manually before executing this script")
        sys.exit()
    #if none of the conditions was met, execute cropping
    print("Name validation passed, executing cropping")

def crop_existing_images(prefix, filedir):
    filenames = os.listdir(prefix + filedir)
    croppedImages = []
    failedCrops = []
    for filename in filenames:
        #cut the file extension
        lastDotOccurance = filename.rfind(".")
        filenameWithoutExtension = filename[:lastDotOccurance]
        #if the last 9 characters of the string equals "_original"
        #a blurred version already exists and therefore does not have to be created
        if filenameWithoutExtension[-9:] == "_original":
            converted = list(filter(lambda listElement: listElement.startswith(filenameWithoutExtension[:-9]), filenames))
            if len(converted) < 1:
                print("False original label (no cropped version existing) for: " + filename)
            continue
        else:
            #check if an image exists, that has the same filename, but with the "_origianal" extension
            # => if it exists, the image has already been cropped and execution can be skipped
            matching = list(filter(lambda listElement: listElement.startswith(filenameWithoutExtension+"_original"), filenames))
            if(len(matching) == 1):
                continue
            if(len(matching) > 1):
                print("Multiple matches for: " + filename)
                continue

        try:
            save_original_image(prefix, filedir, filename)
            crop_image(prefix, filedir, filename)
            croppedImages.append(filename)
        except:
            failedCrops.append(filename)



    print("Cropped images: "+ str(len(croppedImages)))
    print("Names of cropped images:")
    print(croppedImages)

    if len(failedCrops) > 0:
        print('\x1b[0;30;41m' + 'Failed croppings: '+ str(len(failedCrops)) + '\x1b[0m')
        print("Names of files that could not be cropped:")
        print(failedCrops)






#adjusted from document_image.py
def save_original_image(prefix, filedir, filename):
    lastDotOccurance = filename.rfind(".")
    filenameWithoutExtension = filename[:lastDotOccurance]
    extension = filename[lastDotOccurance:]

    new_path = prefix + filedir + filenameWithoutExtension + "_original" + extension
    img = Image.open(prefix + filedir + filename)
    img.save(new_path)


#copied from document_image.py
def crop_image(prefix, filedir, filename):
    print(prefix+filedir+filename)
    fullPath = prefix + filedir + filename
    img_blurr = Image.open(fullPath)
    img_cropped = Image.open(fullPath)

    img_blurr = img_blurr.resize((Static.img_size[0], Static.img_size[1]))
    img_blurr = img_blurr.filter(ImageFilter.BoxBlur(Static.blurr_radius))

    if (
            img_cropped.width > Static.img_size[0]
            or img_cropped.height > Static.img_size[1]
    ):
        img_cropped.thumbnail(Static.img_size)
    elif (img_cropped.width / img_cropped.height) > (
            Static.img_size[0] / Static.img_size[1]
    ):
        img_cropped = img_cropped.resize(
            (
                Static.img_size[0],
                round(
                    (Static.img_size[0] / img_cropped.width) * img_cropped.height
                ),
            )
        )
    else:
        img_cropped = img_cropped.resize(
            (
                round(Static.img_size[1] / img_cropped.height) * img_cropped.width,
                Static.img_size[1],
            )
        )

    offset = (
        ((img_blurr.width - img_cropped.width) // 2),
        ((img_blurr.height - img_cropped.height) // 2),
    )
    img_blurr.paste(img_cropped, offset)
    img_blurr.save(fullPath)



execute_image_cropping()
