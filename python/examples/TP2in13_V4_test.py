#!/usr/bin/python
# -*- coding:utf-8 -*-
import sys
import os
picdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'pic/2in13')
fontdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'pic')
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)
    
from TP_lib import gt1151
from TP_lib import epd2in13_V4
import time
import logging
from PIL import Image,ImageDraw,ImageFont
import traceback
import threading

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
flag_t = 1

def pthread_irq() :
    logger.info("pthread running")
    while flag_t == 1 :
        if(gt.digital_read(gt.INT) == 0) :
            deviceTouchData.Touch = 1
        else :
            deviceTouchData.Touch = 0
    logger.info("thread:exit")

def Show_Photo_Small(image, small):
    for t in range(1, 5):
        if(small*2+t > 6):
            newimage = Image.open(os.path.join(picdir, PhotoPath_S[0]))
            image.paste(newimage, ((t-1)//2*45+2, (t%2)*124+2))
        else:
            newimage = Image.open(os.path.join(picdir, PhotoPath_S[small*2+t]))
            image.paste(newimage, ((t-1)//2*45+2, (t%2)*124+2))

def Show_Photo_Large(image, large):
    if(large > 6):
        newimage = Image.open(os.path.join(picdir, PhotoPath_L[0]))
        image.paste(newimage, (2, 2))
    else:
        newimage = Image.open(os.path.join(picdir, PhotoPath_L[large]))
        image.paste(newimage, (2, 2))

def Read_BMP(File, x, y):
    newimage = Image.open(os.path.join(picdir, File))
    image.paste(newimage, (x, y))

def prepare_text(text, font):
    """Create a rotated text image"""
    # Create temporary image for text measurement
    temp_img = Image.new('L', (1, 1))
    temp_draw = ImageDraw.Draw(temp_img)
    bbox = temp_draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Create image for the text
    text_img = Image.new('L', (text_width + 4, text_height + 4), 255)  # Add padding
    text_draw = ImageDraw.Draw(text_img)
    
    # Draw text
    text_draw.text((2, 2), text, font=font, fill=0)
    
    # Rotate and return
    return text_img.rotate(90, expand=True)

def create_grid_layout(image):
    """Create a grid layout filling the entire display"""
    draw = ImageDraw.Draw(image)
    
    # Display dimensions - swapped coordinate system
    # width (122) now maps to Y-axis, height (250) now maps to X-axis
    display_x = 122  # height becomes X dimension
    display_y = 250  # width becomes Y dimension
    
    # Clear the entire image to white first
    draw.rectangle([(0, 0), (display_x-1, display_y-1)], fill=255)
    
    top_rect_width = int(display_y / 2) - 1

    top_rect_height = int(((display_x * 3 / 7)  - 3))
    
    rect_labels = ["C Wall", "C End", "D Wall", "D End"]
    font = ImageFont.load_default()  # Load default font
    # Draw 4 rectangles in upper 3/4 area
    for i in range(4):
        x1 = (0 if i < 2 else 1) * (top_rect_height + 1) + 1  # Add 1 pixel separator
        y1 = ((i + 2) % 2) * (top_rect_width + 1)  # Add 1 pixel separator
        x2 = x1 + top_rect_height - 1
        y2 = y1 + top_rect_width - 1
        logger.debug(f"Drawing rectangle {i}: ({x1}, {y1}) to ({x2}, {y2})")
        
        # Draw white rectangle with black border
        draw.rectangle([(x1, y1), (x2, y2)], fill=255, outline=0, width=1)

        # Calculate center position for text
        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2
        
        text = prepare_text(draw, rect_labels[i], font)
        text_width, text_height = text.size

        # Calculate text position (top-left corner for centered text)
        text_x = center_x - text_width // 2
        text_y = center_y - text_height // 2
        
        # Draw centered text
        draw.text((text_x, text_y), text, font=font, fill=0)

    return image

try:
    logger.info("epd2in13_V4 Touch Demo")
    
    epd = epd2in13_V4.EPD()
    gt = gt1151.GT1151()
    deviceTouchData = gt1151.GT_Development()
    oldTouchData = gt1151.GT_Development()
    
    logger.info("init and Clear")
    
    epd.init(epd.FULL_UPDATE)
    gt.GT_Init()
    epd.Clear(0xFF)

    t = threading.Thread(target = pthread_irq)
    t.daemon = True
    t.start()

    # Drawing on the image
    #font15 = ImageFont.truetype(os.path.join(fontdir, 'Font.ttc'), 15)
    #font24 = ImageFont.truetype(os.path.join(fontdir, 'Font.ttc'), 24)
    
    #image = Image.open(os.path.join(picdir, 'Menu.bmp'))
    
    # Create a new white image
    image = Image.new('L', (122, 250), 255)  # Create white image (122x250 pixels)
    
    # Create the grid layout
    create_grid_layout(image)
    
    # Create drawing context
    DrawImage = ImageDraw.Draw(image)

    epd.displayPartBaseImage(epd.getbuffer(image))
    # DrawImage = ImageDraw.Draw(image)
    epd.init(epd.PART_UPDATE)
    
    touchEventCount = partialRefreshes = loopsSinceRefresh = ReFlag = SelfFlag = Page = Photo_L = Photo_S = 0
    PhotoPath_S = [ "Photo_1_0.bmp",
                    "Photo_1_1.bmp", "Photo_1_2.bmp", "Photo_1_3.bmp", "Photo_1_4.bmp",
                    "Photo_1_5.bmp", "Photo_1_6.bmp",
                    ]
    PhotoPath_L = [ "Photo_2_0.bmp",
                    "Photo_2_1.bmp", "Photo_2_2.bmp", "Photo_2_3.bmp", "Photo_2_4.bmp",
                    "Photo_2_5.bmp", "Photo_2_6.bmp",
                    ]
    PagePath = ["Menu.bmp", "White_board.bmp", "Photo_1.bmp", "Photo_2.bmp"]
    
    while(True):
        if(touchEventCount > 12 or ReFlag == 1):
            if(Page == 1 and SelfFlag == 0):
                epd.displayPartial(epd.getbuffer(image))
            else:
                epd.displayPartial_Wait(epd.getbuffer(image))
            touchEventCount = 0
            loopsSinceRefresh = 0
            partialRefreshes += 1
            ReFlag = 0
            logger.debug("*** Draw Refresh ***")
        elif(loopsSinceRefresh > 50000 and touchEventCount>0 and Page == 1):
            epd.displayPartial(epd.getbuffer(image))
            touchEventCount = 0
            loopsSinceRefresh = 0
            partialRefreshes += 1
            logger.debug("*** Overtime Refresh ***")
        elif(partialRefreshes > 50 or SelfFlag):
            SelfFlag = 0
            partialRefreshes = 0
            epd.init(epd.FULL_UPDATE)
            epd.displayPartBaseImage(epd.getbuffer(image))
            epd.init(epd.PART_UPDATE)
            logger.info("--- Self Refresh ---")
        else:
            loopsSinceRefresh += 1
        # Read the touch input
        gt.GT_Scan(deviceTouchData, oldTouchData)
        if(oldTouchData.X[0] == deviceTouchData.X[0] and oldTouchData.Y[0] == deviceTouchData.Y[0] and oldTouchData.S[0] == deviceTouchData.S[0]):
            continue
        
        if(deviceTouchData.TouchpointFlag):
            touchEventCount += 1
            deviceTouchData.TouchpointFlag = 0

            if(Page == 0 and ReFlag == 0):     #main menu
                if(deviceTouchData.X[0] > 29 and deviceTouchData.X[0] < 92 and deviceTouchData.Y[0] > 56 and deviceTouchData.Y[0] < 95):
                    logger.debug("Photo ...")
                    Page = 2
                    Read_BMP(PagePath[Page], 0, 0)
                    Show_Photo_Small(image, Photo_S)
                    ReFlag = 1
                elif(deviceTouchData.X[0] > 29 and deviceTouchData.X[0] < 92 and deviceTouchData.Y[0] > 153 and deviceTouchData.Y[0] < 193): 
                    logger.debug("Draw ...")
                    Page = 1
                    Read_BMP(PagePath[Page], 0, 0)
                    ReFlag = 1
                elif(deviceTouchData.X[0] > 0 and deviceTouchData.X[0] < 25 and deviceTouchData.Y[0] > 0 and deviceTouchData.Y[0] < 25):
                    logger.debug("Grid layout ...")
                    create_grid_layout(image)
                    ReFlag = 1
                
            
            if(Page == 1 and ReFlag == 0):   #white board
                DrawImage.rectangle([(deviceTouchData.X[0], deviceTouchData.Y[0]), (deviceTouchData.X[0] + deviceTouchData.S[0]/8 + 1, deviceTouchData.Y[0] + deviceTouchData.S[0]/8 + 1)], fill=0)
                if(deviceTouchData.X[0] > 96 and deviceTouchData.X[0] < 118 and deviceTouchData.Y[0] > 6 and deviceTouchData.Y[0] < 30): 
                    logger.debug("Home ...")
                    Page = 1
                    Read_BMP(PagePath[Page], 0, 0)
                    ReFlag = 1
                elif(deviceTouchData.X[0] > 96 and deviceTouchData.X[0] < 118 and deviceTouchData.Y[0] > 113 and deviceTouchData.Y[0] < 136): 
                    logger.debug("Clear ...")
                    Page = 0
                    Read_BMP(PagePath[Page], 0, 0)
                    ReFlag = 1
                elif(deviceTouchData.X[0] > 96 and deviceTouchData.X[0] < 118 and deviceTouchData.Y[0] > 220 and deviceTouchData.Y[0] < 242): 
                    logger.debug("Refresh ...")
                    SelfFlag = 1
                    ReFlag = 1
                
            
            if(Page == 2  and ReFlag == 0):  #photo menu
                if(deviceTouchData.X[0] > 97 and deviceTouchData.X[0] < 119 and deviceTouchData.Y[0] > 113 and deviceTouchData.Y[0] < 136): 
                    logger.debug("Home ...")
                    Page = 0
                    Read_BMP(PagePath[Page], 0, 0)
                    ReFlag = 1
                elif(deviceTouchData.X[0] > 97 and deviceTouchData.X[0] < 119 and deviceTouchData.Y[0] > 57 and deviceTouchData.Y[0] < 78): 
                    logger.debug("Next page ...")
                    Photo_S += 1
                    if(Photo_S > 2): # 6 photos is a maximum of three pages
                        Photo_S=0
                    ReFlag = 2
                elif(deviceTouchData.X[0] > 97 and deviceTouchData.X[0] < 119 and deviceTouchData.Y[0] > 169 and deviceTouchData.Y[0] < 190): 
                    logger.debug("Last page ...")
                    if(Photo_S == 0):
                        logger.debug("Top page ...")
                    else:
                        Photo_S -= 1
                        ReFlag = 2
                elif(deviceTouchData.X[0] > 97 and deviceTouchData.X[0] < 119 and deviceTouchData.Y[0] > 220 and deviceTouchData.Y[0] < 242): 
                    logger.debug("Refresh ...")
                    SelfFlag = 1
                    ReFlag = 1
                elif(deviceTouchData.X[0] > 2 and deviceTouchData.X[0] < 90 and deviceTouchData.Y[0] > 2 and deviceTouchData.Y[0] < 248 and ReFlag == 0):
                    logger.debug("Select photo ...")
                    Page = 3
                    Read_BMP(PagePath[Page], 0, 0)
                    Photo_L = int(deviceTouchData.X[0]/46*2 + 2-deviceTouchData.Y[0]/124 + Photo_S*2)
                    Show_Photo_Large(image, Photo_L)
                    ReFlag = 1
                if(ReFlag == 2):  # Refresh small photo
                    ReFlag = 1
                    Read_BMP(PagePath[Page], 0, 0)
                    Show_Photo_Small(image, Photo_S)   # show small photo
                
            
            if(Page == 3  and ReFlag == 0):     #view the photo
                if(deviceTouchData.X[0] > 96 and deviceTouchData.X[0] < 117 and deviceTouchData.Y[0] > 4 and deviceTouchData.Y[0] < 25): 
                    logger.debug("Photo menu ...")
                    Page = 2
                    Read_BMP(PagePath[Page], 0, 0)
                    Show_Photo_Small(image, Photo_S)
                    ReFlag = 1
                elif(deviceTouchData.X[0] > 96 and deviceTouchData.X[0] < 117 and deviceTouchData.Y[0] > 57 and deviceTouchData.Y[0] < 78): 
                    logger.debug("Next photo ...")
                    Photo_L += 1
                    if(Photo_L > 6):
                        Photo_L = 1
                    ReFlag = 2
                elif(deviceTouchData.X[0] > 96 and deviceTouchData.X[0] < 117 and deviceTouchData.Y[0] > 113 and deviceTouchData.Y[0] < 136): 
                    logger.debug("Home ...")
                    Page = 0
                    Read_BMP(PagePath[Page], 0, 0)
                    ReFlag = 1
                elif(deviceTouchData.X[0] > 96 and deviceTouchData.X[0] < 117 and deviceTouchData.Y[0] > 169 and deviceTouchData.Y[0] < 190): 
                    logger.debug("Last page ...")
                    if(Photo_L == 1):
                        logger.debug("Top photo ...")
                    else: 
                        Photo_L -= 1
                        ReFlag = 2
                elif(deviceTouchData.X[0] > 96 and deviceTouchData.X[0] < 117 and deviceTouchData.Y[0] > 220 and deviceTouchData.Y[0] < 242): 
                    logger.debug("Refresh photo ...")
                    SelfFlag = 1
                    ReFlag = 1
                if(ReFlag == 2):    # Refresh large photo
                    ReFlag = 1
                    Show_Photo_Large(image, Photo_L)
                
except IOError as e:
    logger.exception("IOError")
    
except KeyboardInterrupt:    
    logger.info("ctrl + c:")
    flag_t = 0
    epd.sleep()
    time.sleep(2)
    t.join()
    epd.Dev_exit()
    exit()
