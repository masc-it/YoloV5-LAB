#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import sys
from pathlib import Path

import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame
backend = "glfw"

import glfw
from imgui.integrations.glfw import GlfwRenderer

import OpenGL.GL as gl
from stb import image as im
import imgui
from yolov5 import detect
from file_selector import file_selector
import threading
import glob
import ctypes
myappid = 'mascit.app.yololab' # arbitrary string
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

io = None
image_texture, image_width, image_height = None, None, None

frame_data = {

    "num_imgs" : 0,
    "is_running": False,
    "img": "",
    "image_texture" : None,
    "done": False,
    "predictions" : None,
    "selected_file" : {
        "path": None,
        "idx": 0,
        "texture":None,
        "image_width" : None,
        "image_height": None
    },
    "progress": 0,
    "folder_path": "D:/Projects/python/semantics/project/test_final/imgs", #D:/Projects/python/semantics/project/test_final/images
    "model_path": "D:/Projects/python/pdf-toolbox/pdf_toolbox/backend/data/pdf_best_multi_nano.pt", #D:/Projects/python/pdf-toolbox/pdf_toolbox/backend/data/pdf_best_multi_nano.pt
    "threshold_conf": 0.55,
    "threshold_iou" : 0.45
}

def fb_to_window_factor(window):
    win_w, win_h = glfw.get_window_size(window)
    fb_w, fb_h = glfw.get_framebuffer_size(window)

    return max(float(fb_w) / win_w, float(fb_h) / win_h)

def main_glfw():
    global image_texture
    global image_width
    global image_height

    def glfw_init():
        width, height = 1024, 900
        window_name = "YoloV5 GUI"
        if not glfw.init():
            print("Could not initialize OpenGL context")
            exit(1)
        # OS X supports only forward-compatible core profiles from 3.2
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, gl.GL_TRUE)
        glfw.window_hint(glfw.REFRESH_RATE, 60)
        # Create a windowed mode window and its OpenGL context
        window = glfw.create_window(
            int(width), int(height), window_name, None, None
        )

        glfw.make_context_current(window)
        if not window:
            glfw.terminate()
            print("Could not initialize Window")
            exit(1)
        return window
    window = glfw_init()
    impl = GlfwRenderer(window)
    io = impl.io

    x = im.load('chip.png')
    glfw.set_window_icon(window, 1, [(x.shape[1],x.shape[0], x)])
    
    io.fonts.clear()
    font_scaling_factor = fb_to_window_factor(window)
    io.font_global_scale = 1. / font_scaling_factor
    
    io.fonts.add_font_from_file_ttf("Roboto-Regular.ttf", 18, io.fonts.get_glyph_ranges_latin())
    impl.refresh_font_texture()
    
    # frame_data["image_texture"], frame_data["image_width"], frame_data["image_height"] = load_image()
    prev_img = ""
    while not glfw.window_should_close(window):
        glfw.poll_events()
        impl.process_inputs()
        if frame_data["is_running"] and frame_data["img"] != "" and frame_data["img"] != prev_img:
            prev_img = frame_data["img"]
            frame_data["image_texture"], frame_data["image_width"], frame_data["image_height"] = load_image(frame_data["img"])
        
        if frame_data["done"] and frame_data["predictions"] is not None and frame_data["selected_file"]["texture"] is None:
            frame_data["selected_file"]["texture"], frame_data["selected_file"]["image_width"], frame_data["selected_file"]["image_height"] = load_image(frame_data["predictions"][frame_data["selected_file"]["idx"]])

        imgui.new_frame()
        on_frame()
        gl.glClearColor(1., 1., 1., 1)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        imgui.render()
        impl.render(imgui.get_draw_data())
        glfw.swap_buffers(window)
        time.sleep(0.0013)

    impl.shutdown()
    glfw.terminate()


def load_image(image_name):
    image = pygame.image.load(image_name)
    textureSurface = pygame.transform.flip(image, False, True)

    textureData = pygame.image.tostring(textureSurface, "RGB", 1)

    width = textureSurface.get_width()
    height = textureSurface.get_height()

    texture = gl.glGenTextures(1)
    gl.glBindTexture(gl.GL_TEXTURE_2D, texture)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
    gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGB, width, height, 0, gl.GL_RGB,
                    gl.GL_UNSIGNED_BYTE, textureData)

    return texture, width, height


def start_inference(frame_data):
    predictions = detect.run(weights=frame_data["model_path"], imgsz=[1280, 1280], conf_thres=frame_data["threshold_conf"], iou_thres=frame_data["threshold_iou"], save_conf=True,
                exist_ok=True, save_txt=True, source=frame_data["folder_path"], project=frame_data["folder_path"] + "/exp", name="predictions",)
        
    for _, (_, img)  in enumerate(predictions):
        # print(img)
        frame_data["img"] = img
        frame_data["progress"] += 0.1
        if not frame_data["is_running"]:
            break
        
    frame_data["is_running"] = False
    frame_data["progress"] = 0
    frame_data["done"] = True
# backend-independent frame rendering function:

def on_frame():
    global frame_data

    if imgui.begin_main_menu_bar():
        if imgui.begin_menu("File", True):
            clicked_quit, selected_quit = imgui.menu_item(
                "Quit", 'Cmd+Q', False, True
            )
            if clicked_quit:
                exit(1)
            imgui.end_menu()
        imgui.end_main_menu_bar()
    viewport = imgui.get_main_viewport().size
    imgui.set_next_window_size(viewport[0], viewport[1]-25, condition=imgui.ALWAYS)
    imgui.set_next_window_position(0, 25, condition=imgui.ALWAYS)
    flags = ( imgui.WINDOW_NO_MOVE 
        | imgui.WINDOW_NO_TITLE_BAR
        |   imgui.WINDOW_NO_COLLAPSE
        | imgui.WINDOW_NO_RESIZE
        
    )
    imgui.begin("Custom window", None, flags=flags)
    
    if frame_data["is_running"]:
        imgui.internal.push_item_flag(imgui.internal.ITEM_DISABLED, True)
        imgui.push_style_var(imgui.STYLE_ALPHA, imgui.get_style().alpha *  0.5)
    imgui.columns(2, "mycolumns3", False)
    # // 3-ways, no border
    
    model_btn_title = "Choose model path..."
    if imgui.button(model_btn_title):
        imgui.open_popup("Choose model path...")

    model_file = file_selector("Choose model path...", False)
    if model_file is not None:
        frame_data["model_path"] = model_file
    
    if frame_data["model_path"] != "":
        imgui.text(frame_data["model_path"])
    
    imgui.next_column()
    
    images_btn_title = "Choose images directory..."
    if imgui.button(images_btn_title):
        imgui.open_popup(images_btn_title)
    images_path = file_selector(images_btn_title, True)
    if images_path is not None:
        frame_data["folder_path"] = images_path
    if frame_data["folder_path"] != "":
        imgui.text(frame_data["folder_path"])
    
    
    imgui.next_column()
    imgui.separator()
    _, frame_data["threshold_conf"] = imgui.slider_float(
                label="Conf. threshold",
                value=frame_data["threshold_conf"],
                min_value=0.0,
                max_value=1.0,
                format="%.2f",
            )
    imgui.next_column()
    _, frame_data["threshold_iou"] = imgui.slider_float(
                label="IoU threshold",
                value=frame_data["threshold_iou"],
                min_value=0.0,
                max_value=1.0,
                format="%.2f",
            )
    imgui.separator()
    
    if frame_data["is_running"]:
        imgui.internal.pop_item_flag()
        imgui.pop_style_var()

    imgui.columns(1)
    if frame_data["is_running"]:
        start_clicked = imgui.button("Stop analysis")
    else:
        start_clicked = imgui.button("Start analysis")

    if start_clicked:

        if not frame_data["is_running"]:
            frame_data["is_running"] = True
            frame_data["progress"] = 0
            frame_data["done"] = False
            frame_data["predictions"] = None
            # call model
            imgs = glob.glob(frame_data["folder_path"] + "/*.jpg")
            frame_data["num_imgs"] = len(imgs)
            # print(f"running {frame_data['is_running']}")
            thread = threading.Thread(target=start_inference, args=(frame_data, ))
            thread.start()
        else:
            frame_data["is_running"] = False


    
    if frame_data["is_running"]:
        
        imgui.columns(3,"progr", False)
        imgui.next_column()
        imgui.progress_bar(
            fraction=frame_data["progress"] * 10 / frame_data["num_imgs"] , 
            size=(-1, 0.0),
            overlay=f"{int(frame_data['progress'] * 10)}/{frame_data['num_imgs']}"
        )
        imgui.columns(1)
        imgui.spacing()
        if frame_data["image_texture"] is not None:
            imgui.same_line((viewport[0] / 2) - (frame_data["image_width"] / 2))
            imgui.image(frame_data["image_texture"], frame_data["image_width"], frame_data["image_height"])
    
    if frame_data["done"]:
        if frame_data["predictions"] is None:
            frame_data["predictions"] = glob.glob(frame_data["folder_path"] + "/exp/predictions/*.jpg")
        
        
        imgui.begin_child(label="files_list", width=(viewport[0] / 5), height=-1, border=False, )
        
        for i, p in enumerate(frame_data["predictions"]):
            clicked, _ = imgui.selectable(
                        label=os.path.basename(p), selected=(frame_data["selected_file"]["idx"] == i)
                    )
            if clicked:
                frame_data["selected_file"]["texture"] = None
                frame_data["selected_file"]["idx"] = i
        imgui.end_child()
        imgui.same_line()
        imgui.begin_child(label="img_preview", width=-1, height=-1, border=False,)

        if frame_data["selected_file"]["texture"] is not None:
            imgui.image(frame_data["selected_file"]["texture"], frame_data["selected_file"]["image_width"], frame_data["selected_file"]["image_height"])
        imgui.end_child()

    imgui.end()



if __name__ == "__main__":
    imgui.create_context()

    io = imgui.get_io()
    
    backend = "glfw"
    main_glfw()
    