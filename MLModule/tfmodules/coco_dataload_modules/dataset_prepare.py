# -*- coding: utf-8 -*-
# @Time    : 18-3-6 3:20 PM
# @Author  : edvard_hua@live.com
# @FileName: data_prepare.py
# @Software: PyCharm
# @updated by Jaewook Kang 20180803 for dontbeturtle proj in Google camp 2018


import numpy as np
import cv2
import struct
import math
from coco_dataload_modules.dataset_augment import CocoPart

class CocoPose:
    @staticmethod
    def get_bgimg(inp, target_size=None):
        inp = cv2.cvtColor(inp.astype(np.uint8), cv2.COLOR_BGR2RGB)
        if target_size:
            inp = cv2.resize(inp, target_size, interpolation=cv2.INTER_AREA)
        return inp

    @staticmethod
    def display_image(inp, heatmap=None, pred_heat=None, as_numpy=False):
        global mplset
        mplset = True
        import matplotlib.pyplot as plt

        fig = plt.figure()
        if heatmap is not None:
            a = fig.add_subplot(1, 2, 1)
            a.set_title('True_Heatmap')
            plt.imshow(CocoPose.get_bgimg(inp, target_size=(heatmap.shape[1], heatmap.shape[0])), alpha=0.5)
            tmp = np.amax(heatmap, axis=2)
            plt.imshow(tmp, cmap=plt.cm.gray, alpha=0.7)
            plt.colorbar()
        else:
            a = fig.add_subplot(1, 2, 1)
            a.set_title('Image')
            plt.imshow(CocoPose.get_bgimg(inp))

        if pred_heat is not None:
            a = fig.add_subplot(1, 2, 2)
            a.set_title('Pred_Heatmap')
            plt.imshow(CocoPose.get_bgimg(inp, target_size=(pred_heat.shape[1], pred_heat.shape[0])), alpha=0.5)
            tmp = np.amax(pred_heat, axis=2)
            plt.imshow(tmp, cmap=plt.cm.gray, alpha=1)
            plt.colorbar()

        if not as_numpy:
            plt.show()
        else:
            fig.canvas.draw()
            data = np.fromstring(fig.canvas.tostring_rgb(), dtype=np.uint8, sep='')
            data = data.reshape(fig.canvas.get_width_height()[::-1] + (3,))

            fig.clear()
            plt.close()
            return data


class CocoMetadata:
    __coco_parts = 14

    @staticmethod
    def parse_float(four_np):
        assert len(four_np) == 4
        return struct.unpack('<f', bytes(four_np))[0]

    @staticmethod
    def parse_floats(four_nps, adjust=0):
        assert len(four_nps) % 4 == 0
        return [(CocoMetadata.parse_float(four_nps[x * 4:x * 4 + 4]) + adjust) for x in range(len(four_nps) // 4)]

    def __init__(self, idx, img_path, img_meta, annotations, sigma):
        self.idx = idx
        self.img = self.read_image(img_path)
        self.sigma = sigma

        self.height = int(img_meta['height'])
        self.width  = int(img_meta['width'])

        joint_list = []
        # print('annotations = %s' % annotations)
        for ann in annotations:
            if ann.get('num_keypoints', 0) == 0:
                continue

            kp = np.array(ann['keypoints'])
            xs = kp[0::3]
            ys = kp[1::3]
            vs = kp[2::3]

            joint_list.append([(x, y) if v >= 1 else (-1000, -1000) for x, y, v in zip(xs, ys, vs)])

            # print('xs= %s'% kp[0::3])
            # print('ys= %s'% kp[1::3])
            # print('vs= %s'% kp[2::3])
        '''
        [{"supercategory": "human", 
        "skeleton": [[1, 2], [2, 3], [2, 4], [3, 5], 
        [5, 7], [4, 6], [6, 8], [2, 9], [2, 10], [9, 11], [10, 12], [11, 13], [12, 14]], 
        "id": 1, 
        "keypoints": ["top_head", "neck", "left_shoulder", "right_shoulder", 
        "left_elbow", "right_elbow", "left_wrist", "right_wrist", "left_hip", 
        "right_hip", "left_knee", "right_knee", "left_ankle", "right_ankle"], 
        "name": "human"}]
        '''
        # for coor_list in joint_list:
        #     print('joint_list = %s\n' % coor_list)
        # print('----------------------------------')

        self.joint_list = []

        transform = list(zip(
            [1, 2, 4, 6, 8, 3, 5, 7, 10, 12, 14, 9, 11, 13],
            [1, 2, 4, 6, 8, 3, 5, 7, 10, 12, 14, 9, 11, 13]
        ))
        for prev_joint in joint_list:
            new_joint = []
            for idx1, idx2 in transform:
                j1 = prev_joint[idx1 - 1]
                j2 = prev_joint[idx2 - 1]

                if j1[0] <= 0 or j1[1] <= 0 or j2[0] <= 0 or j2[1] <= 0:
                    new_joint.append((-1000, -1000))
                else:
                    new_joint.append(((j1[0] + j2[0]) / 2, (j1[1] + j2[1]) / 2))
            # background
            # new_joint.append((-1000, -1000))
            self.joint_list.append(new_joint)

    def get_heatmap(self, target_size):
        heatmap = np.zeros((CocoMetadata.__coco_parts, self.height, self.width), dtype=np.float32)

        # print ('target_size=',target_size)
        for joints in self.joint_list:
            for idx, point in enumerate(joints):

                if point[0] < 0 or point[1] < 0:
                    # uniform labeling for mislabeled data
                    heatmap[idx,:,:] = 1.0 / (target_size[0] * target_size[1])
                    continue

                CocoMetadata.put_heatmap(heatmap, idx, point, self.sigma)

        heatmap = heatmap.transpose((1, 2, 0))

        # background
        # heatmap[:, :, -1] = np.clip(1 - np.amax(heatmap, axis=2), 0.0, 1.0)

        #---------------------------------------------
        # taking only top neck Rshoulder Lshoulder for dontbe turtle proj
        # by jaewook kang
        # Top = 0
        # Neck = 1
        # RShoulder = 2
        # LShoulder = 5

        bodyparts_list = [CocoPart.Top.value,\
                          CocoPart.Neck.value,\
                          CocoPart.LShoulder.value,\
                          CocoPart.RShoulder.value]
        heatmap = heatmap[:,:,bodyparts_list]
        #---------------------------------------------


        if target_size:
            heatmap = cv2.resize(heatmap, target_size, interpolation=cv2.INTER_AREA)
        # print ('[get_heatmap] heatmap shape: %s', heatmap.shape)

        # heatmap normalization
        # for index in range(len(bodyparts_list)):
        #     if abs(sum(sum(heatmap[:, :, index]))) > 0:
        #         heatmap[:,:,index] = heatmap[:,:,index] / sum(sum(heatmap[:,:,index]))
        #         # print('sum of heatmap[:,:,%s] = %s' %(index,sum(sum(heatmap[:,:,index]))))


        return heatmap.astype(np.float16)



    @staticmethod
    # the below function actually made heatmap
    def put_heatmap(heatmap, plane_idx, center, sigma):
        center_x, center_y = center
        _, height, width = heatmap.shape[:3]

        th = 1.6052
        delta = math.sqrt(th * 2)

        if center_x == 0 and center_y == 0 :
            print ('plane_idx = %s' % plane_idx)

        x0 = int(max(0, center_x - delta * sigma))
        y0 = int(max(0, center_y - delta * sigma))

        x1 = int(min(width, center_x + delta * sigma))
        y1 = int(min(height, center_y + delta * sigma))

        # gaussian filter
        for y in range(y0, y1):
            for x in range(x0, x1):
                d = (x - center_x) ** 2 + (y - center_y) ** 2
                exp = d / 2.0 / sigma / sigma
                if exp > th:
                    continue
                heatmap[plane_idx][y][x] = max(heatmap[plane_idx][y][x], math.exp(-exp))
                heatmap[plane_idx][y][x] = min(heatmap[plane_idx][y][x], 1.0)


    def read_image(self, img_path):
        img_str = open(img_path, "rb").read()
        if not img_str:
            print("image not read, path=%s" % img_path)
        nparr = np.fromstring(img_str, np.uint8)
        return cv2.imdecode(nparr, cv2.IMREAD_COLOR)
