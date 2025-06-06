#!/usr/bin/python
# -*- coding:utf-8 -*-
import sys
import os
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

font_large = ImageFont.truetype(os.path.join(fontdir, 'Font.ttc'), 16)
font_small = ImageFont.truetype(os.path.join(fontdir, 'Font.ttc'), 14)

class ButtonSpec:
    def __init__(self, name, xmin, ymin, xmax, ymax, isWhite=True):
        self.name = name
        self.xmin = xmin
        self.ymin = ymin
        self.xmax = xmax
        self.ymax = ymax
        self.isWhite = isWhite

    def isPressed(self, x, y):
        return self.xmin <= x <= self.xmax and self.ymin <= y <= self.ymax

def pthread_irq() :
    logger.info("pthread running")
    while flag_t == 1 :
        if(gt.digital_read(gt.INT) == 0) :
            deviceTouchData.Touch = 1
        else :
            deviceTouchData.Touch = 0
    logger.info("thread:exit")

def prepare_text(text, font, isWhite=True, padding=(2,2)):
    """Create a rotated text image"""
    # Create temporary image for text measurement
    temp_img = Image.new('L', (1, 1))
    temp_draw = ImageDraw.Draw(temp_img)
    bbox = temp_draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Create image for the text
    text_img = Image.new('L', (text_width + 4, text_height + 4), 255 if isWhite else 0)
    text_draw = ImageDraw.Draw(text_img)
    
    # Draw text
    text_draw.text(padding, text, font=font, fill=(0 if isWhite else 255))
    
    # Rotate and return
    return text_img.rotate(90, expand=True)

def toggle_button(image, button_spec, font):
    x_size = button_spec.xmax - button_spec.xmin + 1
    y_size = button_spec.ymax - button_spec.ymin + 1
    isWhite = not button_spec.isWhite
    button_image = Image.new('L', (x_size, y_size), 255 if isWhite else 0)

    draw = ImageDraw.Draw(button_image)
    draw.rectangle([(0, 0), (x_size-1, y_size-1)], fill=(255 if isWhite else 0), outline=(0 if isWhite else 255), width=1)

    # Calculate center position for text
    center_x = x_size // 2
    center_y = y_size // 2
    
    text = prepare_text(button_spec.name, font, isWhite)
    text_width, text_height = text.size

    # Calculate text position (top-left corner for centered text)
    text_x = center_x - text_width // 2
    text_y = center_y - text_height // 2
    
    # Draw centered text
    button_image.paste(text, (text_x, text_y))
    image.paste(button_image, (button_spec.xmin, button_spec.ymin))
    button_spec.isWhite = isWhite  # Toggle the state


def create_grid_layout(image, font):
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
    button_specs = []
    # Draw 4 rectangles in upper area
    for i in range(4):
        button_name = rect_labels[i]
        x1 = (0 if i < 2 else 1) * (top_rect_height + 1) + 1  # Add 1 pixel separator
        y1 = ((i + 2) % 2) * (top_rect_width + 1)  # Add 1 pixel separator
        x2 = x1 + top_rect_height - 1
        y2 = y1 + top_rect_width - 1
        button_specs.append(ButtonSpec(button_name, x1, y1, x2, y2))
        logger.debug(f"Drawing rectangle {i}: ({x1}, {y1}) to ({x2}, {y2})")
        
        # Draw white rectangle with black border
        draw.rectangle([(x1, y1), (x2, y2)], fill=255, outline=0, width=1)

        # Calculate center position for text
        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2
        
        text = prepare_text(button_name, font)
        text_width, text_height = text.size

        # Calculate text position (top-left corner for centered text)
        text_x = center_x - text_width // 2
        text_y = center_y - text_height // 2
        
        # Draw centered text
        image.paste(text, (text_x, text_y))

    bottom_area_top = 4 + (2 * top_rect_height)
    bottom_area_height = 125 - bottom_area_top
    logger.debug(f"Bottom button: top = {bottom_area_top}, height = {bottom_area_height}")


    on_text = prepare_text("ON", font_small, isWhite=True, padding=(0, 0))
    on_text_width, on_text_height = on_text.size
    on_text_x = bottom_area_top + bottom_area_height // 2 - on_text_height // 2
    on_text_y = (250 //4) * 3 - on_text_width
    logger.debug(f"On text: height = {on_text_height} width = {on_text_width} x = {on_text_x}, y = {on_text_y}")
    image.paste(on_text, (on_text_x, on_text_y))

    off_text = prepare_text("OFF", font_small, isWhite=True, padding=(0, 0))
    off_text_width, off_text_height = off_text.size
    off_text_x = on_text_x
    off_text_y = (250 //4) - off_text_width
    logger.debug(f"Off text: height = {off_text_height} width = {off_text_width} x = {off_text_x}, y = {off_text_y}")
    image.paste(off_text, (off_text_x, off_text_y))

    return button_specs

try:
    logger.info("Wall Heater Controller")
    
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

    # Create a new white image
    image = Image.new('L', (122, 250), 255)  # Create white image (122x250 pixels)
    
    # Create the grid layout
    button_specs = create_grid_layout(image, font_large)
    
    # Create drawing context
    DrawImage = ImageDraw.Draw(image)

    epd.displayPartBaseImage(epd.getbuffer(image))
    epd.init(epd.PART_UPDATE)
    
    touchEventCount = partialRefreshes = loopsSinceRefresh = ReFlag = SelfFlag = Page = Photo_L = Photo_S = 0
    
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

            for button_spec in button_specs:
                if button_spec.isPressed(deviceTouchData.X[0], deviceTouchData.Y[0]):
                    logger.debug(f"Button {button_spec.name} pressed at ({deviceTouchData.X[0]}, {deviceTouchData.Y[0]})")
                    toggle_button(image, button_spec, font_large)
                    ReFlag = 1
                    break
                
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
