
from __future__ import annotations
import os, glob, json,sys
from copy import deepcopy
from components.data import *
from typing import Generator, Any

sys.path.append("./")  # add ROOT to PATH
import custom_utils

class Project(object):
    
    page_status : dict = {}

    def __init__(self, name:str, info_obj: dict, project_path:str) -> None:
        self.name = name
        self.info_obj = info_obj
        self.collections_obj : dict = info_obj["collections"]
        self.model_path = info_obj["model_path"]
        self.labels_obj = info_obj["labels"]
        self.project_path = project_path

        self.imgs : dict[str, dict[str, ImageInfo]] = {}
        self.collections : dict[str, CollectionInfo]= {}
        self.labels : Labels = self.load_labels()

        self.experiments : dict[str, Experiment] = {}
        self.load_experiments()
        

    def __str__(self) -> str:
        return json.dumps(self.info_obj, indent=1)
    
    def init_project(self):
        for p in self.collections_obj:
            collection = self.collections_obj[p]
            data_path = collection["data_path"]
            collection_name = collection["name"]
            collection_id = collection["name"].lower().replace(" ", "_")

            coll_info = CollectionInfo(collection_name, collection_id, data_path)
            self.collections[collection_id] = coll_info
            self.imgs[collection_id] = {}
            os.makedirs(data_path + "/annotations", exist_ok=True)
            # init imgs dict with imgs in data_path
            for f in glob.glob(data_path + "/*.jpg"):
                name_ext = os.path.basename(f).rsplit('.')
                img_name = name_ext[0]
                img_ext = name_ext[1]
                self.imgs[collection_id][img_name] = ImageInfo(img_name, img_ext, coll_info)
        self.load_annotations()        
    
    def get_collection(self, collection_id: str) -> CollectionInfo:
        return self.collections[collection_id]
    
    def import_yolo_annotations(self, data_path, yolo_annotations_path):

        for f in glob.glob(f"{yolo_annotations_path}/*.txt"):
            name = os.path.basename(f).rsplit('.')[0]

            img_path = f"{data_path}/{name}.jpg"
            img_info = ImageInfo(name, img_path)
            bboxes = custom_utils.import_yolo_predictions(f, img_info.w, img_info.h)

            img_info.add_bboxes(bboxes)
            self.imgs[name] = img_info
            
            if not os.path.exists(f"projects/{self.name}/annotations/{name}.json"):
                bboxes_list = list(map(lambda x: x.as_obj(), bboxes))
                with open(f"projects/{self.name}/annotations/{name}.json", "w") as fp:
                    data = {"img_path": img_path, "bboxes": bboxes_list}
                    json.dump(data, fp, indent=1)
    
    def load_annotations(self, ):

        for collection in self.collections.values():

            for img_name in self.imgs[collection.id]:
                img_info : ImageInfo = self.imgs[collection.id][img_name]

                annotation_file = f"{collection.path}/annotations/{img_name}.json"
                if not os.path.exists(annotation_file):
                    continue
                with open(annotation_file, "r") as fp:
                    data = json.load(fp)

                bboxes = list(map(lambda x: BBox(x["xmin"],x["ymin"],x["xmax"],x["ymax"], x["label"], x["conf"]), data["bboxes"]))

                img_info.add_bboxes(bboxes)
    
    @staticmethod
    def load_img_annotations(img_info : ImageInfo):

        img_name = img_info.name
        
        collection = img_info.collection_info

        annotation_file = f"{collection.path}/annotations/{img_name}.json"
        if not os.path.exists(annotation_file):
            return
        with open(annotation_file, "r") as fp:
            data = json.load(fp)

        bboxes = list(map(lambda x: BBox(x["xmin"],x["ymin"],x["xmax"],x["ymax"], x["label"], x["conf"]), data["bboxes"]))

        img_info.add_bboxes(bboxes)
    
    def get_image(self, collection_id) -> Generator[ImageInfo, Any, Any]:
        for img in self.imgs[collection_id]:
            yield self.imgs[collection_id][img]

    def load_labels(self):

        labels = Labels()
        for k in self.info_obj["labels"]:
            obj = self.info_obj["labels"][k]
            l = LabelInfo(
                obj["index"], 
                obj["label"],
                [ color / 255.0 for color in obj["rgb"]],
                obj["shortcut"])
            labels.add_label(l)
        return labels
    
    def update_labels(self, save=True):

        labels_obj = {}
        for o in self.labels:
            labels_obj[o.index] = o.as_obj(rgb_int=True)
        
        self.info_obj["labels"] = labels_obj
        if save:
            self.save_config()

    def save_config(self):
        with open(f"projects/{self.name}/info.json", "w") as fp:
            json.dump(self.info_obj, fp, indent=1)

    def load_json_annotation(self, img_name):

        with open(f"projects/{self.name}/annotations/{img_name}.json", "r") as fp:
            annotations = json.load(fp)
        
        return annotations
    
    def set_changed(self, img_name):

        self.page_status[img_name] = True

    def save_annotations(self,):
        
        for collection in self.collections.values():
            for img_name in self.imgs[collection.id]:
                img_info : ImageInfo = self.imgs[collection.id][img_name]
                if img_info.is_changed:
                    with open(f"{collection.path}/annotations/{img_name}.json", "w") as fp:
                        scaled_bboxes = []
                        for bbox in img_info.bboxes:
                            scaled_bboxes.append(bbox.scale((img_info.w, img_info.h), (img_info.orig_w, img_info.orig_h)).as_obj())
                        data = {"collection": collection.id, "bboxes": scaled_bboxes}
                        json.dump(data, fp, indent=1 )
                    img_info.set_changed(False)

    def load_experiments(self):
        
        with open(f"{self.project_path}/experiments.json", "r") as fp:
            exp_obj =json.load(fp)
        
        for exp_key in exp_obj:
            exp = Experiment("", exp_obj[exp_key], exp_key) 
            self.experiments[exp_key] = exp
        
        return self.experiments

def load_projects():

    projects = []
    for p in glob.glob("projects/*"):
        
        with open(p + "/info.json", "r") as fp:
            info_obj = json.load(fp)
        projects.append(Project(os.path.basename(p), info_obj, p))
    
    return projects


if __name__ == "__main__":
    for p in load_projects():
        print(p)