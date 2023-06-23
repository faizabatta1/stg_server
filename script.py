import cv2
from before import run_1
from after import run_2


def translate(pic_path):
    # Call the run_1() function
    run_1(source=pic_path)

    # Call the run_2() function
    txt = run_2()

    return txt


if __name__ == '__main__':
    print("the name of king : ", translate("photo_2_2023-06-22_11-03-41.jpg"))