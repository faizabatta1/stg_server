
import argparse
import os
import numpy as np
import matplotlib.pyplot as plt
import platform
import cv2
#from google.colab.patches import cv2_imshow
import sys
from pathlib import Path

import torch

__file__=os.getcwd()
FILE = Path(__file__).resolve()
ROOT = FILE.parents[0]  # YOLOv5 root directory
ROOT = str(ROOT) + '/yolov5'  
if str(ROOT) not in sys.path:   
    sys.path.append(str(ROOT))  # add ROOT to PATH
ROOT = Path(os.path.relpath(ROOT, Path.cwd()))  # relative

from models.common import DetectMultiBackend
from utils.dataloaders import IMG_FORMATS, VID_FORMATS, LoadImages, LoadScreenshots, LoadStreams
from utils.general import (LOGGER, Profile, check_file, check_img_size, check_imshow, colorstr, cv2,
                           increment_path, non_max_suppression, print_args, scale_boxes, strip_optimizer, xyxy2xywh)
from utils.plots import Annotator, colors, save_one_box
from utils.torch_utils import select_device, smart_inference_mode

  
@smart_inference_mode()
def run_1(source, 
        weights=ROOT / 'runs/train/exp7/weights/best.pt',#'yolov5/runs/train/exp3/weights/best.pt',#ROOT / 'yolov5s.pt',  # model path or triton URL
         #ROOT / 'tstImg_5.jpg',  #'yolov5/tstImg_5.jpg',#ROOT / 'data/images',  # file/dir/URL/glob/screen/0(webcam)
        data=ROOT / 'data_3.yaml',#'yolov5/data_1.yaml',#ROOT / 'data/coco128.yaml',  # dataset.yaml path
        imgsz=(1024, 1024),  # inference size (height, width)
        conf_thres=0.5,#0.25,  # confidence threshold
        iou_thres=0.45,  # NMS IOU threshold
        max_det=1000,  # maximum detections per image
        device='',  # cuda device, i.e. 0 or 0,1,2,3 or cpu
        view_img=False,  # show results
        save_txt=False,  # save results to *.txt
        save_conf=False,  # save confidences in --save-txt labels
        save_crop=False,  # save cropped prediction boxesS
        nosave=False,  # do not save images/videos
        classes=None,  # filter by class: --class 0, or --class 0 2 3
        agnostic_nms=False,  # class-agnostic NMS
        augment=False,  # augmented inference
        visualize=False,  # visualize features
        update=False,  # update all models
        project=ROOT / 'runs/detect',  #'yolov5/runs/detect',#ROOT / 'runs/detect',  # save results to project/name
        name='exp',  # save results to project/name
        exist_ok=False,  # existing project/name ok, do not increment
        line_thickness=1,  # bounding box thickness (pixels)
        hide_labels=True,  # hide labels
        hide_conf=True,  # hide confidences
        half=False,  # use FP16 half-precision inference
        dnn=False,  # use OpenCV DNN for ONNX inference
        vid_stride=1,  # video frame-rate stride
):
    #if source is None:
     #   source = input("Enter path to source image: ")
    source = str(source)
    save_img = not nosave and not source.endswith('.txt')  # save inference images
    is_file = Path(source).suffix[1:] in (IMG_FORMATS + VID_FORMATS)
    is_url = source.lower().startswith(('rtsp://', 'rtmp://', 'http://', 'https://'))
    webcam = source.isnumeric() or source.endswith('.streams') or (is_url and not is_file)
    screenshot = source.lower().startswith('screen')
    if is_url and is_file:
        source = check_file(source)  # download

    # Directories
    save_dir = increment_path(Path(project) / name, exist_ok=exist_ok)  # increment run
    (save_dir / 'labels' if save_txt else save_dir).mkdir(parents=True, exist_ok=True)  # make dir

    # Load model
    device = select_device(device)
    model = DetectMultiBackend(weights, device=device, dnn=dnn, data=data, fp16=half)
    stride, names, pt = model.stride, model.names, model.pt
    imgsz = check_img_size(imgsz, s=stride)  # check image size

    # Dataloader
    bs = 1  # batch_size
    if webcam:
        view_img = check_imshow(warn=True)
        dataset = LoadStreams(source, img_size=imgsz, stride=stride, auto=pt, vid_stride=vid_stride)
        bs = len(dataset)
    elif screenshot:
        dataset = LoadScreenshots(source, img_size=imgsz, stride=stride, auto=pt)
    else:
        dataset = LoadImages(source, img_size=imgsz, stride=stride, auto=pt, vid_stride=vid_stride)
    vid_path, vid_writer = [None] * bs, [None] * bs

    # Run inference
    model.warmup(imgsz=(1 if pt or model.triton else bs, 3, *imgsz))  # warmup
    seen, windows, dt = 0, [], (Profile(), Profile(), Profile())
    for path, im, im0s, vid_cap, s in dataset:
        with dt[0]:
            im = torch.from_numpy(im).to(model.device)
            im = im.half() if model.fp16 else im.float()  # uint8 to fp16/32
            im /= 255  # 0 - 255 to 0.0 - 1.0
            if len(im.shape) == 3:
                im = im[None]  # expand for batch dim

        # Inference
        with dt[1]:
            visualize = increment_path(save_dir / Path(path).stem, mkdir=True) if visualize else False
            pred = model(im, augment=augment, visualize=visualize)

        # NMS
        with dt[2]:
            pred = non_max_suppression(pred, conf_thres, iou_thres, classes, agnostic_nms, max_det=max_det)

        # Second-stage classifier (optional)
        # pred = utils.general.apply_classifier(pred, classifier_model, im, im0s)

        # Process predictions
        for i, det in enumerate(pred):  # per image
            seen += 1
            if webcam:  # batch_size >= 1
                p, im0, frame = path[i], im0s[i].copy(), dataset.count
                s += f'{i}: '
            else:
                p, im0, frame = path, im0s.copy(), getattr(dataset, 'frame', 0)

            p = Path(p)  # to Path
            save_path = str(save_dir / p.name)  # im.jpg
            txt_path = str(save_dir / 'labels' / p.stem) + ('' if dataset.mode == 'image' else f'_{frame}')  # im.txt
            s += '%gx%g ' % im.shape[2:]  # print string
            gn = torch.tensor(im0.shape)[[1, 0, 1, 0]]  # normalization gain whwh
            imc = im0.copy() if save_crop else im0  # for save_crop
            annotator = Annotator(im0, line_width=line_thickness, example=str(names))
            if len(det):
                # Rescale boxes from img_size to im0 size
                det[:, :4] = scale_boxes(im.shape[2:], det[:, :4], im0.shape).round()

                # Print results
                for c in det[:, 5].unique():
                    n = (det[:, 5] == c).sum()  # detections per class
                    s += f"{n} {names[int(c)]}{'s' * (n > 1)}, "  # add to string

                # Initialize variables to store maximum bounding box
                max_bbox = None
                max_area = 0

                # Write results
                for *xyxy, conf, cls in reversed(det):
                    area = (xyxy[2] - xyxy[0]) * (xyxy[3] - xyxy[1])  # calculate area of current bounding box
                    if area > max_area:
                        max_bbox = xyxy  # update maximum bounding box
                        max_area = area  # update maximum area

                    if save_txt:  # Write to file
                        xywh = (xyxy2xywh(torch.tensor(xyxy).view(1, 4)) / gn).view(-1).tolist()  # normalized xywh
                        line = (cls, *xywh, conf) if save_conf else (cls, *xywh)  # label format
                        with open(f'{txt_path}.txt', 'a') as f:
                            f.write(('%g ' * len(line)).rstrip() % line + '\n')

                    if save_img or save_crop or view_img:  # Add bbox to image
                        c = int(cls)  # integer class
                        label = None if hide_labels else (names[c] if hide_conf else f'{names[c]} {conf:.2f}')
                        annotator.box_label(max_bbox, label, color=colors(c, True))
                        #if xyxy == max_bbox:  # if current bbox is the maximum bbox, draw red bbox
                            #annotator.box_label(xyxy, label, color=(0, 0, 255))
                         #   mx_xyxy=xyxy
                        #else:
                            #annotator.box_label(xyxy, label, color=colors(c, True))
                         #   xyxy=xyxy

                    if save_crop:
                        save_one_box(max_bbox, imc, file=save_dir / 'crops' / names[c] / f'{p.stem}.jpg', BGR=True)

                    #here---------
                    #print("xyxy X1,Y1",xyxy[0].item()," ",xyxy[1].item(),"xyxy X2,Y2",xyxy[2].item()," ",xyxy[3].item())
                #print("max_bbox X1,Y1",max_bbox[0].item()," ",max_bbox[1].item(),"max_bbox X2,Y2",max_bbox[2].item()," ",max_bbox[3].item()," , max_area ",max_area) 
                # Define the top left and bottom right points of the ROI
                top_left = (int(max_bbox[0].item()),int( max_bbox[1].item()))
                bottom_right = (int(max_bbox[2].item()),int(max_bbox[3].item()))
                
                #im = im.cpu().detach().numpy().clip(0, 255).astype('uint8')
                #im = im.transpose((0,2, 3, 1))
                
                # Extract the ROI
                # Define the target size
                target_size = ( 86,155)
                
                roi = im0[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0]] 
                roi = cv2.cvtColor(roi, cv2.COLOR_RGB2BGR)  # Convert from RGB to BGR color space
                roi= cv2.resize(roi, target_size, interpolation=cv2.INTER_AREA)  # Resize the image
                # Apply the bilateral filter
                #roi = cv2.bilateralFilter(roi, 9, 75, 75)

                
                #sec_roi = im[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0]] 
                #print(" im shape : ",im.shape)
                #print(" im0 shape : ",im0.shape)                
                #print(" top_left : ",top_left) 
                #print(" bottom_right : ",bottom_right) 
                #print(" roi shape : ",roi.shape) 
               
                # Convert to NumPy array of type uint8
                #roi = roi.cpu().numpy().clip(0, 255).astype('uint8')
                #roi = roi.cpu().detach().numpy().clip(0, 255).astype('uint8')
                #roi = roi.transpose((2, 3, 0))
                 
                # Convert the array to a shape (1024, 1024) uint8 data type
                #roi = roi.squeeze().astype(np.uint8)
                
                # Display the ROI
                # Show image
                #cv2_imshow(im0)
                #cv2.waitKey(0)  # 1 millisecond
                #cv2.destroyAllWindows()
                #cv2_imshow(roi)
                #cv2.waitKey(0)  # 1 millisecond
                #cv2.destroyAllWindows()
                # Save images to disk
                #cv2.imwrite("im0.jpg", im0)
                ############cv2.imwrite("roi.jpg", roi)
                cv2.imwrite("sec_roi.jpg", roi)
                
                
                 
                    



            # Stream results
            im0 = annotator.result()
            if view_img:
                if platform.system() == 'Linux' and p not in windows:
                    windows.append(p)
                    cv2.namedWindow(str(p), cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)  # allow window resize (Linux)
                    cv2.resizeWindow(str(p), im0.shape[1], im0.shape[0])
                #cv2.imshow(str(p), im0)
                #cv2.waitKey(1)  # 1 millisecond

            # Save results (image with detections)
            if save_img:
                if dataset.mode == 'image':
                    cv2.imwrite(save_path, im0)
                else:  # 'video' or 'stream' 
                    if vid_path[i] != save_path:  # new video
                        vid_path[i] = save_path
                        if isinstance(vid_writer[i], cv2.VideoWriter):
                            vid_writer[i].release()  # release previous video writer
                        if vid_cap:  # video
                            fps = vid_cap.get(cv2.CAP_PROP_FPS)
                            w = int(vid_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                            h = int(vid_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        else:  # stream
                            fps, w, h = 30, im0.shape[1], im0.shape[0]
                        save_path = str(Path(save_path).with_suffix('.mp4'))  # force *.mp4 suffix on results videos
                        vid_writer[i] = cv2.VideoWriter(save_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
                    vid_writer[i].write(im0)

        # Print time (inference-only)
        #LOGGER.info(f"{s}{'' if len(det) else '(no detections), '}{dt[1].dt * 1E3:.1f}ms")
    #return roi
    # Print results
    t = tuple(x.t / seen * 1E3 for x in dt)  # speeds per image
    LOGGER.info(f'Speed: %.1fms pre-process, %.1fms inference, %.1fms NMS per image at shape {(1, 3, *imgsz)}' % t)
    if save_txt or save_img:
        s = f"\n{len(list(save_dir.glob('labels/*.txt')))} labels saved to {save_dir / 'labels'}" if save_txt else ''
        LOGGER.info(f"Results saved to {colorstr('bold', save_dir)}{s}")
    if update:
        strip_optimizer(weights[0])  # update model (to fix SourceChangeWarning)
  


    
"""  

def main(opt):
    check_requirements(exclude=('tensorboard', 'thop'))
    run(**vars(opt))


if __name__ == '__main__':
    opt = parse_opt()
    main(opt)
    
    
"""      